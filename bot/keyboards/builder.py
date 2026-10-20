from __future__ import annotations
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=data) for label, data in row]
        for row in rows
    ])


def url_btn(label: str, url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(label, url=url)


def back(target: str = "main_menu") -> list[list[tuple[str, str]]]:
    return [[(f"🔙 Back", target)]]


def confirm_cancel(confirm_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirm", callback_data=confirm_cb),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"),
    ]])
