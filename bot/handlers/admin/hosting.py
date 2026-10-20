from __future__ import annotations
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import get_session
from bot.services.project_service import get_all_projects, get_project, count_all_projects, add_log
from bot.services.hosting_service import start_project, stop_project, restart_project
from bot.services.admin_service import log_action
from bot.utils.decorators import owner_only
from bot.utils.formatting import project_line, STATUS_EMOJI, ts
from bot.utils.pagination import paginate, nav_buttons


@owner_only
async def cb_hosting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    page = int(parts[-1]) if len(parts) > 2 and parts[-1].isdigit() else 0
    async with get_session() as session:
        projects = await get_all_projects(session, limit=200)
        total = await count_all_projects(session)
    page_items, total_pages, page = paginate(projects, page, 8)
    lines = [f"🚀 <b>All Projects</b> ({total} total)\n"]
    buttons = []
    for p in page_items:
        e = STATUS_EMOJI.get(p.status.value, "❓")
        owner = f"@{p.owner.username}" if p.owner and p.owner.username else str(p.owner_id)
        buttons.append([InlineKeyboardButton(
            f"{e} {p.name} [{owner}]",
            callback_data=f"admin:proj:{p.id}"
        )])
    nav = nav_buttons(page, total_pages, "admin:hosting:p")
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@owner_only
async def cb_admin_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    project_id = uuid.UUID(query.data.split(":")[-1])
    async with get_session() as session:
        p = await get_project(session, project_id)
    if not p:
        await query.answer("Not found.", show_alert=True)
        return
    e = STATUS_EMOJI.get(p.status.value, "❓")
    pid = str(p.id)
    text = (
        f"🚀 <b>{p.name}</b>\n\n"
        f"Owner: {p.owner_id}\n"
        f"Status: {e} {p.status.value}\n"
        f"Runtime: {p.runtime.value}\n"
        f"Created: {ts(p.created_at)}\n"
        f"PID: {p.process_pid or '—'}\n"
        + ("⚠️ Suspended\n" if p.is_suspended else "")
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Start", callback_data=f"admin:pa:start:{pid}"),
         InlineKeyboardButton("🔄 Restart", callback_data=f"admin:pa:restart:{pid}"),
         InlineKeyboardButton("⏹️ Stop", callback_data=f"admin:pa:stop:{pid}")],
        [InlineKeyboardButton("🔇 Suspend", callback_data=f"admin:pa:suspend:{pid}"),
         InlineKeyboardButton("✅ Unsuspend", callback_data=f"admin:pa:unsuspend:{pid}")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin:hosting")],
    ]))


@owner_only
async def cb_admin_proj_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    action, project_id = parts[2], uuid.UUID(parts[3])
    config = context.bot_data["config"]
    async with get_session() as session:
        p = await get_project(session, project_id)
        if not p:
            await query.answer("Not found.", show_alert=True)
            return
        if action == "start":
            ok = await start_project(session, p, config.storage_base_path)
            msg = "Started." if ok else "Failed."
        elif action == "stop":
            await stop_project(session, p)
            msg = "Stopped."
        elif action == "restart":
            ok = await restart_project(session, p, config.storage_base_path)
            msg = "Restarted." if ok else "Failed."
        elif action == "suspend":
            p.is_suspended = True
            await stop_project(session, p)
            msg = "Suspended."
        elif action == "unsuspend":
            p.is_suspended = False
            msg = "Unsuspended."
        else:
            msg = "Unknown action."
        await log_action(session, config.owner_id, f"admin_proj_{action}", "project", str(project_id))
    await query.edit_message_text(
        f"✅ {msg}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data=f"admin:proj:{project_id}"),
        ]]),
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_hosting, pattern=r"^admin:hosting"))
    app.add_handler(CallbackQueryHandler(cb_admin_project, pattern=r"^admin:proj:[0-9a-f\-]+$"))
    app.add_handler(CallbackQueryHandler(cb_admin_proj_action, pattern=r"^admin:pa:"))
