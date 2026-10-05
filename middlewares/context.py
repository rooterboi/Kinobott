"""Har bir update uchun kontekst: qaysi bot, qaysi baza, rol (Parent/Child), admin-mi."""
import time

from aiogram import BaseMiddleware
from aiogram.types import Update


class ContextMiddleware(BaseMiddleware):
    def __init__(self, manager):
        self.manager = manager
        self._touched: dict[tuple, float] = {}

    async def __call__(self, handler, event: Update, data: dict):
        bot = data["bot"]
        rt = self.manager.get(bot.id)
        if rt is None:
            return None
        user = data.get("event_from_user")
        data["rt"] = rt
        data["db"] = rt.db
        data["manager"] = self.manager
        data["is_parent"] = rt.is_parent          # CHILD botlarda False — /rooter ishlamaydi
        data["is_admin"] = bool(user and await rt.db.is_admin(user.id))
        if user and not user.is_bot:
            key = (bot.id, user.id)
            now = time.time()
            if now - self._touched.get(key, 0) > 60:   # bazani har updateda yozmaslik uchun
                self._touched[key] = now
                await rt.db.touch_user(user.id, user.full_name, user.username)
        return await handler(event, data)
