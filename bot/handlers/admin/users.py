from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, CallbackQueryHandler, ConversationHandler,
                           MessageHandler, filters, CommandHandler)
from bot.database import get_session
from bot.services.user_service import get_user, search_users, ban_user, unban_user
from bot.services.credit_service import add_credits, deduct_credits, get_balance, TransactionType
from bot.services.subscription_service import grant, revoke, get_active
from bot.services.project_service import get_user_projects
from bot.services.admin_service import log_action
from bot.keyboards.admin import admin_menu, user_actions
from bot.utils.decorators import owner_only
from bot.utils.formatting import ts, credits_fmt

logger = logging.getLogger(__name__)
SEARCH, AMOUNT_INPUT, BAN_REASON, CONFIRM_OP = range(4)


@owner_only
async def cb_users_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👥 <b>User Management</b>\n\nEnter Telegram ID or @username to search:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
        ]]),
    )
    return SEARCH


@owner_only
async def on_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query_text = (update.message.text or "").strip()
    async with get_session() as session:
        users = await search_users(session, query_text)
    if not users:
        await update.message.reply_text(
            "❌ No users found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        )
        return ConversationHandler.END
    buttons = [[InlineKeyboardButton(
        f"{'🚫 ' if u.is_banned else ''}{u.first_name} (@{u.username or '—'}) [{u.id}]",
        callback_data=f"admin:view_user:{u.id}",
    )] for u in users[:10]]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
    await update.message.reply_text(
        f"🔍 Found {len(users)} user(s):",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ConversationHandler.END


@owner_only
async def cb_view_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    uid = int(query.data.split(":")[-1])
    async with get_session() as session:
        user = await get_user(session, uid)
        if not user:
            await query.answer("User not found.", show_alert=True)
            return
        balance = await get_balance(session, uid)
        sub = await get_active(session, uid)
        proj_count = len(await get_user_projects(session, uid))

    plan_line = f"💎 {sub.plan.display_name}" if sub and sub.plan else "⚪ Free"
    text = (
        f"👤 <b>User Profile</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📝 Name: {user.first_name} {user.last_name or ''}\n"
        + (f"🔗 Username: @{user.username}\n" if user.username else "")
        + f"📅 Joined: {ts(user.created_at)}\n"
        f"🕐 Last active: {ts(user.last_active_at)}\n"
        f"{'🚫 BANNED' if user.is_banned else '✅ Active'}"
        + (f"\n  Reason: {user.ban_reason}" if user.is_banned else "")
        + f"\n\n{plan_line}\n"
        f"🪙 Balance: {credits_fmt(balance)}\n"
        f"📁 Projects: {proj_count}"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=user_actions(uid))


@owner_only
async def cb_user_action_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    uid, action = int(parts[1]), parts[2]
    context.user_data["admin_action"] = {"uid": uid, "action": action}

    if action in ("add", "deduct"):
        await query.edit_message_text(
            f"💰 Enter amount to {'add to' if action == 'add' else 'deduct from'} user <code>{uid}</code>:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")]]),
        )
        return AMOUNT_INPUT
    if action == "ban":
        await query.edit_message_text(
            f"🚫 Enter ban reason for user <code>{uid}</code>:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")]]),
        )
        return BAN_REASON
    if action == "unban":
        context.user_data["admin_action"]["ready"] = True
        await query.edit_message_text(
            f"✅ Unban user <code>{uid}</code>? Confirm:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Confirm", callback_data="admin_do_action"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"),
            ]]),
        )
        return CONFIRM_OP
    if action == "premium":
        await query.edit_message_text(
            f"💎 Enter plan_id and optional days for user <code>{uid}</code>:\n\n"
            "Format: <code>plan_id days</code>\n"
            "Example: <code>1 30</code> (plan 1, 30 days)",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")]]),
        )
        return AMOUNT_INPUT
    if action == "revoke_premium":
        context.user_data["admin_action"]["ready"] = True
        await query.edit_message_text(
            f"🔧 Revoke premium for user <code>{uid}</code>?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Confirm", callback_data="admin_do_action"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"),
            ]]),
        )
        return CONFIRM_OP
    if action == "projects":
        async with get_session() as session:
            projects = await get_user_projects(session, uid)
        from bot.utils.formatting import project_line
        lines = [f"📂 <b>Projects for {uid}</b>\n"]
        for p in projects:
            lines.append(project_line(p))
        await query.edit_message_text(
            "\n".join(lines) or "No projects.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data=f"admin:view_user:{uid}")
            ]]),
        )
        return ConversationHandler.END
    return ConversationHandler.END


