import logging
from random import randint, random

import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramAPIError
from aiogram.types import Message
from aiomysql import Pool, DictCursor

from Database.database import user_chat_messages, masks
from Database.db_queries import SELECT_COIN_FROM_STATS, SELECT_ALL_SCORES, SELECT_ALL_SCORES_FROM_CHAT, \
    UPDATE_AFTER_DICE, SELECT_SCORE_FROM_STATS, UPDATE_STATS_SCORE_TIME, UPDATE_STATS_COIN, SELECT_TIMES_FROM_STATS, \
    ADD_NEW_MASK, SELECT_MASKS_FOR_USER

HOURS_12 = 43200  # 12 hours
HOURS_3 = 10800  # 3 hours


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
                # Если победил
                await cursor.execute(SELECT_COIN_FROM_STATS, (user_id,))
                result_coin = await cursor.fetchone()
                time_hour = calculate_reduce_time(value)
                # Прибавляем монет
                coin = (result_coin[0] if result_coin else 0) + time_hour
                # Сокращаем время
                new_last_used = calculate_new_wait_time(last_used, time_hour)

                await asyncio.sleep(4)
                await bot.send_message(chat_id=user_id,
                                       text=f"🎉 Поздравляю, победа! Ты сокращаешь время ожидания на {time_hour} час(а)! 🌟\n"
                                            f"💰 Получено монет: {time_hour} 🪙")
                await cursor.execute(UPDATE_AFTER_DICE, (new_last_used, coin, now, user_id))
            else:
                # Если проиграл
                await asyncio.sleep(4)
                await bot.send_message(chat_id=user_id,
                                       text="😢 Увы, ты проиграл. Попробуй снова! 🎲")

                current_coins = await get_balance(dp_pool, user_id)
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
                    await process_dice_result(bot, dp_pool, user_id, last_used, now)
                except TelegramForbiddenError:
                    await message.answer("Для начала активируйте бот.")
                    return
                finally:
                    await delete_user_messages(bot, user_id, chat_id)


async def delete_user_messages(bot: Bot, user_id: int, chat_id: int, msg: Message | None = None):
    """
        Delete dice messages from chat
        Only deletes in group chats, not in private messages
        """
    message_id = user_chat_messages.get(user_id)

    if message_id is None:
        logging.debug(f"No dice message found for user {user_id}")
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


async def gather_all_masks(dp_pool, user_id):
    res = await get_my_masks(dp_pool, user_id)

    sorted_res = sorted(res, key=lambda x: x['count'], reverse=True)

    full_str = ""
    for user_mask in sorted_res:
        # Ищем маску по id
        matching_mask = next((m for m in masks if m['id'] == user_mask['mask_id']), None)
        if matching_mask:
            emoji = matching_mask['emoji']
            count = user_mask['count']
            full_str += f"{'' if count == 1 else count}{emoji}"
        else:
            logging.error(f"Неизвестная маска ID: {user_mask['mask_id']}")
    return full_str
