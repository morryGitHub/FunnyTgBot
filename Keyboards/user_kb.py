import math
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from Database.database import MASKS, BOOSTS, user_active_mask, BOOSTS_MAP


# Constant
class ShopConfig:
    """Configuration constants for shop pagination and display"""
    MASKS_PER_PAGE = 5
    BOOSTS_PER_PAGE = 4
    INVENTORY_ITEMS_PER_ROW = 3

    # Emojis
    INFO_EMOJI = '❔'
    COIN_EMOJI = '💰'
    LOCK_EMOJI = '🔒'
    PREV_EMOJI = '<'
    NEXT_EMOJI = '>'
    SEARCH_EMOJI = '🔎'
    LOW_BATTERY_EMOJI = '🪫'
    BATTERY_EMOJI = '🔋'
    LIGHTNING_EMOJI = '⚡'
    ACTIVE_MARKER = '👉🏻'
    PIN_EMOJI = '🧷'


class Category(Enum):
    """Shop categories enumeration"""
    MASKS = "masks"
    BOOSTS = "boosts"
    INVENTORY = "inventory"


@dataclass
class PaginationInfo:
    """Data class for pagination information"""
    page: int
    total_pages: int
    start_index: int
    end_index: int
    has_prev: bool
    has_next: bool


class ShopKeyboardBuilder:
    """Builder class for shop keyboards with common functionality"""

    @staticmethod
    def calculate_pagination(items: List, page: int, items_per_page: int) -> PaginationInfo:
        """Calculate pagination details for any list of items"""
        total_pages = max(1, math.ceil(len(items) / items_per_page))
        start_index = (page - 1) * items_per_page
        end_index = start_index + items_per_page

        return PaginationInfo(
            page=page,
            total_pages=total_pages,
            start_index=start_index,
            end_index=end_index,
            has_prev=page > 1,
            has_next=end_index < len(items)
        )

    @staticmethod
    def create_navigation_row(
            pagination: PaginationInfo,
            active_category: str,
            callback_prefix: str = "page"
    ) -> List[InlineKeyboardButton]:
        """Create navigation buttons row with cyclic navigation"""
        navigation = []

        # Left navigation - если первая страница, то переход на последнюю
        if pagination.page == 1:
            navigation.append(
                InlineKeyboardButton(
                    text=ShopConfig.PREV_EMOJI,
                    callback_data=f"{callback_prefix}:{pagination.total_pages}:{active_category}"
                )
            )

        else:
            navigation.append(
                InlineKeyboardButton(
                    text=ShopConfig.PREV_EMOJI,
                    callback_data=f"{callback_prefix}:{pagination.page - 1}:{active_category}"
                )
            )

        # Page counter
        navigation.append(
            InlineKeyboardButton(
                text=f"Page {pagination.page}/{pagination.total_pages}",
                callback_data="nothing"
            )
        )

        # Right navigation - если последняя страница, то переход на первую
        if pagination.page == pagination.total_pages:
            navigation.append(
                InlineKeyboardButton(
                    text=ShopConfig.NEXT_EMOJI,
                    callback_data=f"{callback_prefix}:1:{active_category}"
                )
            )
        else:
            navigation.append(
                InlineKeyboardButton(
                    text=ShopConfig.NEXT_EMOJI,
                    callback_data=f"{callback_prefix}:{pagination.page + 1}:{active_category}"
                )
            )

        return navigation

    @staticmethod
    def create_category_row(active_category: str, include_inventory: bool = True) -> List[InlineKeyboardButton]:
        """Create category selection buttons"""
        mask_active = active_category == Category.MASKS.value
        boost_active = active_category == Category.BOOSTS.value
        inventory_active = active_category == Category.INVENTORY.value

        buttons = []

        mask_btn = InlineKeyboardButton(
            text=f"{ShopConfig.SEARCH_EMOJI} Маски" if mask_active else "Маски",
            callback_data="nothing" if mask_active else f"category:{Category.MASKS.value}"
        )
        buttons.append(mask_btn)

        boost_btn = InlineKeyboardButton(
            text=f"{ShopConfig.SEARCH_EMOJI} Бусты" if boost_active else "Бусты",
            callback_data="nothing" if boost_active else f"category:{Category.BOOSTS.value}"
        )
        buttons.append(boost_btn)

        if include_inventory:
            inventory_btn = InlineKeyboardButton(
                text=f"{ShopConfig.SEARCH_EMOJI} Чемодан" if inventory_active else "Чемодан",
                callback_data="nothing" if inventory_active else f"category:{Category.INVENTORY.value}"
            )
            buttons.append(inventory_btn)

        return buttons


