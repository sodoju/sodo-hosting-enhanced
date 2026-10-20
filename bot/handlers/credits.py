from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, CommandHandler
from bot.database import get_session
from bot.services.credit_service import get_balance, claim_daily, get_transactions, TransactionType
from bot.services.redeem_service import redeem
from bot.services.referral_service import get_link, get_stats
from bot.utils.formatting import credits_fmt, ts
from bot.utils.pagination import paginate, nav_buttons

REDEEM_INPUT = 0


async def cb_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    async with get_session() as session:
        balance = await get_balance(session, user.id)
        stats = await get_stats(session, user.id)
        link = await get_link(session, user.id)

    bot_user = await context.bot.get_me()
    ref_url = f"https://t.me/{bot_user.username}?start=ref_{link.code}" if link else "—"

    text = (
        f"🪙 <b>Credits & Referrals</b>\n\n"
        f"💰 Balance: <b>{credits_fmt(balance)}</b>\n"
        f"👥 Referrals: <b>{stats['total']}</b>\n\n"
        f"🔗 Your referral link:\n<code>{ref_url}</code>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Daily Reward", callback_data="credits:daily"),
         InlineKeyboardButton("🎟️ Redeem Code", callback_data="credits:redeem_start")],
        [InlineKeyboardButton("📋 Tx History", callback_data="credits:history:0"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="credits:leaderboard")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def cb_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    config = context.bot_data["config"]
    async with get_session() as session:
        ok = await claim_daily(session, user.id, config.daily_reward_credits)
        balance = await get_balance(session, user.id)
    if ok:
        await query.answer(f"✅ +{config.daily_reward_credits} credits! Balance: {balance:,}", show_alert=True)
    else:
        await query.answer("⏰ Already claimed today. Come back tomorrow!", show_alert=True)


async def cb_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    page = int(query.data.split(":")[-1])
    async with get_session() as session:
        txs = await get_transactions(session, user.id, limit=100)
    page_items, total_pages, page = paginate(txs, page, 8)
    lines = ["📋 <b>Transaction History</b>\n"]
    for tx in page_items:
        sign = "+" if tx.amount > 0 else ""
        lines.append(f"{sign}{tx.amount:,} 🪙 — {tx.type.value} — {ts(tx.created_at)}")
    nav = nav_buttons(page, total_pages, "credits:history")
    kb = InlineKeyboardMarkup(
        ([nav] if nav else []) + [[InlineKeyboardButton("🔙 Back", callback_data="credits")]]
    )
    await query.edit_message_text("\n".join(lines) or "No transactions.", parse_mode="HTML", reply_markup=kb)


async def cb_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    from bot.services.referral_service import get_leaderboard
    async with get_session() as session:
        board = await get_leaderboard(session, 10)
    lines = ["🏆 <b>Referral Leaderboard</b>\n"]
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 10
    for i, (uid, cnt) in enumerate(board):
        lines.append(f"{medals[i]} User {uid} — {cnt} referral(s)")
    await query.edit_message_text(
        "\n".join(lines) or "No data yet.", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="credits")]]),
    )


async def redeem_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎟️ <b>Redeem Code</b>\n\nEnter your code:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="credits")]]),
    )
    return REDEEM_INPUT


async def redeem_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = (update.message.text or "").strip()
    user = update.effective_user
    async with get_session() as session:
        ok, msg = await redeem(session, user.id, code)
    emoji = "✅" if ok else "❌"
    await update.message.reply_text(
        f"{emoji} {msg}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="credits")]]),
    )
    return ConversationHandler.END


async def redeem_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(redeem_start, pattern="^credits:redeem_start$")],
        states={REDEEM_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, redeem_input)]},
        fallbacks=[CallbackQueryHandler(redeem_cancel, pattern="^credits$"), CommandHandler("cancel", redeem_cancel)],
        per_user=True, per_chat=True,
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(cb_credits, pattern="^credits$"))
    app.add_handler(CallbackQueryHandler(cb_daily, pattern="^credits:daily$"))
    app.add_handler(CallbackQueryHandler(cb_history, pattern=r"^credits:history:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_leaderboard, pattern="^credits:leaderboard$"))
