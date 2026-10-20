from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.keyboards.admin import admin_menu
from bot.utils.decorators import owner_only


@owner_only
async def cb_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚙️ <b>Admin Panel</b>\n\nSelect a section:",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


async def cb_cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data.pop("admin_action", None)
    await query.edit_message_text(
        "⚙️ <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_menu()
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(cb_cancel_action, pattern="^cancel_action$"))
