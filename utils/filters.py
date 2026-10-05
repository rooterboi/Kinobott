from aiogram.filters import BaseFilter


class IsAdmin(BaseFilter):
    """Middleware hisoblagan is_admin bayrog'i bo'yicha."""

    async def __call__(self, event, is_admin: bool = False) -> bool:
        return is_admin
      
