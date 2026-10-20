from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import get_session
from bot.services.subscription_service import get_all_plans, get_active, get_limits
from bot.utils.formatting import ts


async def cb_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    async with get_session() as session:
        plans = await get_all_plans(session)
        sub = await get_active(session, user.id)
        limits = await get_limits(session, user.id)

    lines = ["💎 <b>Premium Plans</b>\n"]
    if sub:
        lines.append(f"✅ Current: <b>{limits['plan_name']}</b>")
        if limits.get("expires_at"):
            lines.append(f"📅 Expires: {ts(limits['expires_at'])}")
        lines.append("")

    for plan in plans:
        dur = f"{plan.duration_days}d" if plan.duration_days else "Permanent"
        lines += [
            f"<b>{plan.display_name}</b>",
            f"  📁 {plan.max_projects} projects | 📦 {plan.max_file_size_mb}MB max",
            f"  {'✅' if plan.allows_zip else '❌'} ZIP  "
            f"{'✅' if plan.allows_github else '❌'} GitHub  "
            f"{'✅' if plan.allows_nodejs else '❌'} Node.js",
            f"  ⏱️ {dur} | 🪙 {plan.price_credits:,} credits",
            "",
        ]

    lines.append("💬 Contact the owner to purchase a plan.")
    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🆘 Contact Support", callback_data="support"),
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
        ]]),
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_premium, pattern="^premium$"))