@owner_only
async def on_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.get("admin_action", {})
    uid = data.get("uid")
    action = data.get("action")
    text = (update.message.text or "").strip()
    config = context.bot_data["config"]

    if action in ("add", "deduct"):
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Enter a positive integer.")
            return AMOUNT_INPUT
        async with get_session() as session:
            try:
                if action == "add":
                    new_bal = await add_credits(session, uid, amount, TransactionType.admin_add,
                                               "Admin credit", config.owner_id)
                else:
                    new_bal = await deduct_credits(session, uid, amount, TransactionType.admin_deduct,
                                                  "Admin deduction", config.owner_id)
                await log_action(session, config.owner_id, f"credits_{action}", "user", str(uid),
                                 f"amount={amount}")
            except ValueError as e:
                await update.message.reply_text(f"❌ {e}")
                return ConversationHandler.END
        sign = "+" if action == "add" else "-"
        await update.message.reply_text(
            f"✅ {sign}{amount:,} credits for user {uid}. New balance: {new_bal:,}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 User", callback_data=f"admin:view_user:{uid}"),
            ]]),
        )

    elif action == "premium":
        parts = text.split()
        try:
            plan_id = int(parts[0])
            days = int(parts[1]) if len(parts) > 1 else None
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Format: plan_id [days]. Example: 1 30")
            return AMOUNT_INPUT
        async with get_session() as session:
            sub = await grant(session, uid, plan_id, config.owner_id, days)
            await log_action(session, config.owner_id, "grant_premium", "user", str(uid),
                             f"plan={plan_id} days={days}")
        await update.message.reply_text(
            f"✅ Premium granted to user {uid}.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 User", callback_data=f"admin:view_user:{uid}"),
            ]]),
        )

    context.user_data.pop("admin_action", None)
    return ConversationHandler.END


@owner_only
async def on_ban_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reason = (update.message.text or "").strip()
    data = context.user_data.get("admin_action", {})
    uid = data.get("uid")
    config = context.bot_data["config"]
    async with get_session() as session:
        await ban_user(session, uid, reason)
        await log_action(session, config.owner_id, "ban_user", "user", str(uid), reason)
    await update.message.reply_text(
        f"🚫 User {uid} banned.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 User", callback_data=f"admin:view_user:{uid}"),
        ]]),
    )
    context.user_data.pop("admin_action", None)
    return ConversationHandler.END


@owner_only
async def on_confirm_op(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = context.user_data.pop("admin_action", {})
    uid = data.get("uid")
    action = data.get("action")
    config = context.bot_data["config"]
    if action == "unban":
        async with get_session() as session:
            await unban_user(session, uid)
            await log_action(session, config.owner_id, "unban_user", "user", str(uid))
        await query.edit_message_text(
            f"✅ User {uid} unbanned.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 User", callback_data=f"admin:view_user:{uid}"),
            ]]),
        )
    elif action == "revoke_premium":
        async with get_session() as session:
            await revoke(session, uid)
            await log_action(session, config.owner_id, "revoke_premium", "user", str(uid))
        await query.edit_message_text(
            f"✅ Premium revoked for user {uid}.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 User", callback_data=f"admin:view_user:{uid}"),
            ]]),
        )
    return ConversationHandler.END


async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("admin_action", None)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("⚙️ <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_menu())
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_users_entry, pattern="^admin:users$"),
            CallbackQueryHandler(cb_user_action_entry, pattern=r"^au:\d+:"),
        ],
        states={
            SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_search)],
            AMOUNT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_amount_input)],
            BAN_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_ban_reason)],
            CONFIRM_OP: [CallbackQueryHandler(on_confirm_op, pattern="^admin_do_action$")],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_admin, pattern="^cancel_action$"),
            CommandHandler("cancel", cancel_admin),
        ],
        per_user=True, per_chat=True,
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(cb_view_user, pattern=r"^admin:view_user:\d+$"))
