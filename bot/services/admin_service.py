from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import AdminActivityLog


async def log_action(session: AsyncSession, actor_id: int, action: str,
                     target_type: str | None = None, target_id: str | None = None,
                     detail: str | None = None) -> None:
    session.add(AdminActivityLog(
        actor_id=actor_id, action=action,
        target_type=target_type, target_id=target_id, detail=detail,
    ))


async def get_recent_logs(session: AsyncSession, limit: int = 50) -> list[AdminActivityLog]:
    from sqlalchemy import select
    result = await session.execute(
        select(AdminActivityLog).order_by(AdminActivityLog.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
