import logging

from aiogram.types import Message
from aiomysql import Pool

from Database.database import user_active_mask
from Services.game_logic import get_active_mask_from_db


async def mask_name(dp_pool, user_id, name):
    """Добавляет эмодзи или маску перед ником пользователя."""
    active_mask = await get_active_mask_from_db(dp_pool, user_id)
    if active_mask:
        return f"{active_mask} {name}"  # убираем [0], используем весь эмодзи
    return name


async def view_table(message: Message, rows, dp_pool):
    if rows:
        # masked_rows — если хочешь, можно применить mask_name к никнеймам
        masked_rows = [(await mask_name(dp_pool, row[0], row[1]), row[2]) for row in rows]
        logging.debug(masked_rows)
        await message.answer(f"📝 <b>🏆 Hall of Fame: </b>\n\n{show_table(masked_rows)}", parse_mode='HTML')
    else:
        await message.answer("🚫 В базе нет пользователей.")


def show_table(table):
    return "\n".join(
        [f"{reward(i + 1)} {i + 1}. <b>{row[0]}</b>: <b>{row[1]} см</b>" for i, row in enumerate(table)]
    )


def reward(place):
    return ["🥇", "🥈", "🥉", "🎗"][min(place - 1, 3)]
