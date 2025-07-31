import logging
import time
from datetime import datetime
from typing import Callable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiomysql import Pool, Cursor

from Database.db_queries import CHECK_USER_CHAT_EXISTS, INSERT_USER_INTO_USERS, INSERT_USER_INTO_STATS, \
    INSERT_USER_INTO_UsersChats


class DbMiddleware(BaseMiddleware):
    def __init__(self, pool):
        self.pool: Pool = pool

    async def __call__(self, handler: Callable[[TelegramObject, dict], Any], event: TelegramObject, data: dict):
        data["dp_pool"] = self.pool
        return await handler(event, data)


class CheckUserMiddleware(BaseMiddleware):
    def __init__(self, pool):
        self.pool: Pool = pool

    async def __call__(self, handler: Callable[[TelegramObject, dict], Any], event: TelegramObject, data: dict):
        # Попытка получить пользователя из event
        user = getattr(event, 'from_user', None)
        chat = getattr(event, 'chat', None)

        if not user and hasattr(event, 'message'):
            user = getattr(event.message, 'from_user', None)
            chat = getattr(event.message, 'chat', None)

        if not user and hasattr(event, 'callback_query'):
            user = getattr(event.callback_query, 'from_user', None)
            chat = getattr(event.callback_query.message, 'chat', None)

        username = user.username or "Unknown"
        user_id = user.id
        chat_id = chat.id
        now = int(time.time())  # текущее время в секундах
        data["user_id"] = user_id
        data["username"] = username
        data["chat_id"] = chat_id
        data["now"] = now

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                cursor: Cursor

                # Проверка, есть ли связь user + chat
                await cursor.execute(CHECK_USER_CHAT_EXISTS, (user_id, chat_id))
                (user_chat_exists,) = await cursor.fetchone()

                if not user_chat_exists:
                    # Проверка, есть ли юзер
                    await cursor.execute("SELECT EXISTS(SELECT 1 FROM Users WHERE user_id = %s)", (user_id,))
                    (user_exists,) = await cursor.fetchone()

                    # Если юзера нет — добавляем
                    if not user_exists:
                        await cursor.execute(INSERT_USER_INTO_USERS, (user_id, username, 1))
                        await cursor.execute(INSERT_USER_INTO_STATS, (user_id, 0, 0, 0, 0))

                    # Добавляем связь user-chat
                    await cursor.execute(INSERT_USER_INTO_UsersChats, (user_id, chat_id))
                    message = event.message or event.callback_query.message
                    # await language_handle(message)
                # await cursor.execute(SELECT_USER_ACTIVITY, user_id)
                # (active,) = await cursor.fetchone()
                # if active == 0:
                #     await cursor.execute(UPDATE_USER_ACTIVE, (1, user_id))

        return await handler(event, data)
