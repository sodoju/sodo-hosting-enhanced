from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_id: int
    database_url: str
    hosting_api_url: str | None
    hosting_api_token: str | None
    welcome_credits: int
    daily_reward_credits: int
    referral_reward_credits: int
    free_plan_max_projects: int
    free_plan_max_file_size_mb: int
    max_log_lines: int
    job_poll_interval: int
    storage_base_path: str

    @classmethod
    def from_env(cls) -> "Config":
        bot_token = os.environ.get("BOT_TOKEN", "")
        if not bot_token:
            raise ValueError("BOT_TOKEN is required")
        owner_raw = os.environ.get("OWNER_ID", "")
        if not owner_raw:
            raise ValueError("OWNER_ID is required")
        try:
            owner_id = int(owner_raw)
        except ValueError:
            raise ValueError("OWNER_ID must be an integer")
        database_url = os.environ.get("DATABASE_URL", "")
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        return cls(
            bot_token=bot_token,
            owner_id=owner_id,
            database_url=database_url,
            hosting_api_url=os.environ.get("HOSTING_API_URL"),
            hosting_api_token=os.environ.get("HOSTING_API_TOKEN"),
            welcome_credits=int(os.environ.get("WELCOME_CREDITS", "50")),
            daily_reward_credits=int(os.environ.get("DAILY_REWARD_CREDITS", "10")),
            referral_reward_credits=int(os.environ.get("REFERRAL_REWARD_CREDITS", "25")),
            free_plan_max_projects=int(os.environ.get("FREE_PLAN_MAX_PROJECTS", "1")),
            free_plan_max_file_size_mb=int(os.environ.get("FREE_PLAN_MAX_FILE_SIZE_MB", "1")),
            max_log_lines=int(os.environ.get("MAX_LOG_LINES", "100")),
            job_poll_interval=int(os.environ.get("JOB_POLL_INTERVAL", "5")),
            storage_base_path=os.environ.get("STORAGE_BASE_PATH", "/tmp/sodo_projects"),
        )
