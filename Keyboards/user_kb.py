import math

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from Database.database import masks

ITEMS_PER_PAGE = 5


def shop_kb(page):
    """Create inline keyboard for shop with mask buttons"""
    buttons = []  # Create list to hold button rows
    navigation_buttons = []

    sorted_mask = sorted(masks, key=lambda x: x.get("price"))

    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE

    page_items = sorted_mask[start_index:end_index]

    for info_mask in page_items:
        id_mask = info_mask.get("id")
        price = info_mask.get("price", "N/A")
        emoji = info_mask.get("emoji", "🚫")

        if id_mask is not None:
            button = InlineKeyboardButton(
                text=f"{emoji} - {price} Coins",
                callback_data=f"buy_mask:{id_mask}"
            )
            buttons.append([button])

    if page == 1:
        navigation_buttons.append(InlineKeyboardButton(text="✖️", callback_data="nothing"))

    if page > 1:  # Если это не первая страница, добавляем кнопку "Назад"
        navigation_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{page - 1}"))

    navigation_buttons.append(InlineKeyboardButton(text=f"Page {page}", callback_data="nothing"))
    # Проверяем, есть ли товары на следующей странице
    if end_index < len(masks):
        # Если на следующей странице есть товары, добавляем кнопку "Next"
        navigation_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{page + 1}"))

    if page == math.ceil(len(masks) / ITEMS_PER_PAGE):
        navigation_buttons.append(InlineKeyboardButton(text="✖️", callback_data="nothing"))

    buttons.append(navigation_buttons)
    return InlineKeyboardMarkup(inline_keyboard=buttons)
