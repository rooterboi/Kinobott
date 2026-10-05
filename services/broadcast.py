"""Rassilka: barcha foydalanuvchilarga xabarni nusxalab yuborish."""
import asyncio

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter


async def run_broadcast(bot, db, admin_chat: int, src_chat: int, src_msg: int):
    ok = fail = 0
    users = await db.user_ids()
    for uid in users:
        for attempt in range(2):
            try:
                await bot.copy_message(uid, src_chat, src_msg)
                ok += 1
                break
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except TelegramForbiddenError:
                await db.set_blocked(uid, True)
                fail += 1
                break
            except Exception:
                fail += 1
                break
        await asyncio.sleep(0.05)   # ~20 xabar/soniya — Telegram limitidan past
    try:
        await bot.send_message(admin_chat, f"✅ Rassilka tugadi.\n\n📨 Yuborildi: <b>{ok}</b>\n🚫 Yetib bormadi: <b>{fail}</b>")
    except Exception:
        pass
