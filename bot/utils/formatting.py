from __future__ import annotations
from datetime import datetime, timezone

STATUS_EMOJI = {
    "running": "🟢", "stopped": "🔴", "pending": "🟡",
    "failed": "🔴", "suspended": "⚫", "queued": "🟡",
    "building": "🔵", "success": "🟢", "cancelled": "⚫",
}

PLAN_EMOJI = {"Free": "⚪", "premium": "💎", "basic": "⭐", "pro": "🔥"}

HEADER = (
    "╔══════════════════════════════════╗\n"
    "║   🚀  <b>SODO HOSTING</b>  ⚡           ║\n"
    "║   Premium Telegram Hosting       ║\n"
    "╚══════════════════════════════════╝"
)


def ts(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def credits_fmt(n: int) -> str:
    return f"🪙 {n:,}"


def project_line(p) -> str:
    e = STATUS_EMOJI.get(p.status.value, "❓")
    return f"{e} <b>{p.name}</b> [{p.runtime.value.upper()}]"


def truncate(text: str, max_len: int = 3500) -> str:
    if len(text) <= max_len:
        return text
    return "...\n" + text[-(max_len - 4):]
