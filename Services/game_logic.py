import logging
import time
from random import randint, random

import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramAPIError
from aiogram.types import Message, TelegramObject
from aiomysql import Pool, DictCursor

from Database.database import user_chat_messages, MASKS, BOOSTS, HOURS_12, HOURS_3
from Database.db_queries import SELECT_COIN_FROM_STATS, SELECT_ALL_SCORES, SELECT_ALL_SCORES_FROM_CHAT, \
    UPDATE_AFTER_DICE, SELECT_SCORE_FROM_STATS, UPDATE_STATS_SCORE_TIME, UPDATE_STATS_COIN, SELECT_TIMES_FROM_STATS, \
    ADD_NEW_MASK, SELECT_MASKS_FOR_USER, ADD_NEW_BOOST, SELECT_BOOSTS_FOR_USER, UPDATE_STATS_LAST_USED, \
    CHECK_BOOST_COUNT, DEL_BOOST_UPDATE, DEL_BOOST_CLEANUP


async def custom_randint():
    """Calculate growth value
    More likely to be positive (growth) than negative (loss)"""
    for _ in range(10):  # max 10 tries
        grow = randint(-5, 10)
        if grow >= 0 or random() < 0.5:
            return grow
    return 0


async def get_balance(dp_pool: Pool, user_id):
    """Get user's balance from database"""
    async with dp_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Получаем баланс монет пользователя
            await cursor.execute(SELECT_COIN_FROM_STATS, (user_id,))
            row = await cursor.fetchone()
            logging.debug('Balance got')
            return row[0] if row else 0


async def get_balance_by_cursor(cursor, user_id):
    """Get user's balance using existing cursor"""
    await cursor.execute(SELECT_COIN_FROM_STATS, (user_id,))
    row = await cursor.fetchone()
    logging.debug('Balance got via existing cursor')
    return row[0] if row else 0


async def set_balance(dp_pool: Pool, user_id: int, balance: int):
    """Set user's balance into database"""
    async with dp_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Меняем баланс монет пользователя
            await cursor.execute(UPDATE_STATS_COIN, (balance, user_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_scores(dp_pool: Pool, chat_id: int = None):
    """Get all scores from database"""
    async with dp_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            if chat_id is None:
                await cursor.execute(SELECT_ALL_SCORES)
            else:
                await cursor.execute(SELECT_ALL_SCORES_FROM_CHAT, (chat_id,))
            row = await cursor.fetchall()
            logging.debug(f"get_scores +> {row}")
            return row


async def process_dice_result(bot: Bot, dp_pool, user_id, last_used, now):
    try:
        dice_message = await asyncio.wait_for(bot.send_dice(chat_id=user_id), timeout=5.0)
        value = dice_message.dice.value
    except asyncio.TimeoutError:
        logging.warning("Dice was crushed")
        await bot.send_message(chat_id=user_id, text="Try again")
        return
    except TelegramAPIError as e:
        logging.warning(f"Error Telegram API: {e}")
        await bot.send_message(chat_id=user_id, text="Try again")
        return

    async with dp_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            if is_winning_dice(value):
                result_coin = await get_balance_by_cursor(cursor, user_id)
                time_hour = calculate_reduce_time(value)
                coin = result_coin + time_hour
                new_last_used = calculate_new_wait_time(last_used, time_hour)

                await asyncio.sleep(4)
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🎉 Поздравляю, победа! Ты сокращаешь время ожидания на {time_hour} час(а)! 🌟\n"
                        f"💰 Получено монет: {time_hour} 🪙"
                    )
                )
                await cursor.execute(UPDATE_AFTER_DICE, (new_last_used, coin, now, user_id))
            else:
                await asyncio.sleep(4)
                await bot.send_message(chat_id=user_id, text="😢 Увы, ты проиграл. Попробуй снова! 🎲")

                current_coins = await get_balance_by_cursor(cursor, user_id)
                await cursor.execute(UPDATE_AFTER_DICE, (last_used, current_coins, now, user_id))


def is_winning_dice(value):
    """Check if the dice value is a winning roll (4, 5 or 6)"""
    return value in [4, 5, 6]


def calculate_reduce_time(value):
    """Calculate hours of time reduction based on dice value"""
    return value - 3


def calculate_new_wait_time(last_used, time_hour):
    """Calculate a new wait time after reducing"""
    new_time = last_used - 3600 * time_hour
    return max(0, new_time)


