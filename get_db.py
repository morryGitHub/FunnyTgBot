import asyncio
from aiogram import Bot
from aiogram.types import FSInputFile

TOKEN = "7821272251:AAF996ZUUrqFXScBRcbwsVJ8mUw6gLujmpY"
CHAT_ID = 782585931  # Узнать можно у @userinfobot

async def send_db():
    bot = Bot(token=TOKEN)
    try:
        file = FSInputFile("dick_bot.db")  # Загружаем файл
        await bot.send_document(CHAT_ID, file, caption="Ваша база данных 📂")
    finally:
        await bot.session.close()

asyncio.run(send_db())
