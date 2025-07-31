from aiogram import Router, Bot, F
from aiogram.filters import Command, or_f, CommandStart
from aiogram.types import Message, CallbackQuery
from aiomysql import Pool

from Database.database import masks
from Keyboards.user_kb import shop_kb
from Services.game_logic import get_balance, get_scores, calculate_new_growth, game_dice, set_balance, save_mask_into_db
from Services.view_logic import view_table

user_callback = Router()


@user_callback.callback_query(F.data.startswith("buy_mask"))
async def buy_mask_from_shop(callback: CallbackQuery, dp_pool: Pool, user_id: int):
    balance = await get_balance(
        dp_pool=dp_pool,
        user_id=user_id
    )
    # buy_mask:mask{count}
    target_id = callback.data.split(":")[1]
    mask = next((m for m in masks if m['id'] == target_id), None)

    if mask:
        price = mask['price']
        emoji = mask['emoji']

    if price > balance:
        await callback.answer("Недостаточно денег на балансе")
        return

    await callback.answer(f"🔰 Вы купили {emoji} за {price} 🪙\nБаланс: {balance - price} 🪙", show_alert=True)
    new_balance = balance - price
    await set_balance(dp_pool, user_id, new_balance)
    await save_mask_into_db(dp_pool, user_id, target_id)


@user_callback.callback_query(F.data.startswith("page"))
async def pagination(callback: CallbackQuery):
    await callback.answer()
    # page:count
    page = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup(reply_markup=shop_kb(page))


@user_callback.callback_query(F.data == "nothing")
async def nothing(callback: CallbackQuery):
    await callback.answer()
