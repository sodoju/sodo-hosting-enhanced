from __future__ import annotations
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(is_premium: bool = False, is_owner: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🚀 Deploy Project", callback_data="deploy"),
            InlineKeyboardButton("📂 My Projects", callback_data="projects"),
        ],
        [
            InlineKeyboardButton("▶️ Start", callback_data="project_pick:start"),
            InlineKeyboardButton("🔄 Restart", callback_data="project_pick:restart"),
            InlineKeyboardButton("⏹️ Stop", callback_data="project_pick:stop"),
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="project_pick:status"),
            InlineKeyboardButton("📜 Logs", callback_data="project_pick:logs"),
        ],
        [
            InlineKeyboardButton("💎 Premium Plans", callback_data="premium"),
            InlineKeyboardButton("🪙 Earn Credits", callback_data="credits"),
        ],
        [
            InlineKeyboardButton("👤 My Account", callback_data="account"),
            InlineKeyboardButton("🆘 Support", callback_data="support"),
        ],
    ]
    if is_owner:
        rows.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)
