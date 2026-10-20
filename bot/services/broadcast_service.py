from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot
from telegram.error import TelegramError
from bot.models import BroadcastJob, BroadcastStatus
from bot.services.user_service import get_all_users_ids

logger = logging.getLogger(__name__)


async def create_job(session: AsyncSession, created_by: int,
                     message_text: str, photo_file_id: str | None = None) -> BroadcastJob:
    job = BroadcastJob(
        created_by=created_by, message_text=message_text,
        photo_file_id=photo_file_id, status=BroadcastStatus.pending,
    )
    session.add(job)
    return job


async def run_broadcast(bot: Bot, job_id: int, session_factory) -> None:
    async with session_factory() as session:
        from bot.models import BroadcastJob
        from sqlalchemy import select
        job = (await session.execute(select(BroadcastJob).where(BroadcastJob.id == job_id))).scalar_one_or_none()
        if not job:
            return
        user_ids = await get_all_users_ids(session)
        job.status = BroadcastStatus.running
        job.total_users = len(user_ids)
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

    sent = failed = 0
    for uid in user_ids:
        try:
            if job.photo_file_id:
                await bot.send_photo(chat_id=uid, photo=job.photo_file_id,
                                     caption=job.message_text, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=uid, text=job.message_text, parse_mode="HTML")
            sent += 1
        except TelegramError:
            failed += 1
        if (sent + failed) % 25 == 0:
            await asyncio.sleep(1)

    async with session_factory() as session:
        from sqlalchemy import select
        job = (await session.execute(select(BroadcastJob).where(BroadcastJob.id == job_id))).scalar_one_or_none()
        if job:
            job.sent_count = sent
            job.failed_count = failed
            job.status = BroadcastStatus.completed
            job.completed_at = datetime.now(timezone.utc)
        await session.commit()
