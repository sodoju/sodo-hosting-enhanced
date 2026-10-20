from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import get_session
from bot.services.user_service import get_user_stats
from bot.services.project_service import count_all_projects, count_running, count_failed
from bot.services.credit_service import total_credits_distributed
from bot.services.subscription_service import get_all_plans
from bot.utils.decorators import owner_only
from sqlalchemy import select, func


@owner_only
async def cb_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    async with get_session() as session:
        users = await get_user_stats(session)
        total_proj = await count_all_projects(session)
        running = await count_running(session)
        failed = await count_failed(session)
        credits = await total_credits_distributed(session)
        from bot.models import Subscription
        premium_count = (await session.scalar(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        )) or 0

    text = (
        "📊 <b>Dashboard</b>\n\n"
        f"👥 Users: <b>{users['total']}</b>  "
        f"(Active: {users['active']} | Banned: {users['banned']})\n"
        f"💎 Premium Members: <b>{premium_count}</b>\n\n"
        f"🚀 Total Projects: <b>{total_proj}</b>\n"
        f"🟢 Running: <b>{running}</b>\n"
        f"🔴 Failed Deployments: <b>{failed}</b>\n\n"
        f"🪙 Credits Distributed: <b>{credits:,}</b>\n"
    )
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_dashboard, pattern="^admin:dashboard$"))
