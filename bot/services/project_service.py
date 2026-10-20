from __future__ import annotations
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from bot.models import Project, Deployment, LogEntry, ProjectStatus, Runtime, DeploymentStatus


async def get_user_projects(session: AsyncSession, user_id: int) -> list[Project]:
    result = await session.execute(
        select(Project).where(Project.owner_id == user_id).order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())


async def get_project(session: AsyncSession, project_id: uuid.UUID, owner_id: int | None = None) -> Project | None:
    stmt = select(Project).where(Project.id == project_id)
    if owner_id is not None:
        stmt = stmt.where(Project.owner_id == owner_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_project(session: AsyncSession, owner_id: int, name: str,
                         runtime: Runtime = Runtime.python, storage_path: str | None = None,
                         entry_file: str | None = None, github_url: str | None = None,
                         env_vars_json: str | None = None) -> Project:
    project = Project(
        owner_id=owner_id, name=name, runtime=runtime,
        status=ProjectStatus.pending, storage_path=storage_path,
        entry_file=entry_file, github_url=github_url, env_vars=env_vars_json,
    )
    session.add(project)
    return project


async def add_log(session: AsyncSession, project_id: uuid.UUID, content: str,
                  deployment_id: uuid.UUID | None = None) -> None:
    session.add(LogEntry(project_id=project_id, deployment_id=deployment_id, content=content))


async def get_recent_logs(session: AsyncSession, project_id: uuid.UUID, limit: int = 50) -> list[LogEntry]:
    result = await session.execute(
        select(LogEntry).where(LogEntry.project_id == project_id)
        .order_by(LogEntry.created_at.desc()).limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def count_user_projects(session: AsyncSession, user_id: int) -> int:
    return (await session.scalar(
        select(func.count(Project.id)).where(Project.owner_id == user_id)
    )) or 0


async def get_all_projects(session: AsyncSession, limit: int = 30, offset: int = 0) -> list[Project]:
    result = await session.execute(
        select(Project).options(selectinload(Project.owner))
        .order_by(Project.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def count_all_projects(session: AsyncSession) -> int:
    return (await session.scalar(select(func.count(Project.id)))) or 0


async def count_running(session: AsyncSession) -> int:
    return (await session.scalar(
        select(func.count(Project.id)).where(Project.status == ProjectStatus.running)
    )) or 0


async def count_failed(session: AsyncSession) -> int:
    return (await session.scalar(
        select(func.count(Deployment.id)).where(Deployment.status == DeploymentStatus.failed)
    )) or 0
