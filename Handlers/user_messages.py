import logging

from aiogram import Router, Bot, F
from aiogram.filters import Command, or_f, CommandStart, ChatMemberUpdatedFilter, KICKED
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatMemberUpdated, LabeledPrice, PreCheckoutQuery
from aiomysql import Pool

from FSM.Shop import ShopStates
from Keyboards.user_kb import mask_kb, inventory_section_kb, kb_get_balance
from Services.game_logic import get_balance, get_scores, calculate_new_growth, game_dice, gather_all_items, \
    get_my_masks, update_user_active, get_active_mask_from_db
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
<b>/start</b> – Start the game 🎮  
<b>/dick</b> – Increase your size randomly 😏  
<b>/game</b> – Play a mini-game to reduce cooldown ⏳  
<b>/global_top</b> – View the global leaderboard 🌍  
<b>/chat_top</b> – View the top players in this chat 💬  
<b>/shop</b> – Open the shop: buy masks & boosts 🏪  
<b>/balance</b> – Check your coin balance 💰  
<b>/profile</b> – Show all your masks 🎭  
<b>/inventory</b> – Manage and equip boosts/masks 🎒  

"""
    await message.answer(commands_text, parse_mode="HTML")


@user_messages.message(Command('balance'))
async def balance_command(message: Message, dp_pool: Pool, user_id: int, full_name):
    coins = await get_balance(dp_pool, user_id)
    kb = kb_get_balance()
    await message.answer(
        f"<a href='tg://user?id={user_id}'>{full_name}</a>, баланс: {coins} монет 🪙",
        reply_markup=kb
    )


@user_messages.message(or_f(Command('dick'), Command('penis')))
async def grow_penis(message: Message, bot: Bot, dp_pool: Pool, chat_id: int, user_id: int, now: int):
    await calculate_new_growth(message=message,
                               bot=bot,
                               dp_pool=dp_pool,
                               user_id=user_id,
                               chat_id=chat_id,
                               now=now)


@user_messages.message(Command("global_top"))
async def show_global_top(message: Message, dp_pool: Pool):
    rows = await get_scores(dp_pool, chat_id=None)
    await view_table(message, rows, dp_pool)


@user_messages.message(Command("chat_top"))
async def show_global_top(message: Message, dp_pool: Pool, chat_id: int):
    rows = await get_scores(dp_pool, chat_id)
    await view_table(message, rows, dp_pool)


@user_messages.message(Command("game"))
async def handle_dice(message: Message, bot: Bot, dp_pool: Pool, user_id: int, chat_id: int, now: int):
    await game_dice(bot=bot,
                    chat_id=chat_id,
                    user_id=user_id,
                    dp_pool=dp_pool,
                    message=message,
                    now=now)


@user_messages.message(Command("shop"))
async def handle_shop(msg: Message, bot: Bot, dp_pool: Pool, user_id: int, state: FSMContext):
    if user_id != msg.chat.id:
        await msg.delete()
    await bot.send_message(
        chat_id=user_id,
        text=f"🏪<i>Магазин</i>: {await get_balance(dp_pool=dp_pool, user_id=user_id)} 🪙\n"
             f"<i>Выберите раздел магазина:<b> Маски | Ускорение | Чемодан </b></i>", parse_mode="HTML",
        reply_markup=mask_kb(page=1))
    await state.set_state(ShopStates.main)


@user_messages.message(or_f(Command("profile"), F.text.lower() == '!ч'))
async def handle_profile(message: Message, bot: Bot, dp_pool, user_id, full_name):
    suitcase = await gather_all_items(dp_pool, user_id)
    await message.answer(
        text=f'<a href="tg://user?id={user_id}">{full_name}</a> открывает свой 🧳Чемодан:\n\n'
             f'<code>Маски:  {suitcase or "пусто 😢"}</code>',
        parse_mode="HTML"
    )


@user_messages.message(Command("inventory"))
async def handle_inventory(msg: Message, bot: Bot, dp_pool, full_name, user_id):
    if user_id != msg.chat.id:
        await msg.delete()

    masks = await get_my_masks(dp_pool, user_id)
    balance = await get_balance(dp_pool, user_id)
    active_mask = await get_active_mask_from_db(dp_pool, user_id)
    kb = inventory_section_kb(masks, "Маски", is_mask=True, user_id=user_id)
    await bot.send_message(
        chat_id=user_id,
        text=f'<i><a href="tg://user?id={user_id}">{full_name}</a> открывает свой 🧳Чемодан:\n'
             f'Баланс: {balance} 🪙\nМаска: {active_mask}\n\n'
             f'Выбери стильную маску, чтобы она отображалась рядом с твоим именем в рейтинге. '
             f'Покажи свой уникальный образ!</i>',
        parse_mode="HTML", reply_markup=kb)


# @user_messages.message(Command('m'))
# async def my_mask(msg: Message, dp_pool, user_id):
#     a = await get_active_mask_from_db(dp_pool, user_id)
#     await msg.answer(f'{a}')
# Команда /pay — отправка инвойса
@user_messages.message(Command("pay"))
async def cmd_pay(message: Message):
    prices = [LabeledPrice(label="Тестовый товар", amount=3)]  # 1000 = 10.00 в копейках/центах

    await message.answer_invoice(
        title="Оплата теста",
        description="Это тестовый товар",
        payload="payload_test",  # строка, которая вернётся в successful_payment
        provider_token="",
        currency="XTR",  #
        prices=prices,
        start_parameter="test-payment",
    )


# Обработчик pre_checkout_query (обязателен)
@user_messages.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


# Обработчик успешной оплаты
@user_messages.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    payment = message.successful_payment
    logging.info(f"Платёж прошёл успешно: {payment.to_python()}")
    await message.answer("✅ Спасибо за оплату!")


@user_messages.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def process_user_blocked_bot(event: ChatMemberUpdated, dp_pool: Pool):
    await update_user_active(dp_pool, event)


@user_messages.message(Command("spam"))
async def spam(mes: Message, bot: Bot):
    await bot.send_message(
        chat_id=1748263745,
        text="У тебя маска снялась, теперь она хранится в дб и не будет исчезать при каждой обнове)"
    )
    await bot.send_message(
        chat_id=6818396490,
        text="У тебя маска снялась, теперь она хранится в дб и не будет исчезать при каждой обнове)"
    )
