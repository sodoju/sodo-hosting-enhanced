from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters, CommandHandler)
from bot.database import get_session
from bot.services.force_join_service import add_channel, remove_channel, list_channels
from bot.services.admin_service import log_action
from bot.keyboards.admin import force_join_menu
from bot.utils.decorators import owner_only
from bot.utils.formatting import ts

logger = logging.getLogger(__name__)

FJ_INPUT, FJ_CONFIRM_REMOVE = range(2)


@owner_only
async def cb_fj_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔐 <b>Force Join Settings</b>",
        parse_mode="HTML",
        reply_markup=force_join_menu(),
    )


@owner_only
async def cb_fj_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    async with get_session() as session:
        channels = await list_channels(session)
    if not channels:
        await query.edit_message_text(
            "📋 <b>Required Channels</b>\n\nNone configured.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin:fj")]]),
        )
        return
    lines = ["📋 <b>Required Channels</b>\n"]
    for ch in channels:
        status = "✅" if ch.is_enabled else "❌"
        lines.append(f"{status} <b>{ch.display_name}</b> (ID: {ch.chat_id})"
                     + (f" @{ch.username}" if ch.username else ""))
    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin:fj")]]),
    )


@owner_only
async def cb_fj_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "➕ <b>Add Required Channel</b>\n\n"
        "Send channel info in this format:\n"
        "<code>CHAT_ID Display Name @username</code>\n\n"
        "Examples:\n"
        "<code>-1001234567890 My Channel @mychannel</code>\n"
        "<code>-1001234567890 Private Channel</code>\n\n"
        "Chat ID is required. Username and invite URL are optional.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin:fj")]]),
    )
    return FJ_INPUT


@owner_only
async def on_fj_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    parts = text.split(None, 3)
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Format: CHAT_ID Display Name [@username]\nTry again or /cancel"
        )
        return FJ_INPUT
    try:
        chat_id = int(parts[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid chat ID. Must be an integer. Try again:")
        return FJ_INPUT

    display_name = parts[1]
    username = None
    for part in parts[2:]:
        if part.startswith("@"):
            username = part.lstrip("@")
        else:
            display_name += " " + part

    config = context.bot_data["config"]
    try:
        await context.bot.get_chat(chat_id)
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Could not verify chat {chat_id}: {e}\n\nAdd anyway? /skip to confirm, or try a different ID."
        )
        context.user_data["pending_fj"] = {"chat_id": chat_id, "name": display_name, "username": username}
        return FJ_INPUT

    async with get_session() as session:
        ch = await add_channel(session, chat_id, display_name, username)
        await log_action(session, config.owner_id, "fj_add", "channel", str(chat_id), display_name)

    await update.message.reply_text(
        f"✅ Channel <b>{display_name}</b> added to Force Join.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin:fj")]]),
    )
    return ConversationHandler.END


@owner_only
async def cb_fj_remove_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    async with get_session() as session:
        channels = await list_channels(session)
    if not channels:
        await query.answer("No channels to remove.", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        f"🗑️ {ch.display_name} [{ch.chat_id}]",
        callback_data=f"admin:fj:del:{ch.id}"
    )] for ch in channels]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin:fj")])
    await query.edit_message_text(
        "➖ <b>Remove Channel</b>\n\nSelect channel to remove:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@owner_only
async def cb_fj_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    ch_id = int(query.data.split(":")[-1])
    config = context.bot_data["config"]
    async with get_session() as session:
        ok = await remove_channel(session, ch_id)
        if ok:
            await log_action(session, config.owner_id, "fj_remove", "channel", str(ch_id))
    msg = "✅ Channel removed." if ok else "❌ Channel not found."
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin:fj")]]),
    )


async def fj_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🔐 <b>Force Join Settings</b>", parse_mode="HTML", reply_markup=force_join_menu())
    elif update.message:
        await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_fj_add_start, pattern="^admin:fj:add$")],
        states={FJ_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_fj_input)]},
        fallbacks=[
            CallbackQueryHandler(fj_cancel, pattern="^admin:fj$"),
            CommandHandler("cancel", fj_cancel),
        ],
        per_user=True, per_chat=True,
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(cb_fj_menu, pattern="^admin:fj$"))
    app.add_handler(CallbackQueryHandler(cb_fj_list, pattern="^admin:fj:list$"))
    app.add_handler(CallbackQueryHandler(cb_fj_remove_list, pattern="^admin:fj:remove_list$"))
    app.add_handler(CallbackQueryHandler(cb_fj_delete, pattern=r"^admin:fj:del:\d+$"))
