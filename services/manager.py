"""Multibot menejeri: Parent va Child botlarni bitta jarayonda ishga tushiradi.

Har bir bot uchun:
  * alohida Bot obyekti,
  * alohida SQLite baza (data/bot_<id>.db),
  * alohida long-polling task (umumiy Dispatcher orqali).
Rol (is_parent) faqat shu yerda belgilanadi — foydalanuvchi uni o'zgartira olmaydi.
"""
import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand

from config import ADMIN_IDS, DATA_DIR, DEFAULT_ROOTER_CMD, DEFAULT_ROOTER_PIN
from database import Database, MasterDB

log = logging.getLogger(__name__)


class ChildBotError(Exception):
    pass


@dataclass
class Runtime:
    bot: Bot
    db: Database
    is_parent: bool
    owner_id: int
    username: str
    task: asyncio.Task | None = None


class BotManager:
    def __init__(self, master: MasterDB, dp: Dispatcher):
        self.master = master
        self.dp = dp
        self.runtimes: dict[int, Runtime] = {}
        self._bg: set[asyncio.Task] = set()
        self._allowed: list[str] | None = None

    def get(self, bot_id: int) -> Runtime | None:
        return self.runtimes.get(bot_id)

    @staticmethod
    def _make_bot(token: str) -> Bot:
        return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # ------------------------------------------------------------ ishga tushirish
    async def start_parent(self, token: str) -> Runtime:
        bot = self._make_bot(token)
        me = await bot.get_me()
        owner = ADMIN_IDS[0] if ADMIN_IDS else 0
        await self.master.add_bot(me.id, token, me.username, owner, 1)
        return await self._launch(bot, me, owner, True)

    async def start_children(self):
        for row in await self.master.get_bots():
            if row["is_parent"] or not row["active"]:
                continue
            bot = self._make_bot(row["token"])
            try:
                me = await bot.get_me()
            except TelegramUnauthorizedError:
                log.warning("Sub-bot %s tokeni yaroqsiz — o'chirildi", row["bot_id"])
                await self.master.set_active(row["bot_id"], 0)
                await bot.session.close()
                continue
            except Exception:
                log.exception("Sub-bot %s ni ishga tushirib bo'lmadi", row["bot_id"])
                await bot.session.close()
                continue
            await self._launch(bot, me, row["owner_id"], False)

    async def create_child(self, token: str, owner_id: int) -> Runtime:
        """/rooter orqali yangi sub-bot yaratish: token tekshiriladi, bazaga yoziladi, bot ishga tushadi."""
        try:
            bot = self._make_bot(token)
            me = await bot.get_me()
        except Exception:
            raise ChildBotError("Token noto'g'ri yoki bot topilmadi.")
        if await self.master.get_bot(me.id) or me.id in self.runtimes:
            await bot.session.close()
            raise ChildBotError("Bu bot allaqachon qo'shilgan.")
        await self.master.add_bot(me.id, token, me.username, owner_id, 0)   # is_parent = 0 (CHILD)
        return await self._launch(bot, me, owner_id, False)

    async def _launch(self, bot: Bot, me, owner_id: int, is_parent: bool) -> Runtime:
        db = Database(DATA_DIR / f"bot_{me.id}.db")
        await db.connect()
        if is_parent:
            for a in ADMIN_IDS:
                await db.add_admin(a)
            if await db.get_setting("rooter_cmd") is None:
                await db.set_setting("rooter_cmd", DEFAULT_ROOTER_CMD)
            if await db.get_setting("rooter_pin") is None:
                await db.set_setting("rooter_pin", DEFAULT_ROOTER_PIN)
        elif owner_id:
            await db.add_admin(owner_id)
        try:
            await bot.delete_webhook(drop_pending_updates=False)
            await bot.set_my_commands([BotCommand(command="start", description="🚀 Boshlash"),
                                       BotCommand(command="help", description="ℹ️ Yordam")])
        except Exception:
            log.exception("Webhook/commands sozlanmadi")
        rt = Runtime(bot=bot, db=db, is_parent=is_parent, owner_id=owner_id, username=me.username or "")
        self.runtimes[me.id] = rt
        rt.task = asyncio.create_task(self._poll(rt), name=f"poll-{me.id}")
        log.info("Bot ishga tushdi: @%s (%s)", me.username, "PARENT" if is_parent else "CHILD")
        return rt

    # ------------------------------------------------------------ polling
    async def _poll(self, rt: Runtime):
        if self._allowed is None:
            self._allowed = self.dp.resolve_used_update_types()
        offset = None
        while True:
            try:
                updates = await rt.bot.get_updates(offset=offset, timeout=25, allowed_updates=self._allowed)
                for u in updates:
                    offset = u.update_id + 1
                    t = asyncio.create_task(self._feed(rt, u))
                    self._bg.add(t)
                    t.add_done_callback(self._bg.discard)
            except asyncio.CancelledError:
                raise
            except TelegramUnauthorizedError:
                log.warning("@%s tokeni bekor qilingan, polling to'xtatildi", rt.username)
                await self.master.set_active(rt.bot.id, 0)
                self.runtimes.pop(rt.bot.id, None)
                return
            except Exception as e:
                log.warning("Polling xatosi @%s: %s", rt.username, e)
                await asyncio.sleep(3)

    async def _feed(self, rt: Runtime, update):
        try:
            await self.dp.feed_update(rt.bot, update)
        except Exception:
            log.exception("Update qayta ishlashda xato")

    # ------------------------------------------------------------ to'xtatish
    async def _stop(self, rt: Runtime):
        if rt.task:
            rt.task.cancel()
            await asyncio.gather(rt.task, return_exceptions=True)
        try:
            await rt.bot.session.close()
        finally:
            await rt.db.close()

    async def remove_child(self, bot_id: int) -> bool:
        rt = self.runtimes.get(bot_id)
        if rt and rt.is_parent:
            return False
        if rt:
            self.runtimes.pop(bot_id, None)
            await self._stop(rt)
        await self.master.delete_bot(bot_id)
        return True

    async def stop_all(self):
        for rt in list(self.runtimes.values()):
            await self._stop(rt)
        self.runtimes.clear()
