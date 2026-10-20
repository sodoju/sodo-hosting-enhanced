from __future__ import annotations
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin:dashboard"),
         InlineKeyboardButton("👥 Users", callback_data="admin:users")],
        [InlineKeyboardButton("🚀 Hosting", callback_data="admin:hosting"),
         InlineKeyboardButton("🪙 Credits", callback_data="admin:credits")],
        [InlineKeyboardButton("💎 Premium", callback_data="admin:premium"),
         InlineKeyboardButton("🔐 Force Join", callback_data="admin:fj")],
        [InlineKeyboardButton("🎟️ Redeem Codes", callback_data="admin:redeem"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin:settings"),
         InlineKeyboardButton("🛡️ Activity Logs", callback_data="admin:activity")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")],
    ])


def force_join_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Channel", callback_data="admin:fj:add"),
         InlineKeyboardButton("➖ Remove Channel", callback_data="admin:fj:remove_list")],
        [InlineKeyboardButton("📋 List Channels", callback_data="admin:fj:list")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")],
    ])


def user_actions(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Credits", callback_data=f"au:{uid}:add"),
         InlineKeyboardButton("➖ Deduct Credits", callback_data=f"au:{uid}:deduct")],
        [InlineKeyboardButton("💎 Grant Premium", callback_data=f"au:{uid}:premium"),
         InlineKeyboardButton("🔧 Revoke Premium", callback_data=f"au:{uid}:revoke_premium")],
        [InlineKeyboardButton("🚫 Ban", callback_data=f"au:{uid}:ban"),
         InlineKeyboardButton("✅ Unban", callback_data=f"au:{uid}:unban")],
        [InlineKeyboardButton("📂 Projects", callback_data=f"au:{uid}:projects"),
         InlineKeyboardButton("🔙 Back", callback_data="admin:users")],
    ])
