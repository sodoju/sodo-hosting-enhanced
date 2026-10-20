from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from bot.services.user_service import get_or_create_user, ban_user, unban_user, get_user


@pytest.mark.asyncio
async def test_create_new_user(db_session: AsyncSession):
    user, created = await get_or_create_user(
        db_session, 999, "newuser", "New", "User"
    )
    assert created is True
    assert user.id == 999
    assert user.username == "newuser"
    assert user.wallet is not None
    assert user.referral_link is not None


@pytest.mark.asyncio
async def test_existing_user_not_recreated(db_session: AsyncSession, sample_user):
    user, created = await get_or_create_user(
        db_session, 123456, "testuser", "Test", "User"
    )
    assert created is False
    assert user.id == 123456


@pytest.mark.asyncio
async def test_ban_unban(db_session: AsyncSession, sample_user):
    ok = await ban_user(db_session, 123456, "Test ban reason")
    assert ok is True
    await db_session.commit()
    u = await get_user(db_session, 123456)
    assert u.is_banned is True
    assert u.ban_reason == "Test ban reason"

    ok2 = await unban_user(db_session, 123456)
    assert ok2 is True
    await db_session.commit()
    u2 = await get_user(db_session, 123456)
    assert u2.is_banned is False


@pytest.mark.asyncio
async def test_ban_nonexistent_user(db_session: AsyncSession):
    ok = await ban_user(db_session, 99999999, "reason")
    assert ok is False


@pytest.mark.asyncio
async def test_owner_authorization():
    from unittest.mock import AsyncMock, MagicMock
    from bot.utils.decorators import owner_only

    @owner_only
    async def protected(update, context):
        return "allowed"

    config = MagicMock()
    config.owner_id = 100

    update_owner = MagicMock()
    update_owner.effective_user.id = 100
    update_owner.callback_query = None
    context = MagicMock()
    context.bot_data = {"config": config}
    result = await protected(update_owner, context)
    assert result == "allowed"

    update_other = MagicMock()
    update_other.effective_user.id = 999
    update_other.callback_query = None
    update_other.message = AsyncMock()
    result2 = await protected(update_other, context)
    assert result2 is None
