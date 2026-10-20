from __future__ import annotations
import logging
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot
from telegram.error import TelegramError
from bot.models import RequiredChannel

logger = logging.getLogger(__name__)


@dataclass
class ChannelStatus:
    channel: RequiredChannel
    is_member: bool


async def get_active_channels(session: AsyncSession) -> list[RequiredChannel]:
    stmt = select(RequiredChannel).where(RequiredChannel.is_enabled == True).order_by(RequiredChannel.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def check_membership(bot: Bot, session: AsyncSession, user_id: int) -> list[ChannelStatus]:
    channels = await get_active_channels(session)
    statuses: list[ChannelStatus] = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch.chat_id, user_id=user_id)
            is_member = member.status in ("member", "administrator", "creator")
        except TelegramError as e:
            logger.warning("Force join check error for %s: %s", ch.chat_id, e)
            is_member = False
        statuses.append(ChannelStatus(channel=ch, is_member=is_member))
    return statuses


async def all_joined(bot: Bot, session: AsyncSession, user_id: int) -> bool:
    statuses = await check_membership(bot, session, user_id)
    return all(s.is_member for s in statuses)


async def add_channel(session: AsyncSession, chat_id: int, display_name: str,
                      username: str | None = None, invite_url: str | None = None) -> RequiredChannel:
    ch = RequiredChannel(chat_id=chat_id, display_name=display_name,
                         username=username, invite_url=invite_url, is_enabled=True)
    session.add(ch)
    return ch


async def remove_channel(session: AsyncSession, channel_id: int) -> bool:
    stmt = select(RequiredChannel).where(RequiredChannel.id == channel_id)
    ch = (await session.execute(stmt)).scalar_one_or_none()
    if ch is None:
        return False
    await session.delete(ch)
    return True


async def list_channels(session: AsyncSession) -> list[RequiredChannel]:
    result = await session.execute(select(RequiredChannel).order_by(RequiredChannel.id))
    return list(result.scalars().all())
