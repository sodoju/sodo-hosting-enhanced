from __future__ import annotations
import functools
from typing import Callable
from telegram import Update
from telegram.ext import ContextTypes
from bot.database import get_session
from bot.services.user_service import get_user
from bot.services.force_join_service import get_active_channels, all_joined


def owner_only(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        config = context.bot_data["config"]
        user = update.effective_user
        if user is None or user.id != config.owner_id:
            if update.callback_query:
                await update.callback_query.answer("⛔ Not authorized.", show_alert=True)
            elif update.message:
                await update.message.reply_text("⛔ Not authorized.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def not_banned(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None:
            return
        async with get_session() as session:
            db_user = await get_user(session, user.id)
            if db_user and db_user.is_banned:
                msg = f"🚫 <b>Account banned.</b>\n<i>{db_user.ban_reason or 'Contact support.'}</i>"
                if update.callback_query:
                    await update.callback_query.answer("🚫 Banned.", show_alert=True)
                elif update.message:
                    await update.message.reply_text(msg, parse_mode="HTML")
                return
        return await func(update, context, *args, **kwargs)
    return wrapper


def require_joined(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None:
            return
        async with get_session() as session:
            channels = await get_active_channels(session)
            if not channels:
                return await func(update, context, *args, **kwargs)
            joined = await all_joined(context.bot, session, user.id)
        if joined:
            return await func(update, context, *args, **kwargs)
        from bot.handlers.start import send_join_prompt
        await send_join_prompt(update, context)
    return wrapper
