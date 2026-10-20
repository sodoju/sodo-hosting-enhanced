from __future__ import annotations
from datetime import datetime, timezone, date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import CreditWallet, CreditTransaction, TransactionType


async def get_balance(session: AsyncSession, user_id: int) -> int:
    wallet = await _locked_wallet(session, user_id)
    return wallet.balance if wallet else 0


async def add_credits(
    session: AsyncSession,
    user_id: int,
    amount: int,
    tx_type: TransactionType,
    description: str,
    actor_id: int | None = None,
) -> int:
    if amount <= 0:
        raise ValueError("amount must be positive")
    wallet = await _locked_wallet(session, user_id)
    if wallet is None:
        wallet = CreditWallet(user_id=user_id, balance=0)
        session.add(wallet)
    wallet.balance += amount
    session.add(CreditTransaction(
        user_id=user_id, amount=amount, type=tx_type,
        description=description, actor_id=actor_id,
    ))
    return wallet.balance


async def deduct_credits(
    session: AsyncSession,
    user_id: int,
    amount: int,
    tx_type: TransactionType,
    description: str,
    actor_id: int | None = None,
) -> int:
    if amount <= 0:
        raise ValueError("amount must be positive")
    wallet = await _locked_wallet(session, user_id)
    if wallet is None or wallet.balance < amount:
        raise ValueError("Insufficient balance")
    wallet.balance -= amount
    session.add(CreditTransaction(
        user_id=user_id, amount=-amount, type=tx_type,
        description=description, actor_id=actor_id,
    ))
    return wallet.balance


async def claim_daily(session: AsyncSession, user_id: int, reward: int) -> bool:
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    stmt = select(CreditTransaction).where(
        CreditTransaction.user_id == user_id,
        CreditTransaction.type == TransactionType.daily,
        CreditTransaction.created_at >= today_start,
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        return False
    await add_credits(session, user_id, reward, TransactionType.daily, "Daily reward")
    return True


async def get_transactions(session: AsyncSession, user_id: int, limit: int = 20, offset: int = 0) -> list[CreditTransaction]:
    stmt = (
        select(CreditTransaction).where(CreditTransaction.user_id == user_id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(limit).offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def total_credits_distributed(session: AsyncSession) -> int:
    from sqlalchemy import func
    result = await session.scalar(
        select(func.sum(CreditTransaction.amount)).where(CreditTransaction.amount > 0)
    )
    return int(result or 0)


async def _locked_wallet(session: AsyncSession, user_id: int) -> CreditWallet | None:
    stmt = select(CreditWallet).where(CreditWallet.user_id == user_id).with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
