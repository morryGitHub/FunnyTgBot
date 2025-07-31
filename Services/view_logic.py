from aiogram.types import Message


async def view_table(message: Message, rows):
    if rows:
        masked_rows = [(row[0], row[1]) for row in rows]
        await message.answer(f"📝 <b>🏆 Hall of Fame: </b>\n\n{show_table(masked_rows)}", parse_mode='HTML')

    else:
        await message.answer("🚫 В базе нет пользователей.")


def show_table(table):
    return "\n".join(
        [f"{reward(i + 1)} {i + 1}. <b>{row[0]}</b>: <b>{row[1]} см</b>" for i, row in enumerate(table)]
    )


def reward(place):
    return ["🥇", "🥈", "🥉", "🎗"][min(place - 1, 3)]


def mask_name(username, user_id):
    """Добавляет эмодзи или маску перед ником пользователя."""
    pass

    # # Получаем активную маску пользователя из базы данных
    # conn = sqlite3.connect('dick_bot.db')
    # cursor = conn.cursor()
    # cursor.execute("SELECT active_mask FROM info WHERE user = ?", (user,))
    # active_mask = cursor.fetchone()
    # conn.close()
    #
    # # Если маска найдена, добавляем её перед именем
    # if active_mask and active_mask[0]:
    #     return f"{active_mask[0]} {name}"
    # else:
    #     # Если маска не найдена, просто возвращаем имя
    #     return f"{name}"
