import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import settings
from database.core import init_db
from handlers import admin, user

async def main():
    logging.basicConfig(level=logging.INFO)

    await init_db()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(admin.router)
    dp.include_router(user.router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")