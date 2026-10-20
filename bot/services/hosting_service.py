from __future__ import annotations
import asyncio
import logging
import os
import signal
import uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import Project, Deployment, ProjectStatus, DeploymentStatus
from bot.services.project_service import add_log

logger = logging.getLogger(__name__)

_RUNTIME_ENV_ALLOWLIST = (
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TZ",
    "TMPDIR",
    "TMP",
    "TEMP",
)


async def start_project(session: AsyncSession, project: Project, storage_base: str) -> bool:
    if not project.storage_path or not project.entry_file:
        return False
    entry = Path(storage_base) / project.storage_path / project.entry_file
    if not entry.exists():
        await add_log(session, project.id, f"Entry file not found: {entry}")
        return False

    dep = Deployment(
        project_id=project.id, triggered_by=project.owner_id,
        status=DeploymentStatus.running,
        started_at=datetime.now(timezone.utc),
    )
    session.add(dep)
    await session.flush()

    try:
        env = _build_env(project)
        if project.runtime.value == "python":
            import sys
            cmd = [sys.executable, str(entry)]
        else:
            cmd = ["node", str(entry)]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(entry.parent),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        project.process_pid = proc.pid
        project.status = ProjectStatus.running
        dep.status = DeploymentStatus.success
        dep.completed_at = datetime.now(timezone.utc)
        await add_log(session, project.id, f"Process launched (PID {proc.pid})", dep.id)
        # Fire-and-forget log reader
        asyncio.create_task(_drain_logs(proc, project.id, storage_base))
        return True
    except Exception as e:
        logger.error("Start failed for project %s: %s", project.id, e)
        project.status = ProjectStatus.failed
        dep.status = DeploymentStatus.failed
        dep.error_message = str(e)
        dep.completed_at = datetime.now(timezone.utc)
        await add_log(session, project.id, f"Launch error: {e}", dep.id)
        return False


async def stop_project(session: AsyncSession, project: Project) -> bool:
    if project.process_pid:
        try:
            os.kill(project.process_pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    project.status = ProjectStatus.stopped
    project.process_pid = None
    await add_log(session, project.id, "Project stopped.")
    return True


async def restart_project(session: AsyncSession, project: Project, storage_base: str) -> bool:
    await stop_project(session, project)
    await asyncio.sleep(0.5)
    return await start_project(session, project, storage_base)


def _build_env(project: Project) -> dict:
    # User code must not inherit bot/database/API credentials or deployment metadata.
    # This reduces accidental exposure, but is not a substitute for OS/container isolation.
    env = {key: os.environ[key] for key in _RUNTIME_ENV_ALLOWLIST if key in os.environ}
    env["SODO_PROJECT_ID"] = str(project.id)
    if project.env_vars:
        import json
        try:
            extra = json.loads(project.env_vars)
            env.update({str(k): str(v) for k, v in extra.items()})
        except Exception:
            pass
    return env


async def _drain_logs(proc, project_id: uuid.UUID, storage_base: str) -> None:
    log_path = Path(storage_base) / str(project_id) / "runtime.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "ab") as f:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                f.write(line)
    except Exception as e:
        logger.debug("Log drain error for %s: %s", project_id, e)
