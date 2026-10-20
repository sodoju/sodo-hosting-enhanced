from __future__ import annotations
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters, CommandHandler)
from bot.database import get_session
from bot.services.broadcast_service import create_job, run_broadcast
from bot.services.admin_service import log_action
from bot.utils.decorators import owner_only

logger = logging.getLogger(__name__)
BC_MSG, BC_PREVIEW = range(2)


@owner_only
async def cb_bc_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📢 <b>Broadcast</b>\n\n"
        "Send the message to broadcast to all users.\n"
        "Supports HTML formatting.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]),
    )
    return BC_MSG


@owner_only
async def on_bc_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text or ""
    photo_id = None
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
        text = update.message.caption or ""
    context.user_data["broadcast"] = {"text": text, "photo": photo_id}
    preview = f"📢 <b>Broadcast Preview</b>\n\n{'[Photo]\n' if photo_id else ''}{text[:500]}"
    await update.message.reply_text(
        preview, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Send", callback_data="bc_send"),
            InlineKeyboardButton("❌ Cancel", callback_data="admin_panel"),
        ]]),
    )
    return BC_PREVIEW


@owner_only
async def on_bc_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = context.user_data.pop("broadcast", {})
    text = data.get("text", "")
    photo = data.get("photo")
    config = context.bot_data["config"]

    async with get_session() as session:
        job = await create_job(session, config.owner_id, text, photo)
        await log_action(session, config.owner_id, "broadcast_start")
        await session.flush()
        job_id = job.id

    from sqlalchemy.ext.asyncio import async_sessionmaker
    from bot.database import _sessionmaker
    asyncio.create_task(run_broadcast(context.bot, job_id, _sessionmaker))

    await query.edit_message_text(
        "📢 Broadcast queued! Sending in background…",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")]]),
    )
    return ConversationHandler.END


async def bc_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("broadcast", None)
    if update.callback_query:
        await update.callback_query.answer()
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_bc_entry, pattern="^admin:broadcast$")],
        states={
            BC_MSG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_bc_msg),
                MessageHandler(filters.PHOTO, on_bc_msg),
            ],
            BC_PREVIEW: [CallbackQueryHandler(on_bc_confirm, pattern="^bc_send$")],
        },
        fallbacks=[
            CallbackQueryHandler(bc_cancel, pattern="^admin_panel$"),
            CommandHandler("cancel", bc_cancel),
        ],
        per_user=True, per_chat=True,
    )
    app.add_handler(conv)
