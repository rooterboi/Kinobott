"""Umumiy yordamchi funksiyalar."""
import secrets
from collections import OrderedDict
from html import escape

# Qidiruv so'zlarini callback_data (64 bayt) ga sig'dirish uchun qisqa kalit bilan keshlaymiz
_CACHE: "OrderedDict[str, str]" = OrderedDict()


def cache_put(value: str) -> str:
    key = secrets.token_hex(4)
    _CACHE[key] = value
    while len(_CACHE) > 1000:
        _CACHE.popitem(last=False)
    return key


def cache_get(key: str):
    return _CACHE.get(key)


def esc(v) -> str:
    return escape(str(v)) if v is not None else ""


def build_caption(c: dict, avg: float = 0.0, cnt: int = 0) -> str:
    """Kino / serial kartochkasi matni."""
    icon = "🎬" if c["type"] == "movie" else "📺"
    lines = [f"{icon} <b>{esc(c['title'])}</b>", "", f"🆔 Kod: <code>{c['code']}</code>"]
    if c.get("genre"):
        lines.append(f"🎭 Janr: {esc(c['genre'])}")
    if c.get("language"):
        lines.append(f"🌐 Til: {esc(c['language'])}")
    if c.get("quality"):
        lines.append(f"📀 Sifat: {esc(c['quality'])}")
    if c.get("year"):
        lines.append(f"📅 Yil: {c['year']}")
    lines.append(f"⭐ Reyting: {avg:.1f}/5 ({cnt})" if cnt else "⭐ Reyting: baholanmagan")
    lines.append(f"👁 Ko'rishlar: {c.get('views', 0)}")
    if c.get("description"):
        lines += ["", f"📝 {esc(c['description'][:450])}"]
    return "\n".join(lines)
