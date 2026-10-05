"""Majburiy obuna kanallari (f) va avto-post kanallari (p) boshqaruvi."""
from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.states import AddCh
from utils.filters import IsAdmin
from utils.helpers import esc
from utils.tg import edit_or_send

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

KIND = {"f": "force", "p": "post"}
TITLE = {"f": "🔒 Majburiy obuna kanallari", "p": "📣 Avto-post kanallari"}
HINT = {"f": "Foydalanuvchilar shu kanallarga obuna bo'lmaguncha bot ishlamaydi.",
        "p": "Yangi kino/serial qo'shilganda shu kanallarga avtomatik post joylanadi."}


async def render(call: CallbackQuery, db, k: str):
    chans = await db.list_channels(KIND[k])
    b = InlineKeyboardBuilder()
    lines = [f"<b>{TITLE[k]}</b>\n{HINT[k]}\n"]
    for ch in chans:
        mark = "🟢" if ch["active"] else "🔴"
        lines.append(f"{mark} {esc(ch['title'])} (<code>{ch['chat_id']}</code>)")
        b.button(text=f"{mark} {ch['title'][:20]}", callback_data=f"ch:tog:{k}:{ch['id']}")
        b.button(text="🗑", callback_data=f"ch:del:{k}:{ch['id']}")
    if not chans:
        lines.append("Hozircha kanal yo'q.")
    b.adjust(2)
    b.button(text="➕ Kanal qo'shish", callback_data=f"ch:add:{k}")
    b.button(text="⬅️ Orqaga", callback_data="adm:home")
    b.adjust(*([2] * len(chans)), 1, 1)
    await edit_or_send(call, "\n".join(lines), b.as_markup())


@router.callback_query(F.data.in_({"adm:force", "adm:post"}))
async def open_ch(call: CallbackQuery, db):
    await call.answer()
    await render(call, db, "f" if call.data == "adm:force" else "p")


@router.callback_query(F.data.startswith("ch:tog:"))
async def tog(call: CallbackQuery, db):
    _, _, k, cid = call.data.split(":")
    await db.toggle_channel(KIND[k], int(cid))
    await call.answer()
    await render(call, db, k)


@router.callback_query(F.data.startswith("ch:del:"))
async def delete(call: CallbackQuery, db):
    _, _, k, cid = call.data.split(":")
    await db.del_channel(KIND[k], int(cid))
    await call.answer("🗑 O'chirildi")
    await render(call, db, k)


@router.callback_query(F.data.startswith("ch:add:"))
async def add_start(call: CallbackQuery, state: FSMContext):
    k = call.data.split(":")[2]
    await state.set_state(AddCh.wait)
    await state.update_data(k=k)
    await call.answer()
    await call.message.answer(
        "➕ Avval botni kanalga <b>admin</b> qiling" + (" (post yuborish huquqi bilan)" if k == "p" else "") + ".\n\n"
        "Keyin kanal <b>@username</b>i, <b>-100...</b> ID sini yuboring yoki kanaldan biror xabarni <b>forward</b> qiling.\n"
        "Bekor qilish: /cancel")


@router.message(AddCh.wait)
async def add_channel(message: Message, state: FSMContext, bot, db):
    d = await state.get_data()
    k = d["k"]
    ident = None
    fo = message.forward_origin
    if fo is not None and getattr(fo, "type", None) == "channel":
        ident = fo.chat.id
    elif message.text:
        t = message.text.strip()
        ident = int(t) if t.lstrip("-").isdigit() else (t if t.startswith("@") else "@" + t.lstrip("/"))
    if ident is None:
        await message.answer("❗ @username, ID yoki forward xabar yuboring.")
        return
    try:
        chat = await bot.get_chat(ident)
        me = await bot.me()
        member = await bot.get_chat_member(chat.id, me.id)
        if member.status not in ("administrator", "creator"):
            await message.answer("❗ Bot bu kanalda admin emas. Avval botni admin qiling.")
            return
    except TelegramAPIError as e:
        await message.answer(f"❌ Kanal topilmadi yoki bot unda yo'q: {esc(e.message)}")
        return
    link = f"https://t.me/{chat.username}" if chat.username else chat.invite_link
    if not link:
        try:
            link = await bot.export_chat_invite_link(chat.id)
        except TelegramAPIError:
            link = None
    await db.add_channel(KIND[k], chat.id, chat.title or str(chat.id), link)
    await state.clear()
    await message.answer(f"✅ Qo'shildi: <b>{esc(chat.title)}</b>")
