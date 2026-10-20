from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from bot.database import get_session
from bot.services.user_service import get_or_create_user, get_user
from bot.services.force_join_service import check_membership, get_active_channels
from bot.services.credit_service import add_credits, TransactionType
from bot.services.referral_service import find_by_code, process_referral
from bot.services.subscription_service import is_premium
from bot.keyboards.main_menu import main_menu
from bot.utils.formatting import HEADER

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    ref_code = None
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            ref_code = arg[4:]

    async with get_session() as session:
        db_user, created = await get_or_create_user(
            session, user.id, user.username, user.first_name, user.last_name,
            referral_code=ref_code,
        )
        if db_user.is_banned:
            await update.message.reply_text(
                f"🚫 <b>Account Banned</b>\n\n<i>{db_user.ban_reason or 'Contact support.'}</i>",
                parse_mode="HTML",
            )
            return
        config = context.bot_data["config"]
        if created:
            await add_credits(session, user.id, config.welcome_credits,
                              TransactionType.welcome, "Welcome bonus")
            if ref_code:
                link = await find_by_code(session, ref_code)
                if link and link.user_id != user.id:
                    await process_referral(session, link.user_id, user.id,
                                           config.referral_reward_credits)

        channels = await get_active_channels(session)
        if channels:
            statuses = await check_membership(context.bot, session, user.id)
            missing = [s for s in statuses if not s.is_member]
            if missing:
                await _show_join_screen(update, missing)
                return

        premium = await is_premium(session, user.id)

    greeting = "🎉 Welcome to <b>SODO HOSTING</b>!" if created else f"👋 Welcome back, <b>{user.first_name}</b>!"
    await update.message.reply_text(
        f"{HEADER}\n\n{greeting}\n\n⚡ Deploy and manage your projects right from Telegram.",
        parse_mode="HTML",
        reply_markup=main_menu(premium, user.id == config.owner_id),
    )


async def send_join_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    async with get_session() as session:
        statuses = await check_membership(context.bot, session, user.id)
        missing = [s for s in statuses if not s.is_member]
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if msg:
        await _show_join_screen_msg(msg, missing)


async def _show_join_screen(update, missing) -> None:
    await _show_join_screen_msg(update.message, missing)


async def _show_join_screen_msg(msg, missing) -> None:
    buttons = []
    for s in missing:
        ch = s.channel
        url = f"https://t.me/{ch.username}" if ch.username else ch.invite_url
        if url:
            buttons.append([InlineKeyboardButton(f"📢 Join {ch.display_name}", url=url)])
    buttons.append([InlineKeyboardButton("🟢 ✅ I'VE JOINED — VERIFY", callback_data="verify_join")])
    await msg.reply_text(
        "🔐 <b>SODO HOSTING — ACCESS VERIFICATION</b>\n\n"
        "Join the required channels below to unlock hosting features.\n\n"
        "After joining all channels, tap <b>✅ VERIFY</b>.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cb_verify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    config = context.bot_data["config"]
    async with get_session() as session:
        db_user = await get_user(session, user.id)
        if db_user and db_user.is_banned:
            await query.edit_message_text("🚫 Your account is banned.")
            return
        statuses = await check_membership(context.bot, session, user.id)
        missing = [s for s in statuses if not s.is_member]
        if missing:
            names = ", ".join(s.channel.display_name for s in missing)
            await query.answer(f"❌ Still not joined: {names}", show_alert=True)
            return
        premium = await is_premium(session, user.id)

    await query.edit_message_text(
        "✅ <b>Verification successful!</b>\n\nWelcome to SODO HOSTING!",
        parse_mode="HTML",
    )
    await query.message.reply_text(
        f"{HEADER}\n\n👋 Welcome, <b>{user.first_name}</b>!\n\nSelect an option:",
        parse_mode="HTML",
        reply_markup=main_menu(premium, user.id == config.owner_id),
    )


async def cb_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    config = context.bot_data["config"]
    async with get_session() as session:
        premium = await is_premium(session, user.id)
    await query.edit_message_text(
        f"🏠 <b>Main Menu</b>\n\nSelect an option:",
        parse_mode="HTML",
        reply_markup=main_menu(premium, user.id == config.owner_id),
    )


def register(app) -> None:
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(cb_verify, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(cb_main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^noop$"))
