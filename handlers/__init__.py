"""Routerlarni tartib bilan ulash.

Tartib muhim: umumiy buyruqlar → /rooter → admin → foydalanuvchi (oxirida umumiy matn qidiruvi).
"""
from aiogram import Dispatcher

from . import common, rooter
from .admin import broadcast, channels, manage, panel, settings, wizard
from .user import content, search


def setup_routers(dp: Dispatcher):
    dp.include_routers(
        common.router,
        rooter.router,
        panel.router,
        wizard.router,
        manage.router,
        channels.router,
        broadcast.router,
        settings.router,
        content.router,
        search.router,     # eng oxirida — oddiy matn = qidiruv
    )
