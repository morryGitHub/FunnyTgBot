from aiogram import Router, Bot
from aiogram.filters import Command, or_f, CommandStart, ChatMemberUpdatedFilter, KICKED
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatMemberUpdated
from aiomysql import Pool

from FSM.Shop import ShopStates
from Keyboards.user_kb import mask_kb, inventory_section_kb
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
async def balance_command(message: Message, dp_pool: Pool, user_id: int):
    coins = await get_balance(dp_pool, user_id)
    await message.answer(f"💰 Ваш баланс: {coins} монет 🪙")


@user_messages.message(or_f(Command('dick'), Command('penis')))
async def grow_penis(message: Message, bot: Bot, dp_pool: Pool, chat_id: int, user_id: int, now: int):
    await calculate_new_growth(message=message,
                               bot=bot,
                               dp_pool=dp_pool,
                               user_id=user_id,
                               chat_id=chat_id,
                               now=now)


@user_messages.message(Command("global_top"))
async def show_global_top(message: Message, dp_pool: Pool, user_id):
    rows = await get_scores(dp_pool)
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
    await bot.send_message(
        chat_id=user_id,
        text=f"🏪<i>Магазин</i>: {await get_balance(dp_pool=dp_pool, user_id=user_id)} 🪙\n"
             f"<i>Выберите раздел магазина:<b> Маски | Ускорение </b></i>", parse_mode="HTML",
        reply_markup=mask_kb(page=1))
    await state.set_state(ShopStates.main)


@user_messages.message(Command("profile"))
async def handle_shop(message: Message, dp_pool, user_id, full_name):
    suitcase = await gather_all_items(dp_pool, user_id)
    await message.answer(
        f'<i><a href="tg://user?id={user_id}">{full_name}</a> открывает свой 🧳Чемодан:\n\n'
        f'Маски:  {suitcase or "пусто 😢"}</i>',
        parse_mode="HTML"
    )


@user_messages.message(Command("inventory"))
async def handle_inventory(message: Message, dp_pool, full_name, user_id):
    masks = await get_my_masks(dp_pool, user_id)
    balance = await get_balance(dp_pool, user_id)
    active_mask = await get_active_mask_from_db(dp_pool, user_id)
    kb = inventory_section_kb(masks, "Маски", is_mask=True, user_id=user_id)
    await message.answer(
        f'<i><a href="tg://user?id={user_id}">{full_name}</a> открывает свой 🧳Чемодан:\nБаланс: {balance} 🪙\nМаска: {active_mask}\n\nВыбери стильную маску, чтобы она отображалась рядом с твоим именем в рейтинге. Покажи свой уникальный образ!</i>',
        parse_mode="HTML", reply_markup=kb)


# @user_messages.message(Command('m'))
# async def my_mask(msg: Message, dp_pool, user_id):
#     a = await get_active_mask_from_db(dp_pool, user_id)
#     await msg.answer(f'{a}')


@user_messages.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def process_user_blocked_bot(event: ChatMemberUpdated, dp_pool: Pool):
    await update_user_active(dp_pool, event)
