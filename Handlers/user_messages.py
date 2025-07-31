import logging

from aiogram import Router, Bot
from aiogram.filters import Command, or_f, CommandStart
from aiogram.types import Message
from aiomysql import Pool

from Database.database import masks
from Keyboards.user_kb import shop_kb
from Services.game_logic import get_balance, get_scores, calculate_new_growth, game_dice, get_my_masks, gather_all_masks
from Services.view_logic import view_table

user_messages = Router()


@user_messages.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        f"🎮 Привет, {message.from_user.full_name}!\n"
        "Добро пожаловать в игру! Готов испытать удачу и показать, кто тут топ?\n"
        "Введи /help, чтобы узнать все команды!"
    )


@user_messages.message(Command('help'))
async def help_command(message: Message):
    commands_text = """
<b>/start</b> – Начать игру
<b>/dick</b> – Увеличить свой размер случайным образом 😏
<b>/game</b> – Мини-игра, чтобы сократить время ожидания
<b>/show_global_top</b> – Топ игроков
<b>/show_chat_top</b> – Лидеры этого чата
<b>/buy_mask</b> – Купить маску за монеты 🎭
<b>/buy_boost</b> – Купить буст: ускорение, бонусы и т.д. ⚡
<b>/show_mask</b> – Посмотреть, какие маски у тебя есть
<b>/show_boosts</b> – Посмотреть доступные бусты
"""
    await message.answer(commands_text, parse_mode="HTML")


@user_messages.message(Command('balance'))
async def balance_command(message: Message, dp_pool: Pool, user_id: int):
    coins = await get_balance(dp_pool, user_id)
    await message.answer(f"💰 Ваш баланс: {coins} монет")


@user_messages.message(or_f(Command('dick'), Command('penis')))
async def grow_penis(message: Message, bot: Bot, dp_pool: Pool, chat_id: int, user_id: int, now: int):
    await calculate_new_growth(message=message,
                               bot=bot,
                               dp_pool=dp_pool,
                               user_id=user_id,
                               chat_id=chat_id,
                               now=now)


@user_messages.message(Command("show_global_top"))
async def show_global_top(message: Message, dp_pool: Pool):
    rows = await get_scores(dp_pool)
    await view_table(message, rows)


@user_messages.message(Command("show_chat_top"))
async def show_global_top(message: Message, dp_pool: Pool, chat_id: int):
    rows = await get_scores(dp_pool, chat_id)
    await view_table(message, rows)


@user_messages.message(Command("game"))
async def handle_dice(message: Message, bot: Bot, dp_pool: Pool, user_id: int, chat_id: int, now: int):
    await game_dice(bot=bot,
                    chat_id=chat_id,
                    user_id=user_id,
                    dp_pool=dp_pool,
                    message=message,
                    now=now)


@user_messages.message(Command("shop"))
async def handle_shop(message: Message):
    await message.answer("Выбери маску", reply_markup=shop_kb(page=1))  # ✅ вызываем функцию

    # try:
    #     # Попробуем отредактировать старое сообщение с новым контентом и клавиатурой
    #     bot.edit_message_text("Welcome to the Shop! Choose a mask to buy:", chat_id=message.chat.id,
    #                           message_id=message.message_id, reply_markup=markup)
    # except Exception as e:
    #     # Если редактирование не удалось, отправим новое сообщение
    #     print(f"Error editing message: {e}")
    #     bot.send_message(message.chat.id, "Welcome to the Shop! Choose a mask to buy:", reply_markup=markup)


@user_messages.message(Command("profile"))
async def handle_shop(message: Message, dp_pool, user_id, username):
    suitcase = await gather_all_masks(dp_pool, user_id)

    await message.answer(
        f'<a href="tg://user?id={user_id}">{username}</a> открывает свой 🧳Чемодан:\n\n'
        f'Маски:  {suitcase or "пусто 😢"}',
        parse_mode="HTML"
    )