class MaskShopKeyboard:
    """Keyboard builder for mask shop"""

    @staticmethod
    def build(page: int, active_category: str = Category.MASKS.value) -> InlineKeyboardMarkup:
        """Build mask shop keyboard with pagination"""
        buttons = []

        # Sort masks by price
        sorted_masks = sorted(MASKS, key=lambda x: x.get("price", 0))

        # Calculate pagination
        pagination = ShopKeyboardBuilder.calculate_pagination(
            sorted_masks, page, ShopConfig.MASKS_PER_PAGE
        )

        # Get items for current page
        page_items = sorted_masks[pagination.start_index:pagination.end_index]

        # Create mask buttons
        for mask in page_items:
            mask_id = mask.get("id")
            price = mask.get("price", "N/A")
            emoji = mask.get("emoji", "🚫")
            name = mask.get("name", "Unknown mask")

            if mask_id is not None:
                info_btn = InlineKeyboardButton(
                    text=f"{emoji} {name} {ShopConfig.INFO_EMOJI}",
                    callback_data=f"mask_info:{emoji}:{name}"
                )
                buy_btn = InlineKeyboardButton(
                    text=f"{price} Coins {ShopConfig.COIN_EMOJI}",
                    callback_data=f"buy_mask:{mask_id}"
                )
                buttons.append([info_btn, buy_btn])

        # Add navigation
        navigation_row = ShopKeyboardBuilder.create_navigation_row(
            pagination, active_category
        )
        buttons.append(navigation_row)

        # Add category selection
        category_row = ShopKeyboardBuilder.create_category_row(active_category)
        buttons.append(category_row)

        return InlineKeyboardMarkup(inline_keyboard=buttons)


class BoostShopKeyboard:
    """Keyboard builder for boost shop"""

    @staticmethod
    def _get_boost_emoji(boost_id: str) -> str:
        """Determine emoji based on boost ID"""
        try:
            last_digit = int(boost_id[-1])
            return ShopConfig.LOW_BATTERY_EMOJI if last_digit <= 4 else ShopConfig.BATTERY_EMOJI
        except (ValueError, IndexError):
            return ShopConfig.BATTERY_EMOJI

    @staticmethod
    def _calculate_price(time_seconds: int) -> int:
        """Calculate boost price based on duration"""
        return time_seconds // 1800 * 5  # Every 30 minutes = 5 coins

    @staticmethod
    def build(page: int, active_category: str = Category.BOOSTS.value) -> InlineKeyboardMarkup:
        """Build boost shop keyboard with pagination"""
        buttons = []

        # Sort boosts by time
        sorted_boosts = sorted(BOOSTS, key=lambda x: x.get("time", 0))

        # Calculate pagination
        pagination = ShopKeyboardBuilder.calculate_pagination(
            sorted_boosts, page, ShopConfig.BOOSTS_PER_PAGE
        )

        # Get items for current page
        page_items = sorted_boosts[pagination.start_index:pagination.end_index]

        # Create boost buttons
        for boost in page_items:
            boost_id = boost.get("id")
            name = boost.get("name", "Unknown boost")
            time_minutes = boost.get("time", 0)
            price = BoostShopKeyboard._calculate_price(time_minutes)
            emoji = BoostShopKeyboard._get_boost_emoji(boost_id)

            info_btn = InlineKeyboardButton(
                text=f"{emoji}{name}{ShopConfig.INFO_EMOJI}",
                callback_data=f"boost_info:{emoji}:{name}:{time_minutes}"
            )
            buy_btn = InlineKeyboardButton(
                text=f"{price} Coins {ShopConfig.COIN_EMOJI}",
                callback_data=f"buy_boost:{boost_id}"
            )
            buttons.append([info_btn, buy_btn])

        # Add navigation
        navigation_row = ShopKeyboardBuilder.create_navigation_row(
            pagination, active_category
        )
        buttons.append(navigation_row)

        # Add category selection
        category_row = ShopKeyboardBuilder.create_category_row(active_category)
        buttons.append(category_row)

        return InlineKeyboardMarkup(inline_keyboard=buttons)


