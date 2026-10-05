"""Maxfiy /rooter (nomi sozlanadi) → PIN → Bot Token → yangi sub-bot.

MUHIM: is_parent bayrog'i ContextMiddleware dan keladi. Child botlarda u False,
shuning uchun bu yerdagi filtr hech qachon ishlamaydi — sub-botda yangi bot ochib bo'lmaydi.
"""
import hmac
import time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DEFAULT_ROOTER_CMD, DEFAULT_ROOTER_PIN
from services.manager import ChildBotError
from states.states import RooterSt

router = Router()
MAX_TRIES, BLOCK_SEC = 3, 600
_attempts: dict[int, list] = {}          # user_id -> [xato_soni, bloklangan_vaqt]


async def rooter_filter(message: Message, db, is_parent: bool) -> bool:
    if not is_parent or not message.text or not message.text.startswith("/"):
        return False
    cmd = message.text[1:].split()[0].split("@")[0].lower()
    return cmd == (await db.get_setting("rooter_cmd", DEFAULT_ROOTER_CMD))


def cancel_kb():
    b = InlineKeyboardBuilder()
    b.button(text="❌ Bekor qilish", callback_data="rooter:cancel")
    return b.as_markup()


@router.message(rooter_filter)
async def rooter_cmd(message: Message, state: FSMContext):
    rec = _attempts.get(message.from_user.id)
    if rec and rec[1] > time.time():
        await message.answer("⛔ Ko'p marta xato kiritdingiz. Keyinroq urinib ko'ring.")
        return
    await state.set_state(RooterSt.pin)
    await message.answer("🔐 PIN-kodni kiriting:", reply_markup=cancel_kb())


@router.callback_query(F.data == "rooter:cancel")
async def rooter_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Bekor qilindi.")
    await call.answer()


@router.message(RooterSt.pin, F.text)
async def rooter_pin(message: Message, state: FSMContext, db, is_parent: bool):
    if not is_parent:
        await state.clear()
        return
    try:
        await message.delete()          # PIN chatda qolib ketmasin
    except Exception:
        pass
    uid = message.from_user.id
    pin = await db.get_setting("rooter_pin", DEFAULT_ROOTER_PIN)
    if hmac.compare_digest(message.text.strip().encode(), pin.encode()):
        _attempts.pop(uid, None)
        await state.set_state(RooterSt.token)
        await message.answer("✅ PIN to'g'ri.\n\n🤖 Yangi bot <b>tokenini</b> yuboring (@BotFather dan olingan):",
                             reply_markup=cancel_kb())
        return
    rec = _attempts.setdefault(uid, [0, 0])
    rec[0] += 1
    if rec[0] >= MAX_TRIES:
        rec[0], rec[1] = 0, time.time() + BLOCK_SEC
        await state.clear()
        await message.answer("⛔ PIN 3 marta xato kiritildi. 10 daqiqaga bloklandingiz.")
    else:
        await message.answer(f"❌ PIN noto'g'ri. Qolgan urinishlar: {MAX_TRIES - rec[0]}")


@router.message(RooterSt.token, F.text)
async def rooter_token(message: Message, state: FSMContext, manager, is_parent: bool):
    if not is_parent:
        await state.clear()
        return
    token = message.text.strip()
    try:
        await message.delete()          # token chatda qolmasin
    except Exception:
        pass
    wait = await message.answer("⏳ Token tekshirilmoqda...")
    try:
        rt = await manager.create_child(token, owner_id=message.from_user.id)
    except ChildBotError as e:
        await wait.edit_text(f"❌ {e}\n\nQayta token yuboring yoki /cancel", reply_markup=cancel_kb())
        return
    await state.clear()
    await wait.edit_text(
        f"✅ Yangi kino bot ishga tushdi: @{rt.username}\n\n"
        f"Siz uning admini bo'ldingiz — botga o'tib /admin ni yuboring.\n"
        f"ℹ️ Sub-botda yangi bot ochish imkoniyati yo'q.")
