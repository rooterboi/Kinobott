"""Kino va serial qo'shish — qadamma-qadam (wizard)."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.admin.manage import send_admin_card
from services.autopost import autopost
from states.states import Wizard
from utils.filters import IsAdmin
from utils.parsing import PROMPTS, parse_field

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

MOVIE_STEPS = ["video", "poster", "title", "code", "genre", "language", "quality", "year", "description"]
SERIES_STEPS = ["poster", "title", "code", "genre", "language", "quality", "year", "description"]
OPTIONAL = {"language", "quality", "year", "description"}


def step_kb(key: str):
    b = InlineKeyboardBuilder()
    if key == "code":
        b.button(text="🔢 Avto kod", callback_data="wiz:auto")
    if key in OPTIONAL:
        b.button(text="⏭ O'tkazib yuborish", callback_data="wiz:skip")
    b.button(text="❌ Bekor qilish", callback_data="wiz:cancel")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data.in_({"adm:addmovie", "adm:addseries"}))
async def wiz_start(call: CallbackQuery, state: FSMContext):
    kind = "movie" if call.data == "adm:addmovie" else "series"
    steps = MOVIE_STEPS if kind == "movie" else SERIES_STEPS
    await state.set_state(Wizard.step)
    await state.update_data(kind=kind, steps=steps, i=0, f={})
    title = "🎬 <b>Yangi kino</b>" if kind == "movie" else "📺 <b>Yangi serial</b>"
    await call.answer()
    await call.message.answer(f"{title}\n\n{PROMPTS[steps[0]]}", reply_markup=step_kb(steps[0]))


@router.callback_query(Wizard.step, F.data == "wiz:cancel")
async def wiz_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Bekor qilindi")
    await call.message.answer("❌ Bekor qilindi. /admin")


async def advance(message: Message, state: FSMContext, bot, db):
    d = await state.get_data()
    i = d["i"] + 1
    if i >= len(d["steps"]):
        await finish(message, state, bot, db, d)
        return
    await state.update_data(i=i)
    key = d["steps"][i]
    await message.answer(PROMPTS[key], reply_markup=step_kb(key))


async def finish(message: Message, state: FSMContext, bot, db, d):
    f, kind = d["f"], d["kind"]
    cid = await db.add_content(kind, f)
    await state.clear()
    c = await db.get_content(cid)
    n = await autopost(bot, db, c)         # avto-post kanallarga chiroyli post
    await message.answer(f"✅ Saqlandi! Kod: <code>{c['code']}</code>\n📣 Avto-post: {n} ta kanalga joylandi.")
    await send_admin_card(bot, db, message.chat.id, cid)
    if kind == "series":
        await message.answer("ℹ️ Endi «➕ Seriya qo'shish» tugmasi orqali sezon va seriyalarni biriktiring.")


@router.callback_query(Wizard.step, F.data == "wiz:skip")
async def wiz_skip(call: CallbackQuery, state: FSMContext, bot, db):
    d = await state.get_data()
    if d["steps"][d["i"]] not in OPTIONAL:
        await call.answer("Bu maydon majburiy", show_alert=True)
        return
    await call.answer()
    await advance(call.message, state, bot, db)


@router.callback_query(Wizard.step, F.data == "wiz:auto")
async def wiz_auto(call: CallbackQuery, state: FSMContext, bot, db):
    d = await state.get_data()
    if d["steps"][d["i"]] != "code":
        await call.answer()
        return
    f = d["f"]
    f["code"] = await db.next_code()
    await state.update_data(f=f)
    await call.answer()
    await call.message.answer(f"🔢 Kod: <code>{f['code']}</code>")
    await advance(call.message, state, bot, db)


@router.message(Wizard.step)
async def wiz_input(message: Message, state: FSMContext, bot, db):
    d = await state.get_data()
    key = d["steps"][d["i"]]
    fields, err = await parse_field(key, message, db)
    if err:
        await message.answer(err)
        return
    f = d["f"]
    f.update(fields)
    await state.update_data(f=f)
    await advance(message, state, bot, db)
