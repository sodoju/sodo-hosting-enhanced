from __future__ import annotations
import asyncio
import json
import logging
import uuid
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, ConversationHandler, CommandHandler,
                           CallbackQueryHandler, MessageHandler, filters)
from bot.database import get_session
from bot.services.project_service import create_project, count_user_projects
from bot.services.subscription_service import get_limits
from bot.services.hosting_service import start_project
from bot.models import Runtime
from bot.utils.validators import validate_python_file, validate_zip, validate_github_url, safe_name
from bot.utils.decorators import not_banned, require_joined

logger = logging.getLogger(__name__)

DTYPE, NAME, UPLOAD, RUNTIME, GITHUB, ENVVARS, CONFIRM = range(7)
_CANCEL_KB = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="deploy_cancel")]])


async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    user = update.effective_user
    async with get_session() as session:
        limits = await get_limits(session, user.id)
        count = await count_user_projects(session, user.id)
    if count >= limits["max_projects"]:
        text = (f"⚠️ <b>Project Limit Reached</b>\n\nPlan limit: {limits['max_projects']} project(s).\n"
                f"Current: {count}." +
                ("\n\nUpgrade to premium for more slots." if not limits["is_premium"] else ""))
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
        if query:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
        return ConversationHandler.END

    context.user_data["deploy"] = {"limits": limits}
    if not limits["is_premium"]:
        context.user_data["deploy"].update({"type": "single", "runtime": "python"})
        text = "🚀 <b>Deploy Project</b>\n\n📋 Free plan: single <code>.py</code> file.\n\nProject name:"
        if query:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=_CANCEL_KB)
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=_CANCEL_KB)
        return NAME

    text = "🚀 <b>Deploy Project</b>\n\nChoose deployment type:"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Single Python File", callback_data="dt:single")],
        [InlineKeyboardButton("📦 ZIP Archive", callback_data="dt:zip")],
        [InlineKeyboardButton("🐙 GitHub Repository", callback_data="dt:github")],
        [InlineKeyboardButton("❌ Cancel", callback_data="deploy_cancel")],
    ])
    if query:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    return DTYPE


async def on_dtype(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["deploy"]["type"] = query.data.split(":")[1]
    await query.edit_message_text("✏️ <b>Project Name</b>\n\nEnter a name:", parse_mode="HTML", reply_markup=_CANCEL_KB)
    return NAME


async def on_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = safe_name(update.message.text or "")
    if not name:
        await update.message.reply_text("❌ Invalid name. Try again:")
        return NAME
    context.user_data["deploy"]["name"] = name
    dtype = context.user_data["deploy"]["type"]
    limits = context.user_data["deploy"]["limits"]

    if dtype == "github":
        await update.message.reply_text(
            "🐙 <b>GitHub URL</b>\n\n<code>https://github.com/owner/repo</code>",
            parse_mode="HTML", reply_markup=_CANCEL_KB)
        return GITHUB

    if dtype == "zip" and limits.get("allows_nodejs"):
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🐍 Python", callback_data="rt:python"),
            InlineKeyboardButton("🟩 Node.js", callback_data="rt:nodejs"),
        ]])
        await update.message.reply_text("⚙️ Select runtime:", reply_markup=kb)
        return RUNTIME

    context.user_data["deploy"]["runtime"] = "python"
    ext = "ZIP archive" if dtype == "zip" else "<code>.py</code> file"
    await update.message.reply_text(f"📤 Send your {ext}:", parse_mode="HTML", reply_markup=_CANCEL_KB)
    return UPLOAD


async def on_runtime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["deploy"]["runtime"] = query.data.split(":")[1]
    await query.edit_message_text("📤 Send your archive or file now:", reply_markup=_CANCEL_KB)
    return UPLOAD


async def on_github(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = (update.message.text or "").strip()
    ok, err = validate_github_url(url)
    if not ok:
        await update.message.reply_text(f"❌ {err}\n\nTry again:")
        return GITHUB
    context.user_data["deploy"]["github_url"] = url
    limits = context.user_data["deploy"]["limits"]
    if limits.get("allows_nodejs"):
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🐍 Python", callback_data="rt:python"),
            InlineKeyboardButton("🟩 Node.js", callback_data="rt:nodejs"),
        ]])
        await update.message.reply_text("⚙️ Select runtime:", reply_markup=kb)
        return RUNTIME
    context.user_data["deploy"]["runtime"] = "python"
    return await _ask_envvars(update, context)


async def on_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    doc = update.message.document
    if not doc:
        await update.message.reply_text("❌ Please send a file.")
        return UPLOAD
    dtype = context.user_data["deploy"]["type"]
    limits = context.user_data["deploy"]["limits"]
    max_mb = limits["max_file_size_mb"]
    file = await doc.get_file()
    data = bytes(await file.download_as_bytearray())
    if dtype == "zip":
        ok, err = validate_zip(data, max_mb)
    else:
        ok, err = validate_python_file(data, doc.file_name or "", max_mb)
    if not ok:
        await update.message.reply_text(f"❌ {err}")
        return UPLOAD
    context.user_data["deploy"]["file_bytes"] = data
    context.user_data["deploy"]["filename"] = doc.file_name or ("main.py" if dtype == "single" else "project.zip")
    if limits.get("allows_env_vars"):
        return await _ask_envvars(update, context)
    return await _show_confirm(update, context)


