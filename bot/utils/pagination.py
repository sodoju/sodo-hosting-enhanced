from __future__ import annotations
import math
from typing import Any
from telegram import InlineKeyboardButton


def paginate(items: list[Any], page: int, page_size: int = 5) -> tuple[list[Any], int, int]:
    total_pages = max(1, math.ceil(len(items) / page_size))
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    return items[start:start + page_size], total_pages, page


def nav_buttons(page: int, total_pages: int, prefix: str) -> list[InlineKeyboardButton]:
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("◀️", callback_data=f"{prefix}:{page - 1}"))
    if total_pages > 1:
        buttons.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("▶️", callback_data=f"{prefix}:{page + 1}"))
    return buttons
