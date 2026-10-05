from aiogram.exceptions import TelegramBadRequest


async def edit_or_send(call, text, kb=None):
    """Xabar matn bo'lsa tahrirlaydi, rasm bo'lsa yangisini yuboradi."""
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=kb)
