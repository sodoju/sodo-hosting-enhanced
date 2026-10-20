from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler


async def cb_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    config = context.bot_data["config"]
    await query.edit_message_text(
        "🆘 <b>Support</b>\n\n"
        "For help with SODO HOSTING:\n\n"
        f"• Message the owner directly (ID: <code>{config.owner_id}</code>)\n"
        "• Include your Telegram ID and a description of the issue.\n\n"
        f"📋 Your ID: <code>{user.id}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]),
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_support, pattern="^support$"))
