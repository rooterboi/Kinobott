"""Kartochka tugmalari: ko'rish, sezon/seriya, saqlash, baholash."""
from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.cards import build_card, is_protected, safe_edit_caption, send_card, send_episode, send_file
from utils.helpers import esc

router = Router()


@router.callback_query(F.data.startswith("show:"))
async def cb_show(call: CallbackQuery, bot, db):
    await call.answer()
    await send_card(bot, db, call.message.chat.id, int(call.data.split(":")[1]), call.from_user.id)


@router.callback_query(F.data.startswith("watch:"))
async def cb_watch(call: CallbackQuery, bot, db):
    c = await db.get_content(int(call.data.split(":")[1]))
    if not c or not c.get("file_id"):
        await call.answer("❌ Video topilmadi", show_alert=True)
        return
    await call.answer("📥 Yuborilmoqda...")
    await db.inc_views(c["id"])
    me = await bot.me()
    caption = f"🎬 <b>{esc(c['title'])}</b>\n🆔 Kod: <code>{c['code']}</code>\n\n🤖 @{me.username}"
    await send_file(bot, call.message.chat.id, c["file_id"], c["file_type"], caption,
                    protect=await is_protected(db))


@router.callback_query(F.data.startswith("sea:"))
async def cb_season(call: CallbackQuery, db):
    _, sid, season = call.data.split(":")
    eps = await db.episodes_of(int(sid), int(season))
    if not eps:
        await call.answer("Bu sezonda seriya yo'q", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    for e in eps:
        b.button(text=f"{e['number']}-seriya", callback_data=f"ep:{e['id']}")
    b.adjust(4)
    await call.answer()
    await call.message.answer(f"📂 <b>{season}-sezon</b> — seriyani tanlang:", reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("ep:"))
async def cb_episode(call: CallbackQuery, bot, db):
    await call.answer("📥 Yuborilmoqda...")
    await send_episode(bot, db, call.message.chat.id, int(call.data.split(":")[1]))


@router.callback_query(F.data.startswith("fav:"))
async def cb_fav(call: CallbackQuery, bot, db):
    cid = int(call.data.split(":")[1])
    c = await db.get_content(cid)
    if not c:
        await call.answer("❌ Topilmadi", show_alert=True)
        return
    added = await db.toggle_fav(call.from_user.id, cid)
    await call.answer("⭐ Saqlanganlarga qo'shildi" if added else "💔 Olib tashlandi")
    caption, kb = await build_card(bot, db, c, call.from_user.id)
    await safe_edit_caption(call.message, caption, kb)


@router.callback_query(F.data.startswith("rate:"))
async def cb_rate(call: CallbackQuery, bot, db):
    _, cid, score = call.data.split(":")
    c = await db.get_content(int(cid))
    if not c:
        await call.answer("❌ Topilmadi", show_alert=True)
        return
    await db.set_rating(call.from_user.id, int(cid), int(score))
    await call.answer(f"Rahmat! Bahoyingiz: {score}⭐")
    caption, kb = await build_card(bot, db, c, call.from_user.id)
    await safe_edit_caption(call.message, caption, kb)
