from __future__ import annotations
import secrets
import string
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from bot.models import User, CreditWallet, ReferralLink


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str,
    last_name: str | None,
    referral_code: str | None = None,
) -> tuple[User, bool]:
    stmt = select(User).where(User.id == telegram_id).options(
        selectinload(User.wallet), selectinload(User.referral_link)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is not None:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.last_active_at = datetime.now(timezone.utc)
        return user, False
    user = User(
        id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        referral_code_used=referral_code,
    )
    wallet = CreditWallet(user_id=telegram_id, balance=0)
    ref_link = ReferralLink(user_id=telegram_id, code=_gen_code())
    user.wallet = wallet
    user.referral_link = ref_link
    session.add(user)
    return user, True


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    stmt = select(User).where(User.id == telegram_id).options(
        selectinload(User.wallet), selectinload(User.referral_link)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def ban_user(session: AsyncSession, telegram_id: int, reason: str) -> bool:
    user = await get_user(session, telegram_id)
    if user is None:
        return False
    user.is_banned = True
    user.ban_reason = reason
    user.banned_at = datetime.now(timezone.utc)
    return True


async def unban_user(session: AsyncSession, telegram_id: int) -> bool:
    user = await get_user(session, telegram_id)
    if user is None:
        return False
    user.is_banned = False
    user.ban_reason = None
    user.banned_at = None
    return True


async def get_user_stats(session: AsyncSession) -> dict:
    total = await session.scalar(select(func.count(User.id))) or 0
    banned = await session.scalar(select(func.count(User.id)).where(User.is_banned == True)) or 0
    return {"total": total, "banned": banned, "active": total - banned}


async def search_users(session: AsyncSession, query: str, limit: int = 10) -> list[User]:
    try:
        uid = int(query)
        stmt = select(User).where(User.id == uid).limit(limit)
    except ValueError:
        clean = query.lstrip("@")
        stmt = select(User).where(User.username.ilike(f"%{clean}%")).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_all_users_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(User.id).where(User.is_banned == False))
    return [row[0] for row in result.all()]


def _gen_code() -> str:
    abc = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(abc) for _ in range(10))