async def calculate_new_growth(message: Message, bot: Bot, dp_pool: Pool, chat_id: int, user_id: int, now: int):
    user_chat_messages[user_id] = message.message_id
    async with dp_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(SELECT_SCORE_FROM_STATS, (user_id,))
            row = await cursor.fetchone()
            if row:
                score, last_used = row
                # Если команда уже использовалась, и прошло меньше 12 часов
                if now - last_used < HOURS_12:
                    hours, minutes = calculate_remaining_time(HOURS_12, now, last_used)
                    msg = await message.reply(
                        f"🚫 Вы уже использовали эту команду. Попробуйте снова через {hours}ч {minutes}м.")
                    await asyncio.sleep(5)
                    await delete_user_messages(bot, user_id, chat_id, msg)

                    return
                grow = await custom_randint()  # -5 to 10
                new_score = score + grow

                # Get current balance and add coins (minimum 1 coin)
                current_coins = await get_balance(dp_pool, user_id)
                coins_to_add = max(1, grow)
                new_coin_balance = current_coins + coins_to_add

                # Update database
                await cursor.execute(UPDATE_STATS_SCORE_TIME, (new_score, now, user_id))
                await cursor.execute(UPDATE_STATS_COIN, (new_coin_balance, user_id))
                # Send response message

                await message.answer(
                    f"🌱 Ваш член {'вырос' if grow >= 0 else 'уменьшился'}: на <b>{grow}</b> см.\n"
                    f"📏 Теперь размер: <b>{new_score}</b> см."
                    f"💰 Получено монет: <b>{coins_to_add}</b> 🪙",
                    parse_mode='HTML'
                )


def calculate_remaining_time(waiting: int, now: int, last_used: int):
    remaining = waiting - (now - last_used)
    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    return hours, minutes


async def game_dice(bot: Bot, message: Message, dp_pool: Pool, user_id: int, chat_id: int, now: int):
    user_chat_messages[user_id] = message.message_id
    async with dp_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(SELECT_TIMES_FROM_STATS, (user_id,))
            rows = await cursor.fetchone()

            if rows:
                last_used, dice_control = rows

                try:
                    if last_used == 0:
                        await bot.send_message(
                            chat_id=user_id,
                            text="Сперва вам нужно стартовать. Введите /dick",
                            parse_mode="HTML")
                        return

                    if now - dice_control < HOURS_3:
                        hours, minutes = calculate_remaining_time(HOURS_3, now, dice_control)
                        await bot.send_message(
                            chat_id=user_id,
                            text=f"🚫 Вы уже использовали эту команду недавно. Попробуйте снова через {hours}ч {minutes}м.")
                        return

                    await bot.send_message(chat_id=user_id,
                                           text="🎲 Игра начинается! Удачи! 🍀")
                    logging.debug("Game is started")
                    await process_dice_result(bot, dp_pool, user_id, last_used, now)
                    logging.debug("Game finish")
                except TelegramForbiddenError:
                    await message.answer("Для начала активируйте бот.")
                    return
                finally:
                    await delete_user_messages(bot, user_id, chat_id)


async def delete_user_messages(bot: Bot, user_id: int, chat_id: int, msg: Message | None = None):
    """
        Delete messages from chat
        Only deletes in group chats, not in private messages
        """
    message_id = user_chat_messages.get(user_id)

    if message_id is None:
        logging.debug(f"No message found for user {user_id}")
        return

    if chat_id != user_id:
        try:
            if msg is not None:
                await msg.delete()
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramBadRequest as e:
            # Message might already be deleted or doesn't exist
            logging.warning(f"Could not delete dice message {message_id}: {e}")
        except TelegramForbiddenError as e:
            # Bot doesn't have permission to delete messages
            await bot.send_message(chat_id=chat_id, text=f"No permission to delete message in chat {chat_id}")
            logging.warning(f"No permission to delete message in chat {chat_id}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error deleting dice message: {e}")

    user_chat_messages.pop(user_id, None)


async def save_mask_into_db(dp_pool: Pool, user_id: int, mask_id: str):
    async with dp_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(ADD_NEW_MASK, (user_id, mask_id))


async def save_boost_into_db(dp_pool: Pool, user_id: int, boost_id: str):
    async with dp_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(ADD_NEW_BOOST, (user_id, boost_id))


# async def update_balance_and_mask(dp_pool: Pool, user_id: int, new_balance: int, target_id: str):
#     async with dp_pool.acquire() as conn:
#         async with conn.cursor() as cursor:
#             await conn.begin()  # начинаем транзакцию
#             try:
#                 # Выполняем первое действие — обновление баланса
#                 await set_balance(dp_pool, user_id, new_balance)
#
#                 # Выполняем второе — сохранение маски
#                 await save_mask_into_db(dp_pool, user_id, target_id)
#
#                 await conn.commit()  # коммитим изменения, если всё успешно
#             except Exception:
#                 await conn.rollback()  # откатываем при ошибке
#                 raise


async def get_my_masks(dp_pool, user_id):
    async with dp_pool.acquire() as conn:
        async with conn.cursor(DictCursor) as cursor:
            await cursor.execute(SELECT_MASKS_FOR_USER, (user_id,))
            return await cursor.fetchall()


async def get_my_boosts(dp_pool, user_id):
    async with dp_pool.acquire() as conn:
        async with conn.cursor(DictCursor) as cursor:
            await cursor.execute(SELECT_BOOSTS_FOR_USER, (user_id,))
            return await cursor.fetchall()


