from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import get_session
from bot.services.admin_service import get_recent_logs
from bot.utils.decorators import owner_only
from bot.utils.formatting import ts


@owner_only
async def cb_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    async with get_session() as session:
        logs = await get_recent_logs(session, 20)
    lines = ["🛡️ <b>Activity Log</b> (last 20)\n"]
    for log in logs:
        target = f" → {log.target_type}:{log.target_id}" if log.target_id else ""
        lines.append(f"[{ts(log.created_at)}] <b>{log.action}</b>{target}")
        if log.detail:
            lines.append(f"  <i>{log.detail[:80]}</i>")
    await query.edit_message_text(
        "\n".join(lines) or "No activity.", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_activity, pattern="^admin:activity$"))
