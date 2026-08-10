import asyncio
import logging
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Spam himoyasi: foydalanuvchi so'rovlar orasida kamida 0.5 sekund kutadi"""

    def __init__(self, throttle_time: float = 0.5):
        self.throttle_time = throttle_time
        self._user_timestamps: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            now = asyncio.get_event_loop().time()
            last = self._user_timestamps.get(user_id, 0)
            if now - last < self.throttle_time:
                await event.answer("⚠️ Biroz sekinroq yuboring!")
                return
            self._user_timestamps[user_id] = now
        return await handler(event, data)
