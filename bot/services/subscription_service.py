from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from bot.models import Plan, Subscription


async def get_active(session: AsyncSession, user_id: int) -> Subscription | None:
    now = datetime.now(timezone.utc)
    stmt = (
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.is_active == True)
        .options(selectinload(Subscription.plan))
        .order_by(Subscription.created_at.desc())
    )
    result = await session.execute(stmt)
    for sub in result.scalars().all():
        if sub.expires_at is None or sub.expires_at > now:
            return sub
        sub.is_active = False
    return None


async def grant(session: AsyncSession, user_id: int, plan_id: int,
                granted_by: int, duration_days: int | None = None) -> Subscription:
    existing = await get_active(session, user_id)
    if existing:
        existing.is_active = False
    now = datetime.now(timezone.utc)
    sub = Subscription(
        user_id=user_id, plan_id=plan_id, granted_by=granted_by,
        starts_at=now,
        expires_at=(now + timedelta(days=duration_days)) if duration_days else None,
        is_active=True,
    )
    session.add(sub)
    return sub


async def revoke(session: AsyncSession, user_id: int) -> bool:
    sub = await get_active(session, user_id)
    if sub is None:
        return False
    sub.is_active = False
    return True


async def extend(session: AsyncSession, user_id: int, days: int) -> bool:
    sub = await get_active(session, user_id)
    if sub is None:
        return False
    now = datetime.now(timezone.utc)
    base = sub.expires_at if (sub.expires_at and sub.expires_at > now) else now
    sub.expires_at = base + timedelta(days=days)
    return True


async def is_premium(session: AsyncSession, user_id: int) -> bool:
    return (await get_active(session, user_id)) is not None


async def get_limits(session: AsyncSession, user_id: int) -> dict:
    sub = await get_active(session, user_id)
    if sub and sub.plan:
        p = sub.plan
        return {
            "max_projects": p.max_projects, "max_file_size_mb": p.max_file_size_mb,
            "max_storage_mb": p.max_storage_mb, "allows_zip": p.allows_zip,
            "allows_github": p.allows_github, "allows_nodejs": p.allows_nodejs,
            "allows_multi_file": p.allows_multi_file, "allows_env_vars": p.allows_env_vars,
            "is_premium": True, "plan_name": p.display_name,
            "expires_at": sub.expires_at,
        }
    return {
        "max_projects": 1, "max_file_size_mb": 1, "max_storage_mb": 10,
        "allows_zip": False, "allows_github": False, "allows_nodejs": False,
        "allows_multi_file": False, "allows_env_vars": False,
        "is_premium": False, "plan_name": "Free", "expires_at": None,
    }


async def get_all_plans(session: AsyncSession) -> list[Plan]:
    result = await session.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.id))
    return list(result.scalars().all())
