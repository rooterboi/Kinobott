"""Rassilka (barcha foydalanuvchilarga xabar)."""
import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.broadcast import run_broadcast
from states.states import Broadcast
from utils.filters import IsAdmin

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())
_tasks: set[asyncio.Task] = set()


@router.callback_query(F.data == "adm:bc")
async def bc_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(Broadcast.msg)
    await call.answer()
    await call.message.answer("✉️ Rassilka uchun xabarni yuboring (matn, rasm, video — istalgani).\nBekor qilish: /cancel")


@router.message(Broadcast.msg)
async def bc_preview(message: Message, state: FSMContext, db):
    await state.update_data(src_chat=message.chat.id, src_msg=message.message_id)
    total = len(await db.user_ids())
    b = InlineKeyboardBuilder()
    b.button(text=f"✅ Yuborish ({total} ta)", callback_data="bc:go")
    b.button(text="❌ Bekor qilish", callback_data="bc:cancel")
    b.adjust(1)
    await message.reply("👆 Shu xabar barcha foydalanuvchilarga yuboriladi. Tasdiqlaysizmi?", reply_markup=b.as_markup())


@router.callback_query(F.data == "bc:cancel")
async def bc_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Bekor qilindi")
    await call.message.edit_text("❌ Rassilka bekor qilindi.")


@router.callback_query(F.data == "bc:go")
async def bc_go(call: CallbackQuery, state: FSMContext, bot, db):
    d = await state.get_data()
    if "src_msg" not in d:
        await call.answer("Xabar topilmadi", show_alert=True)
        return
    await state.clear()
    await call.answer("🚀 Boshlandi")
    await call.message.edit_text("🚀 Rassilka boshlandi. Tugagach xabar beraman.")
    t = asyncio.create_task(run_broadcast(bot, db, call.message.chat.id, d["src_chat"], d["src_msg"]))
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)
