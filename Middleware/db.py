import logging
import time
from datetime import datetime
from typing import Callable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiomysql import Pool, Cursor

from Database.db_queries import CHECK_USER_CHAT_EXISTS, INSERT_USER_INTO_USERS, INSERT_USER_INTO_STATS, \
    INSERT_USER_INTO_UsersChats, UPDATE_USER_ACTIVE_UNBAN


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
        user = None
        chat = None
        is_active = None

        if hasattr(event, "from_user") and event.from_user:
            user = event.from_user
            chat = event.chat
        elif hasattr(event, "message") and event.message and event.message.from_user:
            user = event.message.from_user
            chat = event.message.chat
        elif hasattr(event, "callback_query") and event.callback_query and event.callback_query.from_user:
            user = event.callback_query.from_user
            chat = event.callback_query.message.chat
        elif hasattr(event, "my_chat_member") and event.my_chat_member:
            # Если статус не kicked/left, считаем активным
            user = event.my_chat_member.from_user
            chat = event.my_chat_member.chat
            new_status = event.my_chat_member.new_chat_member.status
            is_active = 0 if new_status in ("kicked", "left") else 1
            logging.info(f"User {user.id} status changed → {new_status} (active={is_active})")
        elif user is None:
            # Просто пропускаем или логируем
            logging.warning("Нет from_user в событии, пропускаем middleware")
            return await handler(event, data)

        username = user.username or "Unknown"
        user_id = user.id or 'None'
        chat_id = chat.id or 'None'
        full_name = user.full_name or "Unknown"
        now = int(time.time())  # текущее время в секундах
        data["user_id"] = user_id
        data["username"] = username
        data["chat_id"] = chat_id
        data["full_name"] = full_name
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

                elif is_active:
                    await cursor.execute(UPDATE_USER_ACTIVE_UNBAN, (1, user_id))
                    logging.info(f'Пользователь {user_id} разблокировал бота')

        return await handler(event, data)
