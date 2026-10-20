from __future__ import annotations
import secrets
import string
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import RedeemCode, RedeemRecord
from bot.services.credit_service import add_credits, TransactionType


async def create_code(session: AsyncSession, created_by: int, credit_amount: int,
                      max_uses: int | None = 1, expires_at: datetime | None = None) -> RedeemCode:
    code = RedeemCode(
        code=_gen(), credit_amount=credit_amount, max_uses=max_uses,
        expires_at=expires_at, created_by=created_by, is_active=True,
    )
    session.add(code)
    return code


async def redeem(session: AsyncSession, user_id: int, code_str: str) -> tuple[bool, str]:
    stmt = select(RedeemCode).where(RedeemCode.code == code_str.upper(), RedeemCode.is_active == True)
    code = (await session.execute(stmt)).scalar_one_or_none()
    if not code:
        return False, "Invalid or inactive code."
    now = datetime.now(timezone.utc)
    if code.expires_at and code.expires_at < now:
        return False, "Code has expired."
    if code.max_uses is not None and code.used_count >= code.max_uses:
        return False, "Code fully redeemed."
    existing = (await session.execute(
        select(RedeemRecord).where(RedeemRecord.code_id == code.id, RedeemRecord.user_id == user_id)
    )).scalar_one_or_none()
    if existing:
        return False, "Already redeemed."
    session.add(RedeemRecord(code_id=code.id, user_id=user_id))
    code.used_count += 1
    await add_credits(session, user_id, code.credit_amount,
                      TransactionType.redeem, f"Code {code_str.upper()}")
    return True, f"✅ {code.credit_amount} credits added!"


async def list_codes(session: AsyncSession) -> list[RedeemCode]:
    result = await session.execute(
        select(RedeemCode).where(RedeemCode.is_active == True).order_by(RedeemCode.created_at.desc())
    )
    return list(result.scalars().all())


def _gen() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
