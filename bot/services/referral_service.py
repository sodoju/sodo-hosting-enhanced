from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import ReferralLink, ReferralRecord
from bot.services.credit_service import add_credits, TransactionType


async def get_link(session: AsyncSession, user_id: int) -> ReferralLink | None:
    result = await session.execute(select(ReferralLink).where(ReferralLink.user_id == user_id))
    return result.scalar_one_or_none()


async def find_by_code(session: AsyncSession, code: str) -> ReferralLink | None:
    result = await session.execute(select(ReferralLink).where(ReferralLink.code == code))
    return result.scalar_one_or_none()


async def process_referral(session: AsyncSession, referrer_id: int, referred_id: int, reward: int) -> bool:
    if referrer_id == referred_id:
        return False
    existing = await session.execute(select(ReferralRecord).where(ReferralRecord.referred_id == referred_id))
    if existing.scalar_one_or_none() is not None:
        return False
    session.add(ReferralRecord(
        referrer_id=referrer_id,
        referred_id=referred_id,
        rewarded_at=datetime.now(timezone.utc),
    ))
    await add_credits(session, referrer_id, reward, TransactionType.referral,
                      f"Referral bonus for user {referred_id}")
    return True


async def get_stats(session: AsyncSession, user_id: int) -> dict:
    total = await session.scalar(
        select(func.count(ReferralRecord.id)).where(ReferralRecord.referrer_id == user_id)
    ) or 0
    return {"total": total}


async def get_leaderboard(session: AsyncSession, limit: int = 10) -> list[tuple[int, int]]:
    stmt = (
        select(ReferralRecord.referrer_id, func.count(ReferralRecord.id).label("cnt"))
        .group_by(ReferralRecord.referrer_id)
        .order_by(func.count(ReferralRecord.id).desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [(row.referrer_id, row.cnt) for row in result.all()]
