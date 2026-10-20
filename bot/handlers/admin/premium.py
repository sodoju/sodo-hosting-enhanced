from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import get_session
from bot.services.subscription_service import get_all_plans
from bot.utils.decorators import owner_only


@owner_only
async def cb_admin_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    async with get_session() as session:
        plans = await get_all_plans(session)
    lines = ["💎 <b>Premium Management</b>\n", "<b>Available Plans:</b>"]
    for p in plans:
        dur = f"{p.duration_days}d" if p.duration_days else "Permanent"
        lines.append(f"  ID:{p.id} — {p.display_name} — {dur} — {p.price_credits}🪙")
    lines += [
        "",
        "To grant/revoke premium go to:",
        "<b>👥 Users</b> → Search user → Grant/Revoke Premium",
    ]
    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Go to Users", callback_data="admin:users")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")],
        ]),
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_admin_premium, pattern="^admin:premium$"))
