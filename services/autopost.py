"""Yangi kontent qo'shilganda avto-post kanallarga chiroyli post joylash."""
import logging

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.helpers import esc

log = logging.getLogger(__name__)


def post_caption(c: dict, username: str) -> str:
    icon = "🎬" if c["type"] == "movie" else "📺"
    lines = [f"{icon} <b>{esc(c['title'])}</b>", "", f"🆔 Kod: <code>{c['code']}</code>"]
    for emoji, label, key in (("🎭", "Janr", "genre"), ("🌐", "Til", "language"),
                              ("📀", "Sifat", "quality"), ("📅", "Yil", "year")):
        if c.get(key):
            lines.append(f"{emoji} {label}: {esc(c[key])}")
    if c.get("description"):
        lines += ["", f"📝 {esc(c['description'][:300])}"]
    lines += ["", f"🤖 @{username} — kodni botga yuboring yoki tugmani bosing 👇"]
    return "\n".join(lines)


async def autopost(bot, db, c: dict) -> int:
    """Faol avto-post kanallarga joylaydi. Muvaffaqiyatli joylanganlar sonini qaytaradi."""
    channels = await db.list_channels("post", only_active=True)
    if not channels or not c.get("poster"):
        return 0
    me = await bot.me()
    label = "🎬 Botda ko'rish" if c["type"] == "movie" else "📺 Botda ko'rish"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=label, url=f"https://t.me/{me.username}?start={c['code']}")]])
    caption = post_caption(c, me.username)
    ok = 0
    for ch in channels:
        try:
            await bot.send_photo(ch["chat_id"], c["poster"], caption=caption, reply_markup=kb)
            ok += 1
        except Exception as e:
            log.warning("Avto-post xatosi (%s): %s", ch["chat_id"], e)
    return ok
  
