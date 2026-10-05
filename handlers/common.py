"""Umumiy buyruqlar: /start (deep-link bilan), /cancel, /help, obunani tekshirish."""
from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.common import main_menu, subscribe_kb
from utils.cards import open_code
from utils.helpers import esc
from utils.subscription import get_missing

router = Router()

DEFAULT_WELCOME = ("🎬 Assalomu alaykum, <b>{name}</b>!\n\n"
                   "Kino yoki serial <b>kodini</b> yuboring, yoki <b>nomini</b> yozib qidiring.\n"
                   "Pastdagi menyudan janr, yil va top ro'yxatlardan ham foydalanishingiz mumkin 👇")

HELP = ("ℹ️ <b>Yordam</b>\n\n"
        "• Kino kodini yuboring — kartochka chiqadi\n"
        "• Nom yoki janr yozing — qidiruv ishlaydi\n"
        "• 4 xonali yil yozing (2024) — shu yilgi kinolar\n"
        "• ⭐ tugmasi bilan saqlang, 1–5 baho bering\n"
        "• /cancel — joriy amalni bekor qilish")


async def send_welcome(message: Message, db, is_admin: bool, user=None):
    user = user or message.from_user
    text = await db.get_setting("welcome", DEFAULT_WELCOME)
    await message.answer(text.replace("{name}", esc(user.full_name)), reply_markup=main_menu(is_admin))


@router.message(CommandStart(deep_link=True), StateFilter("*"))
async def start_deeplink(message: Message, command: CommandObject, state: FSMContext, bot, db, is_admin):
    await state.clear()
    if await open_code(bot, db, message.chat.id, message.from_user.id, command.args or ""):
        return
    await send_welcome(message, db, is_admin)


@router.message(CommandStart(), StateFilter("*"))
async def start(message: Message, state: FSMContext, db, is_admin):
    await state.clear()
    await send_welcome(message, db, is_admin)


@router.message(Command("cancel"), StateFilter("*"))
async def cancel(message: Message, state: FSMContext, is_admin):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=main_menu(is_admin))


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Yordam")
async def help_cmd(message: Message):
    await message.answer(HELP)


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


@router.callback_query(F.data.startswith("check_sub"))
async def check_sub(call: CallbackQuery, bot, db, is_admin):
    if await get_missing(bot, db, call.from_user.id):
        await call.answer("❌ Hali hamma kanalga obuna bo'lmadingiz!", show_alert=True)
        return
    await call.answer("✅ Rahmat!")
    try:
        await call.message.delete()
    except Exception:
        pass
    arg = call.data.partition(":")[2]
    if arg and await open_code(bot, db, call.message.chat.id, call.from_user.id, arg):
        return
    await send_welcome(call.message, db, is_admin, user=call.from_user)