async def gather_all_items(dp_pool, user_id):
    # Получаем данные
    masks = await get_my_masks(dp_pool, user_id)  # [{'mask_id': 'mask1', 'count': 2}, ...]
    boosts = await get_my_boosts(dp_pool, user_id)  # [{'boost_id': 'boost3', 'count': 1}, ...]

    # Сортируем по count
    sorted_masks = sorted(masks, key=lambda x: x['count'], reverse=True)
    sorted_boosts = sorted(boosts, key=lambda x: x['count'], reverse=True)

    full_str = ""

    # Обрабатываем маски
    for user_mask in sorted_masks:
        matching_mask = next((m for m in MASKS if m['id'] == user_mask['mask_id']), None)
        if matching_mask:
            count = user_mask['count']
            emoji = matching_mask['emoji']
            full_str += f"{emoji}" if count == 1 else f"{count}{emoji}"
        else:
            logging.error(f"Неизвестная маска ID: {user_mask['mask_id']}")
    full_str += "\nЭнергетики: "

    # Обрабатываем бусты
    for user_boost in sorted_boosts:
        matching_boost = next((b for b in BOOSTS if b['id'] == user_boost['boost_id']), None)
        if matching_boost:
            emoji = "⚡"
            count = user_boost.get("count", 1)
            time_str = matching_boost['name'].split()[-1]  # Берём только время, например "2h"
            full_str += f"{emoji}{time_str}x{count}" if count > 1 else f"{emoji}{time_str}"
        else:
            logging.error(f"Неизвестный буст ID: {user_boost['boost_id']}")

    return full_str


async def check_and_use_boost_from_inventory(cursor, user_id: int, boost_id: str):
    """
    Проверяет наличие буста и использует его из инвентаря
    """
    try:
        # Проверяем наличие буста
        await cursor.execute(CHECK_BOOST_COUNT, (user_id, boost_id))
        result = await cursor.fetchone()

        if not result or result[0] <= 0:
            return False, "❌ У вас нет этого буста"

        current_count = result[0]

        # Уменьшаем количество на 1
        await cursor.execute(DEL_BOOST_UPDATE, (user_id, boost_id))

        if cursor.rowcount == 0:
            return False, "❌ Не удалось использовать буст"

        # Если осталось 0 бустов, удаляем запись
        if current_count == 1:
            await cursor.execute(DEL_BOOST_CLEANUP, (user_id, boost_id))

        remaining_count = current_count - 1
        message = f"✅ Буст использован! Осталось: {remaining_count}"

        return True, message

    except Exception as e:
        logging.error(f"Error using boost {boost_id} for user {user_id}: {e}")
        return False, "❌ Произошла ошибка при использовании буста из инвентаря"


def format_time_reduction(seconds: int) -> str:
    """
    Форматирует время в удобочитаемый вид
    """
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes} мин"
        else:
            return f"{minutes} мин {remaining_seconds} сек"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes == 0:
            return f"{hours} ч"
        else:
            return f"{hours} ч {remaining_minutes} мин"


# Альтернативная версия основной функции с транзакциями
async def update_use_boost_with_transaction(boost_info: dict, dp_pool, user_id: int):
    """
    Версия с явными транзакциями для большей надежности
    """
    try:
        boost_id, name, time_seconds, price = boost_info.values()

        if time_seconds <= 0:
            return False, "❌ Время уменьшения должно быть положительным"

        async with dp_pool.acquire() as conn:
            # Начинаем транзакцию
            await conn.begin()

            try:
                async with conn.cursor() as cursor:
                    # 1. Проверяем и используем буст
                    boost_available, boost_message = await check_and_use_boost_from_inventory(
                        cursor, user_id, boost_id
                    )

                    if not boost_available:
                        await conn.rollback()
                        return False, boost_message

                    # 2. Обновляем время ожидания
                    await cursor.execute(SELECT_SCORE_FROM_STATS, (user_id,))
                    row = await cursor.fetchone()

                    if not row:
                        await conn.rollback()
                        return False, "❌ Пользователь не найден"

                    score, last_used = row
                    if time.time() - last_used > HOURS_12:
                        return False, "⏳ Прошло уже больше 12 часов - буст больше не нужен!"
                    new_last_used = last_used - time_seconds

                    await cursor.execute(UPDATE_STATS_LAST_USED, (new_last_used, user_id))

                    if cursor.rowcount == 0:
                        await conn.rollback()
                        return False, "❌ Не удалось обновить время ожидания"

                    # Если всё прошло успешно, фиксируем транзакцию
                    await conn.commit()

                    time_str = format_time_reduction(time_seconds)
                    return True, f"✅ Время ожидания уменьшено на {time_str}!"

            except Exception as e:
                await conn.rollback()
                logging.error(f"Transaction error for user {user_id}: {e}")
                return False, "❌ Произошла ошибка при использовании буста"

    except Exception as e:
        logging.error(f"Error in update_use_boost_with_transaction for user {user_id}: {e}")
        return False, "❌ Произошла ошибка при использовании буста"


async def update_user_active(dp_pool: Pool, event: TelegramObject):
    async with dp_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(UPDATE_USER_ACTIVE, (0, event.from_user.id))
            logging.info(f'Пользователь {event.from_user.id} заблокировал бота')
