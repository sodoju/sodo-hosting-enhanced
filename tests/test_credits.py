from __future__ import annotations
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from bot.services.credit_service import add_credits, deduct_credits, get_balance, claim_daily, TransactionType


@pytest.mark.asyncio
async def test_add_credits(db_session: AsyncSession, sample_user):
    new_bal = await add_credits(db_session, 123456, 50, TransactionType.admin_add, "test")
    await db_session.commit()
    assert new_bal == 150


@pytest.mark.asyncio
async def test_deduct_credits(db_session: AsyncSession, sample_user):
    new_bal = await deduct_credits(db_session, 123456, 30, TransactionType.purchase, "test")
    await db_session.commit()
    assert new_bal == 70


@pytest.mark.asyncio
async def test_deduct_insufficient(db_session: AsyncSession, sample_user):
    with pytest.raises(ValueError, match="Insufficient"):
        await deduct_credits(db_session, 123456, 9999, TransactionType.purchase, "test")


@pytest.mark.asyncio
async def test_daily_reward(db_session: AsyncSession, sample_user):
    ok = await claim_daily(db_session, 123456, 10)
    assert ok is True
    ok2 = await claim_daily(db_session, 123456, 10)
    assert ok2 is False


@pytest.mark.asyncio
async def test_add_zero_raises(db_session: AsyncSession, sample_user):
    with pytest.raises(ValueError):
        await add_credits(db_session, 123456, 0, TransactionType.admin_add, "test")


@pytest.mark.asyncio
async def test_concurrent_safety(db_session: AsyncSession, sample_user):
    import asyncio
    async def add_ten():
        await add_credits(db_session, 123456, 10, TransactionType.admin_add, "concurrent")
    await asyncio.gather(add_ten(), add_ten(), add_ten())
    await db_session.commit()
    balance = await get_balance(db_session, 123456)
    assert balance == 130
