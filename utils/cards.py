"""Kino / serial kartochkasi va video yuborish funksiyalari."""
from urllib.parse import quote

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.helpers import build_caption, esc


async def is_protected(db) -> bool:
    return (await db.get_setting("protect", "0")) == "1"


async def build_card(bot, db, c: dict, user_id: int):
    """Kartochka matni + tugmalari (yuklab olish, sezonlar, saqlash, baholash)."""
    avg, cnt = await db.get_rating(c["id"])
    caption = build_caption(c, avg, cnt)
    me = await bot.me()
    deep = f"https://t.me/{me.username}?start={c['code']}"
    b = InlineKeyboardBuilder()
    if c["type"] == "movie":
        b.row(InlineKeyboardButton(text="▶️ Ko'rish / Yuklab olish", callback_data=f"watch:{c['id']}"))
    else:
        seasons = await db.seasons(c["id"])
        if seasons:
            btns = [InlineKeyboardButton(text=f"📂 {s['season']}-sezon", callback_data=f"sea:{c['id']}:{s['season']}")
                    for s in seasons]
            for i in range(0, len(btns), 3):
                b.row(*btns[i:i + 3])
        else:
            b.row(InlineKeyboardButton(text="⏳ Seriyalar tez orada", callback_data="noop"))
    fav = await db.is_fav(user_id, c["id"])
    share = f"https://t.me/share/url?url={quote(deep)}&text={quote(c['title'])}"
    b.row(
        InlineKeyboardButton(text="💔 Saqlanganlardan olib tashlash" if fav else "⭐ Saqlash",
                             callback_data=f"fav:{c['id']}"),
        InlineKeyboardButton(text="📤 Ulashish", url=share),
    )
    mine = await db.user_rating(user_id, c["id"])
    b.row(*[InlineKeyboardButton(text=f"{'✅' if mine == n else ''}{n}⭐", callback_data=f"rate:{c['id']}:{n}")
            for n in range(1, 6)])
    return caption, b.as_markup()


async def send_card(bot, db, chat_id: int, cid: int, user_id: int):
    c = await db.get_content(cid)
    if not c:
        await bot.send_message(chat_id, "❌ Kontent topilmadi (o'chirilgan bo'lishi mumkin).")
        return
    caption, kb = await build_card(bot, db, c, user_id)
    if c.get("poster"):
        await bot.send_photo(chat_id, c["poster"], caption=caption, reply_markup=kb)
    else:
        await bot.send_message(chat_id, caption, reply_markup=kb)


async def send_file(bot, chat_id, file_id, file_type, caption, kb=None, protect=False):
    if file_type == "document":
        return await bot.send_document(chat_id, file_id, caption=caption, reply_markup=kb, protect_content=protect)
    return await bot.send_video(chat_id, file_id, caption=caption, reply_markup=kb,
                                protect_content=protect, supports_streaming=True)


async def send_episode(bot, db, chat_id: int, eid: int):
    ep = await db.get_episode(eid)
    if not ep:
        await bot.send_message(chat_id, "❌ Seriya topilmadi.")
        return
    s = await db.get_content(ep["series_id"])
    await db.inc_views(ep["series_id"])
    me = await bot.me()
    caption = (f"📺 <b>{esc(s['title'])}</b>\n{ep['season']}-sezon, {ep['number']}-seriya\n"
               f"🆔 Kod: <code>{ep['code']}</code>\n\n🤖 @{me.username}")
    nxt = await db.next_episode(ep)
    kb = None
    if nxt:
        b = InlineKeyboardBuilder()
        b.button(text=f"⏭ Keyingi: {nxt['season']}-sezon {nxt['number']}-seriya", callback_data=f"ep:{nxt['id']}")
        kb = b.as_markup()
    await send_file(bot, chat_id, ep["file_id"], ep["file_type"], caption, kb, await is_protected(db))


async def open_code(bot, db, chat_id: int, user_id: int, text: str) -> bool:
    """Kod bo'yicha kino/serial/seriyani ochadi. Topilsa True."""
    text = (text or "").strip()
    if not text.isdigit() or len(text) > 12:
        return False
    found = await db.find_by_code(int(text))
    if not found:
        return False
    kind, row = found
    if kind == "content":
        await send_card(bot, db, chat_id, row["id"], user_id)
    else:
        await send_episode(bot, db, chat_id, row["id"])
    return True


async def safe_edit_caption(message, caption, kb):
    try:
        await message.edit_caption(caption=caption, reply_markup=kb)
    except TelegramBadRequest:
        pass
