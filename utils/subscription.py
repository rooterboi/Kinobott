"""Majburiy obuna tekshiruvi."""
from aiogram.exceptions import TelegramAPIError


async def get_missing(bot, db, user_id: int) -> list:
    """Foydalanuvchi obuna bo'lmagan majburiy kanallar ro'yxati."""
    missing = []
    for ch in await db.list_channels("force", only_active=True):
        try:
            m = await bot.get_chat_member(ch["chat_id"], user_id)
        except TelegramAPIError:
            continue  # bot kanaldan chiqarilgan bo'lsa ham foydalanuvchi qamalib qolmasin
        if m.status in ("left", "kicked") or (
            m.status == "restricted" and getattr(m, "is_member", True) is False
        ):
            missing.append(ch)
    return missing
