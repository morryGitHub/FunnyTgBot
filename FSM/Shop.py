from aiogram.fsm.state import StatesGroup, State


class ShopStates(StatesGroup):
    main = State()  # Главный экран магазина
    category = State()  # Просмотр категории
