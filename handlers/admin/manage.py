"""Kontentni boshqarish: ro'yxat, tahrirlash, o'chirish, qayta post, serial seriyalari."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.autopost import autopost
from states.states import AddEp, Edit
from utils.filters import IsAdmin
from utils.helpers import build_caption, esc
from utils.lists import render_list
from utils.parsing import PROMPTS, parse_field
from utils.tg import edit_or_send

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ---------------------------------------------------------------- admin kartochka
def admin_card_kb(c: dict):
    cid = c["id"]
    b = InlineKeyboardBuilder()
    fields = [("✏️ Nom", "title"), ("🔢 Kod", "code"), ("🎭 Janr", "genre"), ("🌐 Til", "language"),
              ("📀 Sifat", "quality"), ("📅 Yil", "year"), ("📝 Tavsif", "description"), ("🖼 Poster", "poster")]
    if c["type"] == "movie":
        fields.append(("🎞 Video", "video"))
    for text, f in fields:
        b.button(text=text, callback_data=f"aedit:{cid}:{f}")
    b.adjust(2)
    if c["type"] == "series":
        b.row(InlineKeyboardButton(text="➕ Seriya qo'shish", callback_data=f"aaddep:{cid}"),
              InlineKeyboardButton(text="📂 Seriyalar", callback_data=f"aeps:{cid}"))
    b.row(InlineKeyboardButton(text="📣 Kanalga joylash", callback_data=f"arepost:{cid}"),
          InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"adel:{cid}"))
    b.row(InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home"))
    return b.as_markup()


async def send_admin_card(bot, db, chat_id: int, cid: int):
    c = await db.get_content(cid)
    if not c:
        await bot.send_message(chat_id, "❌ Topilmadi.")
        return
    avg, cnt = await db.get_rating(cid)
    caption = build_caption(c, avg, cnt)
    if c["type"] == "series":
        caption += f"\n\n📂 Seriyalar: {await db.count_episodes(cid)} ta"
    if c.get("poster"):
        await bot.send_photo(chat_id, c["poster"], caption=caption, reply_markup=admin_card_kb(c))
    else:
        await bot.send_message(chat_id, caption, reply_markup=admin_card_kb(c))


# ---------------------------------------------------------------- ro'yxat
@router.callback_query(F.data.in_({"adm:list:m", "adm:list:s"}))
async def adm_list(call: CallbackQuery, db):
    kind = call.data[-1]
    text, kb = await render_list(db, kind, None, 0, item_cb="aopen", nav_cb="alst", back="adm:home")
    await call.answer()
    await edit_or_send(call, text, kb)


@router.callback_query(F.data.startswith("alst:"))
async def adm_list_page(call: CallbackQuery, db):
    _, kind, token, page = call.data.split(":")
    text, kb = await render_list(db, kind, None, int(page), item_cb="aopen", nav_cb="alst",
                                 back="adm:home", token=token)
    await call.answer()
    await edit_or_send(call, text, kb)


@router.callback_query(F.data.startswith("aopen:"))
async def adm_open(call: CallbackQuery, bot, db):
    await call.answer()
    await send_admin_card(bot, db, call.message.chat.id, int(call.data.split(":")[1]))


# ---------------------------------------------------------------- tahrirlash
@router.callback_query(F.data.startswith("aedit:"))
async def edit_start(call: CallbackQuery, state: FSMContext):
    _, cid, field = call.data.split(":")
    await state.set_state(Edit.value)
    await state.update_data(cid=int(cid), field=field)
    await call.answer()
    await call.message.answer(PROMPTS[field] + "\n\n(Bekor qilish: /cancel)")


@router.message(Edit.value)
async def edit_value(message: Message, state: FSMContext, bot, db):
    d = await state.get_data()
    c = await db.get_content(d["cid"])
    if not c:
        await state.clear()
        await message.answer("❌ Kontent topilmadi.")
        return
    fields, err = await parse_field(d["field"], message, db, own_code=c["code"])
    if err:
        await message.answer(err)
        return
    await db.update_content(c["id"], **fields)
    await state.clear()
    await message.answer("✅ Yangilandi.")
    await send_admin_card(bot, db, message.chat.id, c["id"])


# ---------------------------------------------------------------- o'chirish / qayta post
@router.callback_query(F.data.startswith("adel:"))
async def delete_ask(call: CallbackQuery):
    cid = call.data.split(":")[1]
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ha, o'chirish", callback_data=f"adel_y:{cid}")
    b.button(text="❌ Yo'q", callback_data="adm:home")
    b.adjust(2)
    await call.answer()
    await call.message.answer("❗ Rostdan ham o'chirilsinmi? (Seriyalar, saqlanganlar va baholar ham o'chadi)",
                              reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("adel_y:"))
async def delete_do(call: CallbackQuery, db):
    await db.delete_content(int(call.data.split(":")[1]))
    await call.answer("🗑 O'chirildi", show_alert=True)
    await edit_or_send(call, "🗑 Kontent o'chirildi.")


@router.callback_query(F.data.startswith("arepost:"))
async def repost(call: CallbackQuery, bot, db):
    c = await db.get_content(int(call.data.split(":")[1]))
    if not c:
        await call.answer("❌ Topilmadi", show_alert=True)
        return
    n = await autopost(bot, db, c)
    await call.answer(f"📣 {n} ta kanalga joylandi" if n else "Faol avto-post kanal yo'q yoki xatolik", show_alert=True)


# ---------------------------------------------------------------- serialga seriya qo'shish
def _season_kb(sid, seasons):
    b = InlineKeyboardBuilder()
    nxt = max([s["season"] for s in seasons], default=0) + 1
    for s in seasons:
        b.button(text=f"{s['season']}-sezon ({s['cnt']})", callback_data=f"epseason:{sid}:{s['season']}")
    b.button(text=f"➕ {nxt}-sezon (yangi)", callback_data=f"epseason:{sid}:{nxt}")
    b.button(text="❌ Bekor qilish", callback_data="adm:home")
    b.adjust(2)
    return b.as_markup()


@router.callback_query(F.data.startswith("aaddep:"))
async def ep_start(call: CallbackQuery, state: FSMContext, db):
    sid = int(call.data.split(":")[1])
    await state.set_state(AddEp.season)
    await state.update_data(sid=sid)
    await call.answer()
    await call.message.answer("📂 Qaysi sezonga seriya qo'shamiz? Tanlang yoki sezon raqamini yozing:",
                              reply_markup=_season_kb(sid, await db.seasons(sid)))


async def _choose_season(message: Message, state: FSMContext, season: int):
    await state.set_state(AddEp.video)
    await state.update_data(season=season)
    b = InlineKeyboardBuilder()
    b.button(text="✅ Tugatish", callback_data="epdone")
    await message.answer(
        f"📹 <b>{season}-sezon</b> seriyalarini ketma-ket yuboring.\n"
        f"Seriya raqami avtomatik beriladi. Videoga izoh (caption) sifatida raqam yozsangiz — u seriya kodi bo'ladi, "
        f"yozmasangiz kod avtomatik tanlanadi.", reply_markup=b.as_markup())


@router.callback_query(AddEp.season, F.data.startswith("epseason:"))
async def ep_season_cb(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await _choose_season(call.message, state, int(call.data.split(":")[2]))


@router.message(AddEp.season, F.text)
async def ep_season_text(message: Message, state: FSMContext):
    t = message.text.strip()
    if not t.isdigit() or not 0 < int(t) < 100:
        await message.answer("❗ Sezon raqamini kiriting (1–99).")
        return
    await _choose_season(message, state, int(t))


@router.message(AddEp.video)
async def ep_video(message: Message, state: FSMContext, db):
    fields, err = await parse_field("video", message, db)
    if err:
        await message.answer(err)
        return
    d = await state.get_data()
    cap = (message.caption or "").strip()
    code = int(cap) if cap.isdigit() and len(cap) <= 10 and not await db.code_exists(int(cap)) else await db.next_code()
    number = await db.next_episode_number(d["sid"], d["season"])
    await db.add_episode(d["sid"], d["season"], number, code, fields["file_id"], fields["file_type"])
    await message.answer(f"✅ {d['season']}-sezon {number}-seriya saqlandi. Kod: <code>{code}</code>\n"
                         f"Keyingi videoni yuboring yoki «✅ Tugatish» ni bosing.")


@router.callback_query(F.data == "epdone")
async def ep_done(call: CallbackQuery, state: FSMContext, bot, db):
    d = await state.get_data()
    await state.clear()
    await call.answer("✅")
    if d.get("sid"):
        await send_admin_card(bot, db, call.message.chat.id, d["sid"])


# ---------------------------------------------------------------- seriyalarni ko'rish / o'chirish
@router.callback_query(F.data.startswith("aeps:"))
async def eps_seasons(call: CallbackQuery, db):
    sid = int(call.data.split(":")[1])
    seasons = await db.seasons(sid)
    b = InlineKeyboardBuilder()
    for s in seasons:
        b.button(text=f"📂 {s['season']}-sezon ({s['cnt']} ta)", callback_data=f"aseason:{sid}:{s['season']}")
    b.button(text="⬅️ Orqaga", callback_data=f"aopen:{sid}")
    b.adjust(1)
    await call.answer()
    await call.message.answer("📂 Sezonni tanlang:" if seasons else "Hali seriya yo'q.", reply_markup=b.as_markup())


async def _render_season(call: CallbackQuery, db, sid: int, season: int):
    eps = await db.episodes_of(sid, season)
    b = InlineKeyboardBuilder()
    for e in eps:
        b.button(text=f"🗑 {e['number']}-seriya • kod {e['code']}",
                 callback_data=f"aepdel:{e['id']}:{sid}:{season}")
    b.button(text="⬅️ Orqaga", callback_data=f"aeps:{sid}")
    b.adjust(1)
    await edit_or_send(call, f"📂 <b>{season}-sezon</b>. O'chirish uchun seriyani bosing:" if eps
                       else "Bu sezon bo'sh.", b.as_markup())


@router.callback_query(F.data.startswith("aseason:"))
async def eps_list(call: CallbackQuery, db):
    _, sid, season = call.data.split(":")
    await call.answer()
    await _render_season(call, db, int(sid), int(season))


@router.callback_query(F.data.startswith("aepdel:"))
async def ep_delete(call: CallbackQuery, db):
    _, eid, sid, season = call.data.split(":")
    await db.delete_episode(int(eid))
    await call.answer("🗑 O'chirildi")
    await _render_season(call, db, int(sid), int(season))
