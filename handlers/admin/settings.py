"""Sozlamalar: yashirin buyruq va PIN (faqat Parent), adminlar, salomlashuv, himoya."""
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DEFAULT_ROOTER_CMD, DEFAULT_ROOTER_PIN, RESERVED_CMDS
from states.states import SettingsSt
from utils.filters import IsAdmin
from utils.tg import edit_or_send

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def view(call: CallbackQuery, db, is_parent: bool):
    protect = (await db.get_setting("protect", "0")) == "1"
    text = ("⚙️ <b>Sozlamalar</b>\n\n"
            f"🛡 Kontentni forward/saqlashdan himoya: <b>{'yoqilgan' if protect else 'o`chiq'}</b>")
    b = InlineKeyboardBuilder()
    b.button(text=("🛡 Himoyani o'chirish" if protect else "🛡 Himoyani yoqish"), callback_data="set:protect")
    b.button(text="👋 Salomlashuv matni", callback_data="set:welcome")
    b.button(text="👥 Adminlar", callback_data="set:admins")
    if is_parent:   # yashirin buyruq sozlamalari faqat asosiy botda
        cmd = await db.get_setting("rooter_cmd", DEFAULT_ROOTER_CMD)
        text += f"\n🔐 Yashirin buyruq: <code>/{cmd}</code>"
        b.button(text="🔐 Yashirin buyruq nomi", callback_data="set:cmd")
        b.button(text="🔑 PIN-kod", callback_data="set:pin")
    b.button(text="⬅️ Orqaga", callback_data="adm:home")
    b.adjust(1)
    await edit_or_send(call, text, b.as_markup())


@router.callback_query(F.data == "adm:settings")
async def open_settings(call: CallbackQuery, db, is_parent):
    await call.answer()
    await view(call, db, is_parent)


@router.callback_query(F.data == "set:protect")
async def toggle_protect(call: CallbackQuery, db, is_parent):
    cur = (await db.get_setting("protect", "0")) == "1"
    await db.set_setting("protect", "0" if cur else "1")
    await call.answer("✅")
    await view(call, db, is_parent)


@router.callback_query(F.data.in_({"set:cmd", "set:pin", "set:welcome", "set:add_admin"}))
async def ask(call: CallbackQuery, state: FSMContext, is_parent):
    key = call.data.split(":")[1]
    if key in ("cmd", "pin") and not is_parent:
        await call.answer("⛔ Sub-botda bu mavjud emas", show_alert=True)
        return
    st = {"cmd": SettingsSt.cmd, "pin": SettingsSt.pin,
          "welcome": SettingsSt.welcome, "add_admin": SettingsSt.add_admin}[key]
    prompts = {
        "cmd": "🔐 Yangi yashirin buyruq nomini yuboring (lotin harf/raqam/_ , masalan: <code>panel77</code>):",
        "pin": "🔑 Yangi PIN-kodni yuboring (4–12 ta raqam):",
        "welcome": "👋 Yangi salomlashuv matnini yuboring. Ism uchun <code>{name}</code> yozing:",
        "add_admin": "👤 Yangi admin Telegram ID sini yuboring:",
    }
    await state.set_state(st)
    await call.answer()
    await call.message.answer(prompts[key] + "\nBekor qilish: /cancel")


@router.message(SettingsSt.cmd, F.text)
async def set_cmd(message: Message, state: FSMContext, db, is_parent):
    cmd = message.text.strip().lstrip("/").lower()
    if not is_parent:
        await state.clear()
        return
    if not re.fullmatch(r"[a-z0-9_]{1,32}", cmd) or cmd in RESERVED_CMDS:
        await message.answer("❗ Noto'g'ri nom. Faqat lotin harf, raqam va _ (start/help/admin/cancel mumkin emas).")
        return
    await db.set_setting("rooter_cmd", cmd)
    await state.clear()
    await message.answer(f"✅ Yashirin buyruq endi: <code>/{cmd}</code>")


@router.message(SettingsSt.pin, F.text)
async def set_pin(message: Message, state: FSMContext, db, is_parent):
    pin = message.text.strip()
    if not is_parent:
        await state.clear()
        return
    if not (pin.isdigit() and 4 <= len(pin) <= 12):
        await message.answer("❗ PIN 4–12 ta raqamdan iborat bo'lishi kerak.")
        return
    await db.set_setting("rooter_pin", pin)
    await state.clear()
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer("✅ PIN-kod yangilandi.")


@router.message(SettingsSt.welcome, F.text)
async def set_welcome(message: Message, state: FSMContext, db):
    await db.set_setting("welcome", message.html_text)
    await state.clear()
    await message.answer("✅ Salomlashuv matni yangilandi.")


@router.message(SettingsSt.add_admin, F.text)
async def set_add_admin(message: Message, state: FSMContext, db):
    t = message.text.strip()
    if not t.isdigit():
        await message.answer("❗ Faqat raqamli ID yuboring.")
        return
    await db.add_admin(int(t))
    await state.clear()
    await message.answer(f"✅ Admin qo'shildi: <code>{t}</code>")


@router.callback_query(F.data == "set:admins")
async def admins(call: CallbackQuery, db):
    ids = await db.list_admins()
    b = InlineKeyboardBuilder()
    for i in ids:
        if i != call.from_user.id:
            b.button(text=f"🗑 {i}", callback_data=f"set:deladmin:{i}")
    b.button(text="➕ Admin qo'shish", callback_data="set:add_admin")
    b.button(text="⬅️ Orqaga", callback_data="adm:settings")
    b.adjust(2)
    await call.answer()
    await edit_or_send(call, "👥 <b>Adminlar</b>:\n" + "\n".join(f"• <code>{i}</code>" for i in ids), b.as_markup())


@router.callback_query(F.data.startswith("set:deladmin:"))
async def del_admin(call: CallbackQuery, db):
    uid = int(call.data.split(":")[2])
    if uid != call.from_user.id:
        await db.del_admin(uid)
    await admins(call, db)
