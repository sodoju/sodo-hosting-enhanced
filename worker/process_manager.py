from __future__ import annotations
import asyncio
import logging
import os
import signal
from pathlib import Path

logger = logging.getLogger(__name__)

_PROCESSES: dict[str, asyncio.subprocess.Process] = {}


async def launch(project_id: str, cmd: list[str], cwd: str, env: dict) -> int | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd, env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        _PROCESSES[project_id] = proc
        logger.info("Launched %s PID=%d", project_id, proc.pid)
        return proc.pid
    except Exception as e:
        logger.error("Launch failed %s: %s", project_id, e)
        return None


def kill(project_id: str) -> bool:
    proc = _PROCESSES.pop(project_id, None)
    if proc is None:
        return False
    try:
        proc.terminate()
    except Exception:
        pass
    return True


def is_running(project_id: str) -> bool:
    proc = _PROCESSES.get(project_id)
    if proc is None:
        return False
    return proc.returncode is None


async def wait_all() -> None:
    for pid, proc in list(_PROCESSES.items()):
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
    _PROCESSES.clear()
