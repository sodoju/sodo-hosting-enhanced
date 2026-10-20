from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import get_session
from bot.services.credit_service import get_balance
from bot.services.subscription_service import get_limits
from bot.services.project_service import count_user_projects
from bot.services.referral_service import get_stats, get_link
from bot.utils.formatting import credits_fmt, ts


async def cb_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    async with get_session() as session:
        balance = await get_balance(session, user.id)
        limits = await get_limits(session, user.id)
        proj_count = await count_user_projects(session, user.id)
        ref_stats = await get_stats(session, user.id)
        link = await get_link(session, user.id)

    bot_info = await context.bot.get_me()
    ref_url = f"https://t.me/{bot_info.username}?start=ref_{link.code}" if link else "—"
    plan_line = f"{'💎' if limits['is_premium'] else '⚪'} {limits['plan_name']}"
    if limits.get("expires_at"):
        plan_line += f" (expires {ts(limits['expires_at'])})"

    text = (
        f"👤 <b>My Account</b>\n\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"👤 Name: {user.full_name}\n"
        + (f"🔗 Username: @{user.username}\n" if user.username else "")
        + f"\n{plan_line}\n"
        f"🪙 Balance: <b>{credits_fmt(balance)}</b>\n"
        f"📁 Projects: {proj_count}/{limits['max_projects']}\n"
        f"👥 Referrals: {ref_stats['total']}\n\n"
        f"🔗 Referral link:\n<code>{ref_url}</code>"
    )
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🪙 Credits", callback_data="credits"),
            InlineKeyboardButton("💎 Plans", callback_data="premium"),
        ], [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]),
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_account, pattern="^account$"))
