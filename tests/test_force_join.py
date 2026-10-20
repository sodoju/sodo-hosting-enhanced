from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import RequiredChannel
from bot.services.force_join_service import (
    add_channel, remove_channel, list_channels,
    check_membership, all_joined, get_active_channels,
)
from telegram.error import TelegramError


@pytest.mark.asyncio
async def test_add_and_list_channel(db_session: AsyncSession):
    ch = await add_channel(db_session, -1001234567890, "Test Channel", "testchan")
    await db_session.commit()
    channels = await list_channels(db_session)
    assert len(channels) == 1
    assert channels[0].chat_id == -1001234567890
    assert channels[0].display_name == "Test Channel"


@pytest.mark.asyncio
async def test_remove_channel(db_session: AsyncSession):
    ch = await add_channel(db_session, -1001111111111, "Remove Me")
    await db_session.commit()
    ok = await remove_channel(db_session, ch.id)
    await db_session.commit()
    assert ok is True
    channels = await list_channels(db_session)
    assert len(channels) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent(db_session: AsyncSession):
    ok = await remove_channel(db_session, 99999)
    assert ok is False


@pytest.mark.asyncio
async def test_membership_check_joined(db_session: AsyncSession, mock_bot):
    await add_channel(db_session, -100111, "Chan A", "chana")
    await db_session.commit()
    member = MagicMock()
    member.status = "member"
    mock_bot.get_chat_member.return_value = member
    statuses = await check_membership(mock_bot, db_session, 999)
    assert len(statuses) == 1
    assert statuses[0].is_member is True


@pytest.mark.asyncio
async def test_membership_check_not_joined(db_session: AsyncSession, mock_bot):
    await add_channel(db_session, -100222, "Chan B", "chanb")
    await db_session.commit()
    member = MagicMock()
    member.status = "left"
    mock_bot.get_chat_member.return_value = member
    joined = await all_joined(mock_bot, db_session, 999)
    assert joined is False


@pytest.mark.asyncio
async def test_membership_api_error(db_session: AsyncSession, mock_bot):
    await add_channel(db_session, -100333, "Chan C")
    await db_session.commit()
    mock_bot.get_chat_member.side_effect = TelegramError("Forbidden")
    statuses = await check_membership(mock_bot, db_session, 999)
    assert statuses[0].is_member is False


@pytest.mark.asyncio
async def test_no_channels_means_all_joined(db_session: AsyncSession, mock_bot):
    joined = await all_joined(mock_bot, db_session, 999)
    assert joined is True
