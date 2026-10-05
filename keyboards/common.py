"""Foydalanuvchi klaviaturalari."""
import math

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import PAGE_SIZE


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🔍 Qidiruv"), KeyboardButton(text="🎭 Janrlar")],
        [KeyboardButton(text="📅 Yillar"), KeyboardButton(text="🔥 Top")],
        [KeyboardButton(text="🆕 Yangi"), KeyboardButton(text="⭐ Saqlanganlar")],
        [KeyboardButton(text="🎲 Tasodifiy"), KeyboardButton(text="ℹ️ Yordam")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="👑 Admin panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def subscribe_kb(channels: list, code: str = "") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for ch in channels:
        if ch.get("link"):
            b.button(text=f"📢 {ch['title']}", url=ch["link"])
    b.button(text="✅ Tekshirish", callback_data=f"check_sub:{code}" if code else "check_sub")
    b.adjust(1)
    return b.as_markup()


def results_kb(rows, kind, token, page, total, item_cb="show", nav_cb="lst", back=None):
    """Sahifalangan natijalar ro'yxati."""
    b = InlineKeyboardBuilder()
    for r in rows:
        icon = "🎬" if r["type"] == "movie" else "📺"
        label = f"{icon} {r['title']}" + (f" ({r['year']})" if r.get("year") else "") + f" • {r['code']}"
        b.button(text=label[:60], callback_data=f"{item_cb}:{r['id']}")
    b.adjust(1)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"{nav_cb}:{kind}:{token}:{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="noop"))
        if page + 1 < pages:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"{nav_cb}:{kind}:{token}:{page + 1}"))
        b.row(*nav)
    if back:
        b.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=back))
    return b.as_markup()
