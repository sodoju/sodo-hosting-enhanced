from __future__ import annotations
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from bot.models.base import Base
from bot.models import (
    User, CreditWallet, ReferralLink, RequiredChannel, Plan
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    user = User(id=123456, username="testuser", first_name="Test", last_name="User")
    wallet = CreditWallet(user_id=123456, balance=100)
    ref = ReferralLink(user_id=123456, code="TESTCODE01")
    user.wallet = wallet
    user.referral_link = ref
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def sample_plan(db_session: AsyncSession) -> Plan:
    plan = Plan(
        name="test_premium", display_name="Test Premium",
        max_projects=5, max_file_size_mb=10, max_storage_mb=100,
        allows_zip=True, allows_github=True, allows_nodejs=True,
        allows_multi_file=True, allows_env_vars=True,
        duration_days=30, price_credits=500,
    )
    db_session.add(plan)
    await db_session.commit()
    return plan


@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    bot.get_chat_member = AsyncMock()
    bot.send_message = AsyncMock()
    return bot
