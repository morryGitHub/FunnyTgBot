import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiomysql import Pool

from Database.database import MASKS, BOOSTS, user_active_mask
from FSM.Shop import ShopStates
from Keyboards.user_kb import mask_kb, show_category, boosts_kb, inventory_section_kb, InventoryKeyboard
from Services.game_logic import get_balance, set_balance, save_mask_into_db, save_boost_into_db, get_my_masks, \
    get_my_boosts, update_use_boost_with_transaction

user_callback = Router()


@user_callback.callback_query(F.data.startswith("category:"))
async def open_category(callback: CallbackQuery, state: FSMContext, dp_pool, user_id, full_name):
    category = callback.data.split(":")[1]
    balance = await get_balance(dp_pool, user_id)
    await state.update_data(current_category=category)  # сохраняем выбранную категорию
    masks = await get_my_masks(dp_pool, user_id)
    active_mask = user_active_mask.get(user_id, '🚫')
    await show_category(callback.message, category, balance, full_name, page=1, user_masks=masks, active_mask=active_mask)
    await state.set_state(ShopStates.category)


@user_callback.callback_query(F.data.startswith("buy_mask"))
async def buy_mask_from_shop(callback: CallbackQuery, dp_pool: Pool, user_id: int):
    balance = await get_balance(
        dp_pool=dp_pool,
        user_id=user_id
    )
    # buy_mask:mask{count}
    target_id = callback.data.split(":")[1]
    mask = next((m for m in MASKS if m['id'] == target_id), None)

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


@user_callback.callback_query(F.data.startswith("buy_boost"))
async def buy_mask_from_shop(callback: CallbackQuery, dp_pool: Pool, user_id: int):
    balance = await get_balance(
        dp_pool=dp_pool,
        user_id=user_id
    )
    # buy_mask:mask{count}
    target_id = callback.data.split(":")[1]
    boost = next((m for m in BOOSTS if m['id'] == target_id), None)

    if boost:
        price = boost['price']
        name = boost['name']
        time_minutes = boost['time']

    if price > balance:
        await callback.answer("Недостаточно денег на балансе", show_alert=True)
        return

    # Перевод минут в удобный формат (часы/минуты)
    if time_minutes >= 60:
        hours = time_minutes // 60
        minutes = time_minutes % 60
        time_str = f"{hours} ч" + (f" {minutes} мин" if minutes else "")
    else:
        time_str = f"{time_minutes} мин"

    await callback.answer(
        f"🔰 Вы купили буст\n"
        f"(⏳ ускоряет на {time_str}) за {price} 🪙\n"
        f"Баланс: {balance - price} 🪙",
        show_alert=True
    )

    new_balance = balance - price
    await set_balance(dp_pool, user_id, new_balance)
    await save_boost_into_db(dp_pool, user_id, target_id)


@user_callback.callback_query(F.data.startswith("mask_info"))
async def mask_info_handler(callback: CallbackQuery):
    emoji, name = callback.data.split(':')[1:]
    await callback.answer(
        f"{emoji}{name}\n"
        f"Маска используется как знак отличия от других пользователей",
        show_alert=True
    )


@user_callback.callback_query(F.data.startswith("boost_info"))
async def boost_info_handler(callback: CallbackQuery):
    emoji, name, time_minutes = callback.data.split(':')[1:]
    await callback.answer(
        f"{emoji}{name}\n"
        f"⏳ Этот буст сокращает время ожидания на {time_minutes} минут!",
        parseMode="HTML",
        show_alert=True
    )


@user_callback.callback_query(F.data.startswith("page"))
async def pagination(callback: CallbackQuery):
    await callback.answer()
    # page:category
    parts = callback.data.split(":")
    page = int(parts[1])
    category = parts[2]
    if category == "masks":
        kb = mask_kb(page, active_category=category)
    elif category == "boosts":
        kb = boosts_kb(page, active_category=category)
    else:
        kb = None  # якщо раптом якась інша категорія

    if kb:
        await callback.message.edit_reply_markup(reply_markup=kb)


@user_callback.callback_query(F.data == "nothing")
async def nothing(callback: CallbackQuery):
    await callback.answer()


