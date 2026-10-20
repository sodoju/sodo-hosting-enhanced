from __future__ import annotations
import asyncio
import logging
import sys
from pathlib import Path
from telegram.ext import Application, ApplicationBuilder, ContextTypes
from telegram import Update
from bot.config import Config
from bot.database import init_db, create_tables, get_session

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    config: Config = app.bot_data["config"]
    await create_tables()
    async with get_session() as session:
        from bot.models import Plan
        from sqlalchemy import select
        existing = (await session.execute(select(Plan).limit(1))).scalar_one_or_none()
        if existing is None:
            session.add(Plan(
                name="premium_basic",
                display_name="⭐ Premium Basic",
                max_projects=5,
                max_file_size_mb=10,
                max_storage_mb=100,
                allows_zip=True,
                allows_github=True,
                allows_nodejs=True,
                allows_multi_file=True,
                allows_env_vars=True,
                duration_days=30,
                price_credits=500,
                is_active=True,
            ))
            session.add(Plan(
                name="premium_pro",
                display_name="🔥 Premium Pro",
                max_projects=20,
                max_file_size_mb=50,
                max_storage_mb=500,
                allows_zip=True,
                allows_github=True,
                allows_nodejs=True,
                allows_multi_file=True,
                allows_env_vars=True,
                duration_days=None,
                price_credits=2000,
                is_active=True,
            ))
    Path(config.storage_base_path).mkdir(parents=True, exist_ok=True)
    logger.info("SODO HOSTING started. Owner: %d", config.owner_id)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Update caused error:", exc_info=context.error)
    if isinstance(update, Update):
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            try:
                await msg.reply_text("❌ An internal error occurred. Please try again.")
            except Exception:
                pass


def build_app() -> Application:
    config = Config.from_env()
    init_db(config.database_url)
    app = (
        ApplicationBuilder()
        .token(config.bot_token)
        .post_init(post_init)
        .build()
    )
    app.bot_data["config"] = config
    app.add_error_handler(error_handler)

    import bot.handlers.start as h_start
    import bot.handlers.deploy as h_deploy
    import bot.handlers.projects as h_projects
    import bot.handlers.credits as h_credits
    import bot.handlers.premium as h_premium
    import bot.handlers.account as h_account
    import bot.handlers.support as h_support
    import bot.handlers.admin.panel as a_panel
    import bot.handlers.admin.dashboard as a_dash
    import bot.handlers.admin.activity as a_activity
    import bot.handlers.admin.users as a_users
    import bot.handlers.admin.force_join as a_fj
    import bot.handlers.admin.broadcast as a_bc
    import bot.handlers.admin.redeem as a_redeem
    import bot.handlers.admin.hosting as a_hosting
    import bot.handlers.admin.credits as a_credits
    import bot.handlers.admin.premium as a_premium
    import bot.handlers.admin.settings as a_settings

    for mod in [
        h_start, h_deploy, h_projects, h_credits, h_premium, h_account, h_support,
        a_panel, a_dash, a_activity, a_users, a_fj, a_bc, a_redeem,
        a_hosting, a_credits, a_premium, a_settings,
    ]:
        mod.register(app)

    return app


def main() -> None:
    app = build_app()
    logger.info("Starting polling...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
