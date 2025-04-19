import asyncio
from aiogram import Bot, Dispatcher
from config import read_bot_token
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from handlers.common import common_router
from handlers.menu import menu_router
from handlers.courses import courses_router

from data_manager import DataManager


BOT_TOKEN = read_bot_token()

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
data_manager = DataManager()

async def on_startup():
    """Вызывается при старте бота."""
    await data_manager.load_products_base()  # Загружаем данные

dp.startup.register(on_startup)
dp.include_router(courses_router)
dp.include_router(common_router)
dp.include_router(menu_router)


async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())