@user_callback.callback_query(F.data.startswith("show_"))
async def switch_section(callback: CallbackQuery, dp_pool, user_id, full_name):
    # callback.data будет, например, "show_masks" или "show_boosts"
    balance = await get_balance(dp_pool, user_id)
    active_mask = user_active_mask.get(user_id, '🚫')

    masks = await get_my_masks(dp_pool, user_id)
    boosts = await get_my_boosts(dp_pool, user_id)
    if callback.data == "show_masks":
        kb = inventory_section_kb(masks, "Маски", is_mask=True, user_id=user_id)
        section_name = "Выбери стильную маску, чтобы она отображалась рядом с твоим именем в рейтинге. Покажи свой уникальный образ!"
    else:
        kb = inventory_section_kb(boosts, "Бусты", is_mask=False, user_id=user_id)
        section_name = "Бусты — активируй их, чтобы мгновенно получить преимущество и сократить время ожидания!"

    text = (f'<i><a href="tg://user?id={user_id}">{full_name}</a> открывает свой 🧳Чемодан:\n'
            f'Баланс: {balance} 🪙\n'
            f'Маска: {active_mask}\n\n'
            f'{section_name}</i>')

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@user_callback.callback_query(F.data.startswith("use_"))
async def use_item(callback: CallbackQuery, dp_pool, full_name):
    user_id = callback.from_user.id
    data = callback.data
    balance = await get_balance(dp_pool, user_id)

    if data.startswith("use_mask:"):
        mask_id = data.split(":")[1]
        matching = next((m for m in MASKS if m['id'] == mask_id), None)
        if matching:
            # Сохраняем активную маску
            user_active_mask[user_id] = matching.get('emoji', '❔')

            # Обновляем клавиатуру
            masks = await get_my_masks(dp_pool, user_id)
            kb = inventory_section_kb(items=masks, section="Маски", is_mask=True, user_id=user_id)

            # Формируем текст с актуальной маской
            active_mask = user_active_mask.get(user_id, '')
            text = (f'<i><a href="tg://user?id={user_id}">{full_name}</a> открывает свой 🧳Чемодан:\n'
                    f'Баланс: {balance} 🪙\n'
                    f'Маска: {active_mask}\n\n'
                    'Выбери стильную маску, чтобы она отображалась рядом с твоим именем в рейтинге. Покажи свой уникальный образ!.</i>')

            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
            await callback.answer(f"Вы активировали маску {active_mask}!")

    elif data.startswith("use_boost:"):
        boost_id = data.split(":")[1]
        matching = next((b for b in BOOSTS if b['id'] == boost_id), None)
        if matching:
            result, message = await update_use_boost_with_transaction(matching, dp_pool, user_id)
            if result:
                await callback.answer(f"{message}")
            else:
                await callback.answer(f"{message}")

            # await callback.answer(f"Вы использовали буст {matching['name']}!")
        else:
            await callback.answer("Буст не найден!", show_alert=True)

        user_boosts = await get_my_boosts(dp_pool, user_id)

        # Строим клавиатуру заново
        kb = InventoryKeyboard.build_boost_inventory(user_boosts, page=1)

        await callback.message.edit_reply_markup(reply_markup=kb)
        await callback.answer(message, show_alert=True)


@user_callback.callback_query(F.data == 'category:inventory')
async def handle_inventory(callback: CallbackQuery, dp_pool, username, user_id):
    masks = await get_my_masks(dp_pool, user_id)
    kb = inventory_section_kb(masks, "Маски", is_mask=True, user_id=user_id)
    balance = await get_balance(dp_pool, user_id)
    active_mask = user_active_mask.get(user_id, '🚫')
    await callback.message.answer(
        f'<i><a href="tg://user?id={user_id}">{username}</a> открывает свой 🧳Чемодан:\nБаланс: {balance} 🪙\nМаска: {active_mask}\n\nВыбери стильную маску, чтобы она отображалась рядом с твоим именем в рейтинге. Покажи свой уникальный образ!</i>',
        parse_mode="HTML", reply_markup=kb)
