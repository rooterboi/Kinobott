"""Sahifalangan ro'yxatlarni tayyorlash (foydalanuvchi va admin uchun umumiy)."""
from config import PAGE_SIZE
from keyboards.common import results_kb
from utils.helpers import cache_put

HEADERS = {
    "q": "🔎 Qidiruv natijalari", "g": "🎭 Janr", "y": "📅 Yil", "top": "🔥 Eng ko'p ko'rilganlar",
    "new": "🆕 Yangi qo'shilganlar", "fav": "⭐ Saqlanganlar", "m": "🎞 Kinolar", "s": "📚 Seriallar",
}


async def render_list(db, kind, value, page, user_id=0, item_cb="show", nav_cb="lst", back=None, token=None):
    rows, total = await db.list_by(kind, value, user_id, page * PAGE_SIZE, PAGE_SIZE)
    if token is None:
        if kind in ("q", "g"):
            token = cache_put(str(value))
        elif kind == "y":
            token = str(value)
        else:
            token = "0"
    if not total:
        return "😕 Hech narsa topilmadi.", (results_kb([], kind, token, 0, 0, back=back) if back else None)
    text = f"{HEADERS[kind]}: <b>{total}</b> ta\nKerakli kontentni tanlang 👇"
    return text, results_kb(rows, kind, token, page, total, item_cb, nav_cb, back)
