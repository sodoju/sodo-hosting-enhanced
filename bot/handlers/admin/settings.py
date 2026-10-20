from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import get_session
from bot.models import AppSettings
from sqlalchemy import select
from bot.utils.decorators import owner_only


@owner_only
async def cb_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    config = context.bot_data["config"]
    async with get_session() as session:
        result = await session.execute(select(AppSettings).order_by(AppSettings.key))
        settings = result.scalars().all()
    lines = [
        "⚙️ <b>Bot Settings</b>\n",
        f"👤 Owner ID: <code>{config.owner_id}</code>",
        f"🎁 Welcome Credits: <code>{config.welcome_credits}</code>",
        f"🎯 Daily Reward: <code>{config.daily_reward_credits}</code>",
        f"👥 Referral Reward: <code>{config.referral_reward_credits}</code>",
        f"📁 Free Max Projects: <code>{config.free_plan_max_projects}</code>",
        f"📦 Free Max File: <code>{config.free_plan_max_file_size_mb}MB</code>",
        "",
        "<b>Custom Settings (DB):</b>",
    ]
    for s in settings:
        lines.append(f"  <code>{s.key}</code> = <code>{s.value}</code>")
    lines.append("\n<i>Edit environment variables in Railway to change core settings.</i>")
    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_settings, pattern="^admin:settings$"))
