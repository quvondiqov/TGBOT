import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import create_tables
from handlers import start, registration, browse, payment
from middlewares.throttling import ThrottlingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN or "your_telegram_bot_token" in BOT_TOKEN:
        logger.error("BOT_TOKEN hali .env faylida ko'rsatilmagan!")
        print("\n=======================================================")
        print("ILTIMOS, .env FAYLINI OCHIB BOT_TOKEN NI KIRITING!")
        print("Masalan: BOT_TOKEN=777000111:AAEE... (@BotFather)")
        print("=======================================================\n")
        return

    # Ma'lumotlar bazasini yaratish
    await create_tables()
    logger.info("✅ Ma'lumotlar bazasi tayyor")

    try:
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    except Exception as e:
        logger.error(f"Telegram Bot token xato: {e}")
        print("\nIltimos, .env faylidagi BOT_TOKEN ni tekshiring!")
        return

    dp = Dispatcher(storage=MemoryStorage())

    # Middleware
    dp.message.middleware(ThrottlingMiddleware(throttle_time=0.5))

    # Handlerlarni ro'yxatdan o'tkazish
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(browse.router)
    dp.include_router(payment.router)

    logger.info("🚀 Bot polling rejimida ishga tushdi!")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    asyncio.run(main())
