"""Admin panel: bosh menyu, statistika, sub-botlar boshqaruvi."""
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.filters import IsAdmin
from utils.tg import edit_or_send

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

BACK = "adm:home"


def panel_kb(is_parent: bool):
    b = InlineKeyboardBuilder()
    b.button(text="🎬 Kino qo'shish", callback_data="adm:addmovie")
    b.button(text="🎞 Kinolar", callback_data="adm:list:m")
    b.button(text="📺 Serial yaratish", callback_data="adm:addseries")
    b.button(text="📚 Seriallar", callback_data="adm:list:s")
    b.button(text="📣 Avto-post kanallar", callback_data="adm:post")
    b.button(text="🔒 Majburiy obuna", callback_data="adm:force")
    b.button(text="📊 Statistika", callback_data="adm:stats")
    b.button(text="✉️ Rassilka", callback_data="adm:bc")
    b.button(text="⚙️ Sozlamalar", callback_data="adm:settings")
    if is_parent:
        b.button(text="🤖 Sub-botlar", callback_data="adm:subbots")
    b.adjust(2)
    return b.as_markup()


@router.message(Command("admin"), StateFilter("*"))
@router.message(F.text == "👑 Admin panel", StateFilter("*"))
async def open_panel(message: Message, state: FSMContext, is_parent):
    await state.clear()
    await message.answer("👑 <b>Admin panel</b>", reply_markup=panel_kb(is_parent))


@router.callback_query(F.data == "adm:home")
async def home(call: CallbackQuery, state: FSMContext, is_parent):
    await state.clear()
    await call.answer()
    await edit_or_send(call, "👑 <b>Admin panel</b>", panel_kb(is_parent))


@router.callback_query(F.data == "adm:stats")
async def stats(call: CallbackQuery, db, is_parent, manager):
    s = await db.stats()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['users']}</b>\n"
        f"🆕 Bugun qo'shilgan (24 soat): <b>{s['new_today']}</b>\n"
        f"🔥 Faol (24 soat): <b>{s['active']}</b>\n"
        f"🚫 Botni bloklagan: <b>{s['blocked']}</b>\n\n"
        f"🎬 Kinolar: <b>{s['movies']}</b>\n"
        f"📺 Seriallar: <b>{s['series']}</b> ({s['episodes']} ta seriya)\n"
        f"👁 Jami ko'rishlar: <b>{s['views']}</b>\n"
        f"⭐ Saqlanganlar: <b>{s['favs']}</b>\n\n"
        f"🔒 Majburiy kanallar: <b>{s['force']}</b>\n"
        f"📣 Avto-post kanallar: <b>{s['post']}</b>"
    )
    if is_parent:
        subs = [r for r in await manager.master.get_bots() if not r["is_parent"]]
        text += f"\n🤖 Sub-botlar: <b>{len(subs)}</b>"
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Orqaga", callback_data=BACK)
    await call.answer()
    await edit_or_send(call, text, b.as_markup())


# ---------------------------------------------------------------- sub-botlar (faqat Parent)
@router.callback_query(F.data == "adm:subbots")
async def subbots(call: CallbackQuery, is_parent, manager):
    if not is_parent:
        await call.answer("⛔", show_alert=True)
        return
    subs = [r for r in await manager.master.get_bots() if not r["is_parent"]]
    b = InlineKeyboardBuilder()
    lines = ["🤖 <b>Sub-botlar</b>\n"]
    for r in subs:
        state = "🟢" if r["active"] else "🔴"
        lines.append(f"{state} @{r['username']} — egasi: <code>{r['owner_id']}</code>")
        b.button(text=f"🗑 @{r['username']}", callback_data=f"sb:del:{r['bot_id']}")
    if not subs:
        lines.append("Hozircha sub-bot yo'q.")
    b.button(text="⬅️ Orqaga", callback_data=BACK)
    b.adjust(1)
    await call.answer()
    await edit_or_send(call, "\n".join(lines), b.as_markup())


@router.callback_query(F.data.startswith("sb:del:"))
async def sub_del_ask(call: CallbackQuery, is_parent):
    if not is_parent:
        await call.answer("⛔", show_alert=True)
        return
    bid = call.data.split(":")[2]
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ha, o'chirish", callback_data=f"sb:ok:{bid}")
    b.button(text="❌ Yo'q", callback_data="adm:subbots")
    b.adjust(2)
    await call.answer()
    await edit_or_send(call, "❗ Sub-bot to'xtatiladi va ro'yxatdan o'chiriladi (baza fayli saqlanib qoladi). Davom etasizmi?",
                       b.as_markup())


@router.callback_query(F.data.startswith("sb:ok:"))
async def sub_del(call: CallbackQuery, is_parent, manager):
    if not is_parent:
        await call.answer("⛔", show_alert=True)
        return
    ok = await manager.remove_child(int(call.data.split(":")[2]))
    await call.answer("✅ O'chirildi" if ok else "❌ Bo'lmadi", show_alert=True)
    await subbots(call, is_parent, manager)
