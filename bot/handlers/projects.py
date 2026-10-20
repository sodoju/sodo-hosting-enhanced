from __future__ import annotations
import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import get_session
from bot.services.project_service import get_user_projects, get_project, get_recent_logs, add_log
from bot.services.hosting_service import start_project, stop_project, restart_project
from bot.utils.formatting import project_line, ts, truncate, STATUS_EMOJI
from bot.utils.pagination import paginate, nav_buttons

logger = logging.getLogger(__name__)


async def cb_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    parts = query.data.split(":")
    page = int(parts[1]) if len(parts) > 1 else 0

    async with get_session() as session:
        projects = await get_user_projects(session, user.id)

    if not projects:
        await query.edit_message_text(
            "📂 <b>My Projects</b>\n\nYou have no projects yet.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🚀 Deploy Now", callback_data="deploy"),
                InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            ]]),
        )
        return

    page_items, total_pages, page = paginate(projects, page, 5)
    lines = [f"📂 <b>My Projects</b> ({len(projects)} total)\n"]
    buttons = []
    for p in page_items:
        lines.append(project_line(p))
        buttons.append([InlineKeyboardButton(
            f"{STATUS_EMOJI.get(p.status.value, '❓')} {p.name}",
            callback_data=f"project:{p.id}"
        )])

    nav = nav_buttons(page, total_pages, "projects")
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])

    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cb_project_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    project_id = uuid.UUID(query.data.split(":")[1])

    async with get_session() as session:
        p = await get_project(session, project_id, user.id)
    if not p:
        await query.answer("Project not found.", show_alert=True)
        return

    emoji = STATUS_EMOJI.get(p.status.value, "❓")
    text = (
        f"📁 <b>{p.name}</b>\n\n"
        f"🆔 <code>{str(p.id)[:8]}…</code>\n"
        f"⚙️ Runtime: {p.runtime.value.upper()}\n"
        f"📊 Status: {emoji} {p.status.value}\n"
        f"📅 Created: {ts(p.created_at)}\n"
        + (f"🐙 Repo: <code>{p.github_url}</code>\n" if p.github_url else "")
        + (f"⚠️ <i>Suspended by admin</i>\n" if p.is_suspended else "")
    )
    pid = str(p.id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Start", callback_data=f"pa:start:{pid}"),
         InlineKeyboardButton("🔄 Restart", callback_data=f"pa:restart:{pid}"),
         InlineKeyboardButton("⏹️ Stop", callback_data=f"pa:stop:{pid}")],
        [InlineKeyboardButton("📜 Logs", callback_data=f"pa:logs:{pid}"),
         InlineKeyboardButton("🗑️ Delete", callback_data=f"pa:delete_confirm:{pid}")],
        [InlineKeyboardButton("🔙 Back", callback_data="projects")],
    ])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def cb_project_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    action = query.data.split(":")[1]

    async with get_session() as session:
        projects = await get_user_projects(session, user.id)

    if not projects:
        await query.answer("No projects found.", show_alert=True)
        return

    buttons = [[InlineKeyboardButton(
        f"{STATUS_EMOJI.get(p.status.value, '❓')} {p.name}",
        callback_data=f"pa:{action}:{p.id}"
    )] for p in projects]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    await query.edit_message_text(
        f"Select a project to <b>{action}</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cb_project_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    parts = query.data.split(":")
    action = parts[1]
    project_id = uuid.UUID(parts[2])
    config = context.bot_data["config"]

    if action == "delete_confirm":
        await query.edit_message_text(
            "⚠️ <b>Delete Project</b>\n\nThis is irreversible. Confirm?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🗑️ Yes, Delete", callback_data=f"pa:delete:{project_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"project:{project_id}"),
            ]]),
        )
        return

    if action == "logs":
        async with get_session() as session:
            p = await get_project(session, project_id, user.id)
            if not p:
                await query.answer("Not found.", show_alert=True)
                return
            entries = await get_recent_logs(session, project_id, 30)
            log_path = None
            import os
            path = os.path.join(config.storage_base_path, str(project_id), "runtime.log")
            if os.path.exists(path):
                with open(path, "rb") as f:
                    f.seek(max(0, os.path.getsize(path) - 4000))
                    log_path = f.read().decode("utf-8", errors="replace")

        db_logs = "\n".join(e.content for e in entries[-20:])
        file_logs = log_path or "(no runtime output yet)"
        text = (
            f"📜 <b>Logs: {p.name}</b>\n\n"
            f"<b>System events:</b>\n<pre>{db_logs or '—'}</pre>\n\n"
            f"<b>Runtime output:</b>\n<pre>{truncate(file_logs, 1500)}</pre>"
        )
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"project:{project_id}")]]),
        )
        return

    async with get_session() as session:
        p = await get_project(session, project_id, user.id)
        if not p:
            await query.answer("Project not found.", show_alert=True)
            return
        if p.is_suspended:
            await query.answer("Project is suspended by admin.", show_alert=True)
            return

        msg = ""
        if action == "start":
            ok = await start_project(session, p, config.storage_base_path)
            msg = "🟢 Started." if ok else "❌ Failed to start."
        elif action == "stop":
            await stop_project(session, p)
            msg = "🔴 Stopped."
        elif action == "restart":
            ok = await restart_project(session, p, config.storage_base_path)
            msg = "🔄 Restarted." if ok else "❌ Restart failed."
        elif action == "status":
            e = STATUS_EMOJI.get(p.status.value, "❓")
            pid_str = f" (PID {p.process_pid})" if p.process_pid else ""
            msg = f"📊 Status: {e} {p.status.value}{pid_str}"
        elif action == "delete":
            import shutil, os
            path = os.path.join(config.storage_base_path, str(project_id))
            await stop_project(session, p)
            await session.delete(p)
            try:
                shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass
            await query.edit_message_text("🗑️ Project deleted.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📂 Projects", callback_data="projects")]]))
            return

    await query.edit_message_text(
        f"<b>{p.name}</b>\n\n{msg}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data=f"project:{project_id}"),
        ]]),
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(cb_projects, pattern=r"^projects(:\d+)?$"))
    app.add_handler(CallbackQueryHandler(cb_project_pick, pattern=r"^project_pick:"))
    app.add_handler(CallbackQueryHandler(cb_project_detail, pattern=r"^project:[0-9a-f\-]+$"))
    app.add_handler(CallbackQueryHandler(cb_project_action, pattern=r"^pa:"))
