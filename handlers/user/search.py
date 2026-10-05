"""Qidiruv, janrlar, yillar, top, yangi, saqlanganlar, tasodifiy."""
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.cards import open_code, send_card
from utils.helpers import cache_get
from utils.lists import render_list

router = Router()


async def send_list(message: Message, db, kind, value=None, user_id=None):
    text, kb = await render_list(db, kind, value, 0, user_id or message.from_user.id)
    await message.answer(text, reply_markup=kb)


@router.message(F.text == "🔍 Qidiruv")
async def btn_search(message: Message):
    await message.answer("🔍 Kino <b>kodini</b>, <b>nomini</b>, janrini yoki yilini yuboring:")


@router.message(F.text == "🔥 Top")
async def btn_top(message: Message, db):
    await send_list(message, db, "top")


@router.message(F.text == "🆕 Yangi")
async def btn_new(message: Message, db):
    await send_list(message, db, "new")


@router.message(F.text == "⭐ Saqlanganlar")
async def btn_fav(message: Message, db):
    await send_list(message, db, "fav")


@router.message(F.text == "🎲 Tasodifiy")
async def btn_random(message: Message, bot, db):
    c = await db.random_content()
    if not c:
        await message.answer("😕 Hozircha kontent yo'q.")
        return
    await send_card(bot, db, message.chat.id, c["id"], message.from_user.id)


@router.message(F.text == "🎭 Janrlar")
async def btn_genres(message: Message, db):
    genres = await db.genres()
    if not genres:
        await message.answer("😕 Janrlar hali yo'q.")
        return
    b = InlineKeyboardBuilder()
    for name, cnt in genres:
        b.button(text=f"{name} ({cnt})", callback_data=f"gen:{name[:25]}")
    b.adjust(2)
    await message.answer("🎭 Janrni tanlang:", reply_markup=b.as_markup())


@router.message(F.text == "📅 Yillar")
async def btn_years(message: Message, db):
    years = await db.years()
    if not years:
        await message.answer("😕 Yillar hali yo'q.")
        return
    b = InlineKeyboardBuilder()
    for y in years:
        b.button(text=str(y), callback_data=f"yr:{y}")
    b.adjust(4)
    await message.answer("📅 Yilni tanlang:", reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("gen:"))
async def cb_genre(call: CallbackQuery, db):
    await call.answer()
    await send_list(call.message, db, "g", call.data[4:], call.from_user.id)


@router.callback_query(F.data.startswith("yr:"))
async def cb_year(call: CallbackQuery, db):
    await call.answer()
    await send_list(call.message, db, "y", call.data[3:], call.from_user.id)


@router.callback_query(F.data.startswith("lst:"))
async def cb_list_page(call: CallbackQuery, db):
    _, kind, token, page = call.data.split(":")
    value = cache_get(token) if kind in ("q", "g") else (token if kind == "y" else None)
    if kind in ("q", "g") and value is None:
        await call.answer("Qidiruv eskirgan, qaytadan yuboring.", show_alert=True)
        return
    text, kb = await render_list(db, kind, value, int(page), call.from_user.id, token=token)
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass
    await call.answer()


# Eng oxirida: oddiy matn = kod yoki qidiruv (FSM holati yo'q bo'lganda)
@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def text_search(message: Message, bot, db):
    text = message.text.strip()
    if await open_code(bot, db, message.chat.id, message.from_user.id, text):
        return
    if text.isdigit() and len(text) == 4:                       # yil bo'yicha
        rows, total = await db.list_by("y", text, limit=1)
        if total:
            await send_list(message, db, "y", text)
            return
    if text.isdigit():
        await message.answer("😕 Bunday kodli kino topilmadi.")
        return
    await send_list(message, db, "q", text[:60])