class InventoryKeyboard:
    """Keyboard builder for user inventory"""

    @staticmethod
    def build_boost_inventory(
            user_boosts: List[Dict],
            page: int = 1
    ) -> InlineKeyboardMarkup:
        """Build inventory keyboard for user boosts"""
        buttons = []

        # enrich boosts with info from BOOSTS_MAP
        enriched_boosts = []
        for ub in user_boosts:
            boost_id = ub.get("boost_id")
            count = ub.get("count", 0)

            boost_info = BOOSTS_MAP.get(boost_id)
            if not boost_info or count <= 0:
                continue

            enriched_boosts.append({
                "boost_id": boost_id,
                "name": boost_info["name"],
                "time": boost_info["time"],
                "price": boost_info["price"],
                "count": count
            })

        # Sort boosts by time
        sorted_boosts = sorted(enriched_boosts, key=lambda x: x.get("time", 0))

        # Calculate pagination
        pagination = ShopKeyboardBuilder.calculate_pagination(
            sorted_boosts, page, ShopConfig.BOOSTS_PER_PAGE
        )

        # Get items for current page
        page_items = sorted_boosts[pagination.start_index:pagination.end_index]

        # Create boost buttons
        for boost in page_items:
            boost_id = boost["boost_id"]
            name = boost["name"]
            time_seconds = boost["time"]
            count = boost["count"]
            emoji = BoostShopKeyboard._get_boost_emoji(boost_id)

            info_btn = InlineKeyboardButton(
                text=f"{emoji}{name} x{count}{ShopConfig.INFO_EMOJI}",
                callback_data=f"boost_info:{boost_id}:{name}:{time_seconds // 60}"
            )
            use_btn = InlineKeyboardButton(
                text=f"Использовать {ShopConfig.LIGHTNING_EMOJI}",
                callback_data=f"use_boost:{boost_id}"
            )
            buttons.append([info_btn, use_btn])

        # Add navigation if needed
        if pagination.total_pages > 1:
            navigation_row = ShopKeyboardBuilder.create_navigation_row(
                pagination, "Чемодан", "inventory_page"
            )
            buttons.append(navigation_row)

        # Add shop/inventory navigation
        buttons.append([
            InlineKeyboardButton(
                text=f"{ShopConfig.PIN_EMOJI} Маски",
                callback_data="show_masks"
            ),
            InlineKeyboardButton(
                text=f"🏪 Магазин",
                callback_data=f"category:{Category.MASKS.value}"
            )
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def build_mask_inventory(
            items: List[Dict],
            user_id: int
    ) -> InlineKeyboardMarkup:
        """Build inventory section for masks only"""
        buttons = []
        row = []

        for item in items:
            button = InventoryKeyboard._create_mask_button(item, user_id)
            if button:
                row.append(button)
                if len(row) >= ShopConfig.INVENTORY_ITEMS_PER_ROW:
                    buttons.append(row)
                    row = []

        if row:
            buttons.append(row)

        # Add shop/inventory navigation
        buttons.append([
            InlineKeyboardButton(
                text=f"{ShopConfig.PIN_EMOJI} Бусты",
                callback_data="show_boosts"
            ),
            InlineKeyboardButton(
                text=f"🏪 Магазин",
                callback_data=f"category:{Category.MASKS.value}"
            )
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def _create_mask_button(
            item: Dict,
            user_id: int
    ) -> Optional[InlineKeyboardButton]:
        """Create a single mask inventory button"""
        matching = next((m for m in MASKS if m['id'] == item['mask_id']), None)
        if not matching:
            return None

        emoji = matching.get('emoji', '❔')
        count = item.get('count', 1)

        # Mark active mask
        is_active = user_active_mask.get(user_id) == emoji
        prefix = ShopConfig.ACTIVE_MARKER if is_active else ""
        count_text = f"({count})" if count > 1 else ""

        text = f"{prefix}{count_text}{emoji}"
        callback = f"use_mask:{item['mask_id']}"

        return InlineKeyboardButton(text=text, callback_data=callback)

    @staticmethod
    def build_section(
            items: List[Dict],
            section: str,
            is_mask: bool,
            user_id: int
    ) -> InlineKeyboardMarkup:
        """Build inventory section keyboard - now routes to appropriate detailed view"""
        if is_mask:
            return InventoryKeyboard.build_mask_inventory(items, user_id)
        else:
            # Convert items to the format expected by build_boost_inventory
            user_boosts = [{"boost_id": item.get("boost_id"), "count": item.get("count", 1)}
                           for item in items]
            return InventoryKeyboard.build_boost_inventory(user_boosts)


# Main interface functions (backward compatibility)
def mask_kb(page: int, active_category: str = Category.MASKS.value) -> InlineKeyboardMarkup:
    """Build mask shop keyboard (backward compatibility wrapper)"""
    return MaskShopKeyboard.build(page, active_category)


def boosts_kb(page: int, active_category: str = Category.BOOSTS.value) -> InlineKeyboardMarkup:
    """Build boost shop keyboard (backward compatibility wrapper)"""
    return BoostShopKeyboard.build(page, active_category)


def boost_shop_kb(user_boosts: List[Dict], page: int = 1) -> InlineKeyboardMarkup:
    """Build boost inventory keyboard (backward compatibility wrapper)"""
    return InventoryKeyboard.build_boost_inventory(user_boosts, page)


def inventory_section_kb(
        items: List[Dict],
        section: str,
        is_mask: bool,
        user_id: int
) -> InlineKeyboardMarkup:
    """Build inventory section keyboard (backward compatibility wrapper)"""
    return InventoryKeyboard.build_section(items, section, is_mask, user_id)


async def show_category(
        message: Message,
        category: str,
        balance: int,
        full_name: str,
        active_mask: str,
        page: int = 1,
        user_id: int = None,
        user_masks: List[Dict] = None,
        user_boosts: List[Dict] = None
) -> None:
    """Display shop category with appropriate keyboard"""
    keyboard_map = {
        Category.MASKS.value: MaskShopKeyboard.build,
        Category.BOOSTS.value: BoostShopKeyboard.build,
    }

    # Handle inventory category
    if category == Category.INVENTORY.value:
        # Показываем маски в инвентаре

        if user_masks and len(user_masks) > 0:

            keyboard = InventoryKeyboard.build_mask_inventory(user_masks, user_id)
        else:
            # Пустой инвентарь
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=f"{ShopConfig.PIN_EMOJI} Бусты",
                    callback_data="show_boosts"
                ),
                InlineKeyboardButton(
                    text=f"🏪 Магазин",
                    callback_data=f"category:{Category.MASKS.value}"
                )
            ]])

        text = f"""<i><a href="tg://user?id={user_id}">{full_name}</a> открывает свой 🧳Чемодан:
Баланс: {balance} 🪙
Маска: {active_mask}

Выбери стильную маску, чтобы она отображалась рядом с твоим именем в рейтинге. Покажи свой уникальный образ!</i>"""

    else:
        # Shop categories
        builder = keyboard_map.get(category)
        if not builder:
            return

        keyboard = builder(page, category)
        text = (
            f"🏪<i>Магазин</i>: {balance} 🪙\n"
            f"<i>Выберите раздел магазина:<b> Маски | Ускорение | Чемодан </b></i>"
        )

    await message.edit_text(text, reply_markup=keyboard)


def kb_get_balance():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Проверить баланс 🔎", callback_data='get_balance')]
        ]
    )
    return kb