async def _ask_envvars(update, context) -> int:
    await update.message.reply_text(
        "🔧 <b>Environment Variables</b> (optional)\n\n"
        "One per line: <code>KEY=value</code>\n\n"
        "Or send <code>/skip</code>",
        parse_mode="HTML", reply_markup=_CANCEL_KB,
    )
    return ENVVARS


async def on_envvars(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text.lower() in ("/skip", "skip"):
        context.user_data["deploy"]["env_vars"] = {}
    else:
        env = {}
        for line in text.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
        context.user_data["deploy"]["env_vars"] = env
    return await _show_confirm(update, context)


async def _show_confirm(update, context) -> int:
    d = context.user_data["deploy"]
    envcount = len(d.get("env_vars", {}))
    lines = [
        f"📋 <b>Deploy Summary</b>",
        f"🏷️ Name: <b>{d.get('name')}</b>",
        f"📦 Type: <b>{d.get('type', 'single').title()}</b>",
        f"⚙️ Runtime: <b>{d.get('runtime', 'python')}</b>",
    ]
    if d.get("github_url"):
        lines.append(f"🐙 Repo: <code>{d['github_url']}</code>")
    if envcount:
        lines.append(f"🔧 Env vars: <b>{envcount}</b>")
    lines.append("\nReady to deploy?")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Deploy Now", callback_data="deploy_go"),
        InlineKeyboardButton("❌ Cancel", callback_data="deploy_cancel"),
    ]])
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)
    return CONFIRM


async def on_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "deploy_cancel":
        context.user_data.pop("deploy", None)
        await query.edit_message_text("❌ Deployment cancelled.")
        return ConversationHandler.END

    await query.edit_message_text("⏳ <b>Deploying...</b>", parse_mode="HTML")
    user = update.effective_user
    d = context.user_data.pop("deploy", {})
    config = context.bot_data["config"]
    storage = config.storage_base_path
    dtype = d.get("type", "single")
    runtime = d.get("runtime", "python")
    name = d.get("name", "project")
    project_id = uuid.uuid4()
    project_dir = Path(storage) / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    entry_file = None

    try:
        if dtype == "single":
            fname = d.get("filename", "main.py")
            (project_dir / fname).write_bytes(d["file_bytes"])
            entry_file = fname

        elif dtype == "zip":
            import zipfile, io
            with zipfile.ZipFile(io.BytesIO(d["file_bytes"])) as zf:
                zf.extractall(str(project_dir))
            entry_file = _find_entry(project_dir, runtime)

        elif dtype == "github":
            proc = await asyncio.create_subprocess_exec(
                "git", "clone", "--depth=1", d["github_url"], str(project_dir),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                await query.edit_message_text(
                    f"❌ Git clone failed.\n<code>{stderr.decode()[:400]}</code>", parse_mode="HTML")
                return ConversationHandler.END
            entry_file = _find_entry(project_dir, runtime)

        if entry_file is None:
            await query.edit_message_text("❌ No entry file found (main.py / index.js).")
            return ConversationHandler.END

        env_json = json.dumps(d.get("env_vars", {})) if d.get("env_vars") else None

        async with get_session() as session:
            project = await create_project(
                session, owner_id=user.id, name=name, runtime=Runtime(runtime),
                storage_path=str(project_id), entry_file=entry_file,
                github_url=d.get("github_url"), env_vars_json=env_json,
            )
            await session.flush()
            started = await start_project(session, project, storage)
            pid = str(project.id)

        if started:
            await query.edit_message_text(
                f"✅ <b>Deployed!</b>\n\n🏷️ {name}\n🆔 <code>{pid[:8]}…</code>\n🟢 Running",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📂 My Projects", callback_data="projects"),
                    InlineKeyboardButton("🏠 Menu", callback_data="main_menu"),
                ]]),
            )
        else:
            await query.edit_message_text(
                "⚠️ Project saved but failed to start.\nTry starting it from My Projects.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📂 My Projects", callback_data="projects")]]),
            )
    except Exception as e:
        logger.exception("Deploy error user=%d", user.id)
        await query.edit_message_text(f"❌ Deployment error: {str(e)[:300]}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("deploy", None)
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Deployment cancelled.")
    elif update.message:
        await update.message.reply_text("❌ Deployment cancelled.")
    return ConversationHandler.END


def _find_entry(d: Path, runtime: str) -> str | None:
    if runtime == "python":
        for f in ("main.py", "app.py", "bot.py", "run.py"):
            if (d / f).exists():
                return f
        files = list(d.glob("*.py"))
        return files[0].name if files else None
    for f in ("index.js", "main.js", "app.js", "server.js"):
        if (d / f).exists():
            return f
    files = list(d.glob("*.js"))
    return files[0].name if files else None


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(entry, pattern="^deploy$")],
        states={
            DTYPE: [CallbackQueryHandler(on_dtype, pattern="^dt:")],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_name)],
            UPLOAD: [MessageHandler(filters.Document.ALL, on_upload)],
            RUNTIME: [CallbackQueryHandler(on_runtime, pattern="^rt:")],
            GITHUB: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_github)],
            ENVVARS: [MessageHandler(filters.TEXT, on_envvars)],
            CONFIRM: [CallbackQueryHandler(on_confirm, pattern="^deploy_(go|cancel)$")],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^deploy_cancel$"),
            CommandHandler("cancel", cancel),
        ],
        per_user=True, per_chat=True,
    )
    app.add_handler(conv)
