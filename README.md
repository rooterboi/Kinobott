# 🎬 Kino Bot (aiogram 3 + aiosqlite)

Modulli, multibot (Parent/Child) arxitekturali kino va serial boti.

## Ishga tushirish
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # BOT_TOKEN va ADMIN_IDS ni to'ldiring
python main.py
```

## Tuzilma
```
main.py                  ishga tushirish
config.py                .env sozlamalari
database/db.py           har bir bot uchun SQLite (aiosqlite)
database/master.py       barcha botlar ro'yxati (Parent/Child)
services/manager.py      multibot menejeri (polling, rol, sub-bot yaratish)
services/autopost.py     kanalga avto-post
services/broadcast.py    rassilka
middlewares/             kontekst (rol/admin) + majburiy obuna
handlers/common.py       /start (deep-link), /cancel, /help
handlers/rooter.py       maxfiy /rooter → PIN → token → sub-bot
handlers/user/           qidiruv, kartochka, saqlash, baholash
handlers/admin/          panel, wizard (qo'shish), manage (tahrir), channels, broadcast, settings
```

## Muhim qoidalar
- **Admin**: `.env` dagi `ADMIN_IDS` (Parent). Sub-botning admini — uni yaratgan foydalanuvchi.
- **Maxfiy buyruq**: standart `/rooter`, PIN `9767`. Admin panel → ⚙️ Sozlamalar dan o'zgartiriladi (faqat Parent).
  3 marta xato PIN → 10 daqiqa blok.
- **Sub-bot**: har biri o'z bazasi (`data/bot_<id>.db`), kontenti, kanallari va admin paneliga ega.
  Rol faqat serverda (`is_parent`) belgilanadi; Child botda `/rooter` ishlamaydi, sozlamalarda ham ko'rinmaydi.
- **Majburiy obuna / avto-post**: botni kanalga **admin** qiling, so'ng panelda kanalni qo'shing.
- **Kodlar**: kino/serial/seriya kodlari yagona raqamlar fazosida (takrorlanmaydi). Videoga izohga raqam yozsangiz — seriya kodi bo'ladi.
- Telegram `file_id` lar bot-xos, shuning uchun sub-botga kontentni shu sub-botning o'zida yuklang.
- FSM holati xotirada (MemoryStorage): qayta ishga tushganda tugamagan jarayonlar tozalanadi, baza saqlanib qoladi.
