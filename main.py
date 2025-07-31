import asyncio
import logging

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from Config.config import Config, load_config
from Database.database import close_pool, create_pool
from Handlers.user_callback import user_callback
from Handlers.user_messages import user_messages
from Middleware.db import DbMiddleware, CheckUserMiddleware

logger = logging.getLogger(__name__)


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s'
    )

    config: Config = load_config(r'.env')

    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    logger.info("Connect handlers")
    dp.include_router(user_messages)
    dp.include_router(user_callback)

    try:
        dp['dp_pool'] = await create_pool()
        pool = dp['dp_pool']
        logging.info('Database successfully connected')
    except Exception as error:
        logging.error('Database refused connection')
        logging.error(error)
        return  # Завершаем, если нет базы

    logging.info('Connect Middlewares')
    dp.update.outer_middleware(DbMiddleware(pool))
    dp.update.outer_middleware(CheckUserMiddleware(pool))

    try:
        await dp.start_polling(bot)  # Запуск основного цикла обработки обновлений
    finally:
        # Корректное закрытие ресурсов после остановки бота
        await close_pool(pool)


if __name__ == "__main__":
    logger.info("Bot successfully started")
    try:
        asyncio.run(main())
    except KeyboardInterrupt or RuntimeError:
        logger.info("Bot has shut down")
