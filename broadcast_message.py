import asyncio
import sqlite3
import textwrap

from aiogram import Bot

TOKEN = "7821272251:AAF996ZUUrqFXScBRcbwsVJ8mUw6gLujmpY"  # Замініть на ваш справжній токен


def get_all_chat_ids():
    """Отримує всі chat_id з бази даних"""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM users")
    chat_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return chat_ids


async def send_broadcast_message(bot, chat_ids, message):
    """Надсилає повідомлення всім користувачам"""
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"Повідомлення надіслано {chat_id}")
        except Exception as e:
            print(f"Помилка відправки {chat_id}: {e}")


async def main():
    # chat_ids = get_all_chat_ids()  # Отримуємо список chat_id з бази
    chat_ids = [782585931]
    if not chat_ids:
        print("Немає користувачів для розсилки.")
        return

    message = textwrap.dedent("""\
        🌍 Приглашаем в World Penis Group! 🌍

        🔥 Уникальное место для настоящих мужчин и не только! 🔥

        Присоединяйся к World Penis Group – здесь мы делимся идеями, обсуждаем самое интересное и вместе создаём что-то действительно крутое!

        💬 Есть предложения или пожелания? Пиши, и мы сделаем сообщество ещё лучше!
        
        🚀 Только лучший контент и дружеская атмосфера!

        🔗 Не тормози – заходи! 👉 https://t.me/worldPenisGroup
    """)

    bot = Bot(token=TOKEN)

    try:
        await send_broadcast_message(bot, chat_ids, message)
    finally:
        await bot.session.close()  # Закриваємо сесію після використання


# Запуск асинхронного коду
asyncio.run(main())
