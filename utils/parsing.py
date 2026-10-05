"""Admin kiritgan qiymatlarni tekshirish (qo'shish va tahrirlashda umumiy)."""


async def parse_field(key: str, message, db, own_code=None):
    """(dict | None, xato_matni | None) qaytaradi."""
    if key == "video":
        if message.video:
            return {"file_id": message.video.file_id, "file_type": "video"}, None
        if message.document:
            return {"file_id": message.document.file_id, "file_type": "document"}, None
        return None, "❗ Video (yoki video-fayl) yuboring."
    if key == "poster":
        if message.photo:
            return {"poster": message.photo[-1].file_id}, None
        return None, "❗ Rasm yuboring."
    text = (message.text or "").strip()
    if not text:
        return None, "❗ Matn yuboring."
    if key == "code":
        if not text.isdigit() or len(text) > 10:
            return None, "❗ Kod faqat raqamlardan iborat bo'lishi kerak."
        code = int(text)
        if code != own_code and await db.code_exists(code):
            return None, "❗ Bu kod band. Boshqa kod kiriting."
        return {"code": code}, None
    if key == "year":
        if not (text.isdigit() and 1900 <= int(text) <= 2100):
            return None, "❗ Yilni to'g'ri kiriting (masalan 2024)."
        return {"year": int(text)}, None
    limit = 1000 if key == "description" else 150
    return {key: text[:limit]}, None


PROMPTS = {
    "video": "🎬 <b>Video</b>ni yuboring (video yoki fayl ko'rinishida):",
    "poster": "🖼 <b>Poster</b> (rasm) yuboring:",
    "title": "✏️ <b>Nomi</b>ni kiriting:",
    "code": "🔢 <b>Kod</b>ni kiriting (faqat raqam) yoki «Avto kod» tugmasini bosing:",
    "genre": "🎭 <b>Janr</b>ni kiriting (vergul bilan: Jangari, Drama):",
    "language": "🌐 <b>Til</b>ni kiriting (masalan: O'zbek tilida):",
    "quality": "📀 <b>Sifat</b>ni kiriting (masalan: 1080p):",
    "year": "📅 <b>Yil</b>ni kiriting (masalan: 2024):",
    "description": "📝 <b>Tavsif</b>ni kiriting:",
}
