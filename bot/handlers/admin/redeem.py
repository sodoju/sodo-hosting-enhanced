from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters, CommandHandler)
from bot.database import get_session
from bot.services.redeem_service import create_code, list_codes
from bot.services.admin_service import log_action
from bot.utils.decorators import owner_only
from bot.utils.formatting import ts

REDEEM_INPUT = 0


@owner_only
async def cb_redeem_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    async with get_session() as session:
        codes = await list_codes(session)
    lines = ["🎟️ <b>Redeem Codes</b>\n"]
    for c in codes[:15]:
        uses = f"{c.used_count}/{c.max_uses}" if c.max_uses else f"{c.used_count}/∞"
        lines.append(f"<code>{c.code}</code> — {c.credit_amount}🪙 — {uses}")
    await query.edit_message_text(
        "\n".join(lines) or "No active codes.", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Generate Code", callback_data="admin:redeem:gen")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")],
        ]),
    )
    return ConversationHandler.END


@owner_only
async def cb_gen_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎟️ <b>Generate Code</b>\n\n"
        "Format: <code>credits [max_uses]</code>\n"
        "Examples:\n"
        "<code>100</code> — 100 credits, 1 use\n"
        "<code>50 10</code> — 50 credits, 10 uses\n"
        "<code>200 0</code> — 200 credits, unlimited",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin:redeem")]]),
    )
    return REDEEM_INPUT


@owner_only
async def on_gen_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parts = (update.message.text or "").split()
    try:
        amount = int(parts[0])
        max_uses = int(parts[1]) if len(parts) > 1 else 1
        if max_uses == 0:
            max_uses = None
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Format: credits [max_uses]")
        return REDEEM_INPUT
    config = context.bot_data["config"]
    async with get_session() as session:
        code = await create_code(session, config.owner_id, amount, max_uses)
        await log_action(session, config.owner_id, "create_redeem_code", detail=f"amount={amount}")
    uses_str = str(max_uses) if max_uses else "unlimited"
    await update.message.reply_text(
        f"✅ Code created!\n\n<code>{code.code}</code>\n"
        f"💰 {amount} credits | {uses_str} use(s)",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin:redeem")]]),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_gen_start, pattern="^admin:redeem:gen$")],
        states={REDEEM_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_gen_input)]},
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^admin:redeem$"),
            CommandHandler("cancel", cancel),
        ],
        per_user=True, per_chat=True,
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(cb_redeem_menu, pattern="^admin:redeem$"))
