from __future__ import annotations
import asyncio
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import Config
from bot.database import init_db

logging.basicConfig(format="%(asctime)s [WORKER] %(name)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = Config.from_env()
    init_db(config.database_url)
    logger.info("Worker started. Poll interval: %ds", config.job_poll_interval)
    while True:
        await asyncio.sleep(config.job_poll_interval)


if __name__ == "__main__":
    asyncio.run(main())
