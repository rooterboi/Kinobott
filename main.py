"""Kino Bot — ishga tushirish nuqtasi.

Parent bot (.env dagi BOT_TOKEN) + bazada saqlangan barcha Child (sub) botlar
bitta jarayonda, bitta Dispatcher orqali ishlaydi.
"""
import asyncio
import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DATA_DIR
from database import MasterDB
from handlers import setup_routers
from middlewares.context import ContextMiddleware
from middlewares.forcesub import ForceSubMiddleware
from services.manager import BotManager


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not BOT_TOKEN:
        raise SystemExit("❌ .env faylida BOT_TOKEN ko'rsatilmagan (.env.example ga qarang).")

    master = MasterDB(DATA_DIR / "master.db")
    await master.connect()

    dp = Dispatcher(storage=MemoryStorage())
    manager = BotManager(master, dp)

    # 1) kontekst (baza, rol, admin) → 2) majburiy obuna
    dp.update.outer_middleware(ContextMiddleware(manager))
    force_sub = ForceSubMiddleware()
    dp.message.outer_middleware(force_sub)
    dp.callback_query.outer_middleware(force_sub)
    setup_routers(dp)

    try:
        await manager.start_parent(BOT_TOKEN)
        await manager.start_children()
        logging.info("Hammasi tayyor. To'xtatish: Ctrl+C")
        await asyncio.Event().wait()
    finally:
        await manager.stop_all()
        await master.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
