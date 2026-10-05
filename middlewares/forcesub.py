"""Majburiy obuna: admin qo'shgan kanallarga obuna bo'lmaguncha bot ishlamaydi."""
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from keyboards.common import subscribe_kb
from utils.subscription import get_missing


class ForceSubMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data: dict):
        if data.get("is_admin"):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and (event.data or "").startswith("check_sub"):
            return await handler(event, data)
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)
        bot, db = data["bot"], data["db"]
        missing = await get_missing(bot, db, user.id)
        if not missing:
            return await handler(event, data)

        # Deep-link kodini saqlab qolamiz: obunadan keyin kino ochiladi
        code = ""
        if isinstance(event, Message) and (event.text or "").startswith("/start "):
            arg = event.text.split(maxsplit=1)[1].strip()
            code = arg if arg.isdigit() else ""
        text = "🔒 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling, so'ng «✅ Tekshirish» tugmasini bosing:"
        kb = subscribe_kb(missing, code)
        if isinstance(event, CallbackQuery):
            await event.answer("❗ Avval kanallarga obuna bo'ling", show_alert=True)
            await event.message.answer(text, reply_markup=kb)
        else:
            await event.answer(text, reply_markup=kb)
        return None
