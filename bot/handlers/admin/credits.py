from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.utils.decorators import owner_only


@owner_only
async def cb_admin_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🪙 <b>Credits Management</b>\n\n"
        "To add or deduct credits from a user, go to:\n"
        "<b>👥 Users</b> → Search user → Add/Deduct Credits",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Go to Users", callback_data="admin:users")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")],
        ]),
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_admin_credits, pattern="^admin:credits$"))
