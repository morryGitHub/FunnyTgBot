# import os
# import time
# from datetime import datetime
# import shutil
# import logging
# import threading
#
# from random import randint, random
# from dotenv import load_dotenv
#
# # Загружаем переменные окружения
# load_dotenv()
# TOKEN = os.getenv("BOT_TOKEN")
# CREATOR = int(os.getenv("CREATOR_ID"))
# BACKUP = os.getenv(r"backup_dir")
#
# # Настройка логирования
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#
# bot = telebot.TeleBot(TOKEN)
#


# # minigames
#
#

#
# def get_shop_items_page(page: int = 1, items_per_page: int = 5):
#     # Расчёт смещения для SQL-запроса
#     offset = (page - 1) * items_per_page
#
#     conn = sqlite3.connect('dick_bot.db')
#     cursor = conn.cursor()
#     cursor.execute("SELECT mask_id, masks_unicode, price FROM shop LIMIT ? OFFSET ?", (items_per_page, offset))
#     items = cursor.fetchall()
#     conn.close()
#
#     return items
#
#

#
# @bot.callback_query_handler(func=lambda call: call.data.startswith("page:"))
# def handle_page_navigation(call):
#     # Получаем текущую страницу из callback_data
#     page = int(call.data.split(":")[1])
#     show_shop(call.message, page)  # Отображаем магазин с новой страницей
#     bot.answer_callback_query(call.id)  # Отвечаем на запрос, чтобы убрать индикатор загрузки
#
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith("buy_mask:"))
# def handle_buy_mask(call):
#     mask_id = int(call.data.split(":")[1])
#     user_id = call.from_user.id
#     buy_mask(mask_id, user_id, call.message)
#
#
# def buy_mask(mask_id: int, user_id: int, message):
#     conn = sqlite3.connect('dick_bot.db')
#     cursor = conn.cursor()
#
#     # Получаем данные маски из магазина
#     cursor.execute("SELECT masks_unicode, price FROM shop WHERE mask_id = ?", (mask_id,))
#     item = cursor.fetchone()
#
#     if not item:
#         conn.close()
#         bot.send_message(message.chat.id, "❌ Mask not found in the shop.")
#         return
#
#     masks_unicode, price = item
#
#     # Проверяем, есть ли уже такая маска у пользователя
#     cursor.execute("SELECT 1 FROM masks WHERE user = ? AND masks_unicode = ?", (user_id, masks_unicode))
#     already_owned = cursor.fetchone()
#
#     if already_owned:
#         conn.close()
#         bot.send_message(message.chat.id, f"You already own {masks_unicode}.")
#         return
#
#     # Получаем количество монет у пользователя
#     cursor.execute("SELECT coin FROM info WHERE user = ?", (user_id,))
#     user_coins = cursor.fetchone()
#
#     if not user_coins:
#         conn.close()
#         bot.send_message(message.chat.id, "❌ Could not find your coin balance.")
#         return
#
#     user_coins = user_coins[0]
#
#     if user_coins < price:
#         conn.close()
#         bot.send_message(message.chat.id, f"💸 Not enough coins to buy {masks_unicode}. You need {price} coins.")
#         return
#
#     # Совершаем покупку: списываем монеты и добавляем маску
#     cursor.execute("UPDATE info SET coin = coin - ? WHERE user = ?", (price, user_id))
#     cursor.execute("INSERT INTO masks (user, masks_unicode) VALUES (?, ?)", (user_id, masks_unicode))
#     conn.commit()
#     conn.close()
#
#     bot.send_message(message.chat.id, f"✅ You bought {masks_unicode} for {price} coins.")
#
#
# @bot.message_handler(commands=['buy_mask'])
# def shop(message):
#     show_shop(message, page=1)  # По умолчанию показываем первую страницу
#
#
# @bot.message_handler(commands=['show_mask'])
# def my_masks(message):
#     user_id = message.from_user.id
#     chat_id = message.chat.id
#     conn = sqlite3.connect('dick_bot.db')
#     cursor = conn.cursor()
#
#     # Получаем маски пользователя
#     cursor.execute("SELECT DISTINCT masks_unicode FROM masks WHERE user = ?", (user_id,))
#     masks = cursor.fetchall()
#
#     # Получаем монеты и активную маску
#     cursor.execute("SELECT coin, active_mask FROM info WHERE user = ? ", (user_id,))
#     result = cursor.fetchone()  # Используем fetchone(), так как ожидаем одну строку
#
#     conn.close()
#
#     if result:
#         coins = result[0]  # Количество монет
#         active_mask = result[1]  # Активная маска
#     else:
#         coins = 0
#         active_mask = "❓"  # Если нет данных, ставим значение по умолчанию
#
#     if masks:
#         markup = types.InlineKeyboardMarkup(row_width=4)  # Максимум 4 кнопок в строке
#         buttons = [
#             types.InlineKeyboardButton(
#                 text=(mask[0] if mask[0] is not None else "❓") + ("👈" if mask[0] == active_mask else ""),
#                 callback_data=f"select_mask:{mask[0]}"
#             ) for mask in masks
#         ]
#         markup.add(*buttons)  # Добавляем все кнопки в рядок
#
#         # Формируем сообщение с балансом и активной маской
#         response = f"""🧳  <b>Your inventory: </b>
#
# <b>Your balance:</b> {coins}💲
# <b>Active mask:</b> {active_mask}
#
# <i>Select one of your masks to wear:</i>"""
#
#         bot.send_message(message.chat.id, response, reply_markup=markup, parse_mode="HTML")
#     else:
#         response = """😔 <b>No masks found!</b>
#
# 🛒 <i>Go to the shop and buy one!</i> /shop"""
#         bot.send_message(message.chat.id, response, parse_mode="HTML")
#
#
# ################################################
#
#
# def get_boosts_page(page: int = 1, items_per_page: int = 5):
#     offset = (page - 1) * items_per_page
#
#     conn = sqlite3.connect('dick_bot.db')
#     cursor = conn.cursor()
#     cursor.execute("SELECT boost_id, boost_type, price FROM boosts_shop LIMIT ? OFFSET ?", (items_per_page, offset))
#     items = cursor.fetchall()
#     conn.close()
#
#     return items
#
#
# def show_boosts_shop(message, page=1):
#     items = get_boosts_page(page)
#     markup = types.InlineKeyboardMarkup()
#
#     for item in items:
#         boost_id, boost_type, price = item
#         button = types.InlineKeyboardButton(f"{boost_type} - {price} Coins", callback_data=f"buy_boost:{boost_id}")
#         markup.add(button)
#
#     # Навигация по страницам
#     navigation_buttons = []
#
#     if page > 1:
#         navigation_buttons.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"boosts_page:{page - 1}"))
#
#     navigation_buttons.append(types.InlineKeyboardButton(f"Page {page}", callback_data="current_boosts_page"))
#
#     # Проверяем, есть ли бусты на следующей странице
#     next_page_items = get_boosts_page(page + 1)
#     if next_page_items:
#         navigation_buttons.append(types.InlineKeyboardButton("➡️ Next", callback_data=f"boosts_page:{page + 1}"))
#
#     if navigation_buttons:
#         markup.add(*navigation_buttons)
#
#     try:
#         bot.edit_message_text("⚡ Boost Shop! Choose a boost to buy:", chat_id=message.chat.id,
#                               message_id=message.message_id, reply_markup=markup)
#     except Exception as e:
#         print(f"Error editing message: {e}")
#         bot.send_message(message.chat.id, "⚡ Boost Shop! Choose a boost to buy:", reply_markup=markup)
#
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith("boosts_page:"))
# def handle_boosts_page_navigation(call):
#     page = int(call.data.split(":")[1])
#     show_boosts_shop(call.message, page)
#     bot.answer_callback_query(call.id)
#
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith("buy_boost:"))
# def handle_buy_boost(call):
#     boost_id = int(call.data.split(":")[1])
#     user_id = call.from_user.id
#     buy_boost(boost_id, user_id, call.message)
#
#
# def buy_boost(boost_id: int, user_id: int, message):
#     conn = sqlite3.connect('dick_bot.db')
#     cursor = conn.cursor()
#
#     # Получаем данные буста
#     cursor.execute("SELECT boost_type, price FROM boosts_shop WHERE boost_id = ?", (boost_id,))
#     item = cursor.fetchone()
#
#     if not item:
#         conn.close()
#         bot.send_message(message.chat.id, "❌ Boost not found.")
#         return
#
#     boost_type, price = item
#
#     # Получаем монеты пользователя
#     cursor.execute("SELECT coin FROM info WHERE user = ?", (user_id,))
#     user_coins = cursor.fetchone()
#
#     if not user_coins:
#         conn.close()
#         bot.send_message(message.chat.id, "❌ Could not find your coin balance.")
#         return
#
#     user_coins = user_coins[0]
#
#     if user_coins < price:
#         conn.close()
#         bot.send_message(message.chat.id, f"💸 Not enough coins to buy {boost_type}. You need {price} coins.")
#         return
#
#     # Совершаем покупку: списываем монеты и добавляем буст
#     cursor.execute("UPDATE info SET coin = coin - ? WHERE user = ?", (price, user_id))
#     cursor.execute("INSERT INTO boosts (user, boost_type) VALUES (?, ?)", (user_id, boost_type))
#     conn.commit()
#     conn.close()
#
#     bot.send_message(message.chat.id, f"✅ You bought boost: {boost_type} for {price} coins.")
#
#
# @bot.message_handler(commands=['buy_boost'])
# def boosts_command(message):
#     show_boosts_shop(message, page=1)
#
#
# def get_user_boosts(user_id):
#     conn = sqlite3.connect('dick_bot.db')
#     cursor = conn.cursor()
#     cursor.execute("SELECT id, boost_type, purchased_count FROM boosts WHERE user = ?", (user_id,))
#     items = cursor.fetchall()
#     conn.close()
#     return items
#
#
# def show_inventory(message):
#     user_id = message.from_user.id
#     boosts = get_user_boosts(user_id)
#
#     if not boosts:
#         bot.send_message(message.chat.id, "🎒 Your inventory is empty.")
#         return
#
#     markup = types.InlineKeyboardMarkup(row_width=3)
#     buttons = []
#
#     for boost_id, boost_type, used in boosts:
#         if used:
#             continue  # Пропускаем использованные
#         label = f"🧪 {boost_type}"
#         button = types.InlineKeyboardButton(label, callback_data=f"use_boost:{boost_id}")
#         buttons.append(button)
#
#     if not buttons:
#         bot.send_message(message.chat.id, "🎒 All your boosts have been used.")
#         return
#
#     for i in range(0, len(buttons), 3):
#         markup.row(*buttons[i:i + 3])
#
#     bot.send_message(message.chat.id, "🎒 Your Boost Inventory:", reply_markup=markup)
#
#
# active_boosts = {}
#
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith("use_boost:"))
# def handle_use_boost(call):
#     boost_id = int(call.data.split(":")[1])
#     user_id = call.from_user.id
#     chat_id = call.message.chat.id
#
#     conn = sqlite3.connect('dick_bot.db')
#     cursor = conn.cursor()
#
#     # Получаем тип буста и его статус (использован или нет)
#     cursor.execute("SELECT boost_type, purchased_count FROM boosts WHERE id = ? AND user = ?", (boost_id, user_id))
#     row = cursor.fetchone()
#
#     if not row:
#         conn.close()
#         bot.answer_callback_query(call.id, "❌ Boost not found.")
#         return
#
#     boost_type, used = row
#     effect_msg = ""
#
#     # Проверка, использовал ли пользователь буст
#     if used:
#         conn.close()
#         bot.answer_callback_query(call.id, "⛔ You have already used this boost.")
#         return
#
#     # Проверка, активен ли уже какой-либо буст у пользователя
#     if user_id in active_boosts and active_boosts[user_id] is not None:
#         conn.close()
#         bot.answer_callback_query(call.id, "⛔ You already have an active boost. Wait until it is used.")
#         return
#
#     # Применяем эффект в зависимости от типа
#     if boost_type == "3 hours":
#         cursor.execute("UPDATE info SET last_used = last_used - ? WHERE user = ? AND chat_id = ?",
#                        (10800, user_id, chat_id))  # 3 часа
#         effect_msg = "🕒 Cooldown reduced by 3 hours!"
#     elif boost_type == "6 hours":
#         cursor.execute("UPDATE info SET last_used = last_used - ? WHERE user = ? AND chat_id = ?",
#                        (21600, user_id, chat_id))  # 6 часов
#         effect_msg = "🕒 Cooldown reduced by 6 hours!"
#     elif boost_type == "Unlimited":
#         cursor.execute("UPDATE info SET last_used = 0 WHERE user = ? AND chat_id = ?",
#                        (user_id, chat_id))
#         effect_msg = "🕒 Cooldown fully reset! Unlimited access!"
#     else:
#         effect_msg = f"⚡ Unknown boost type: {boost_type}"
#
#     # Устанавливаем активный буст для пользователя
#     active_boosts[user_id] = boost_id
#
#     # Помечаем буст как использованный в базе данных
#     cursor.execute("UPDATE boosts SET purchased_count = 1 WHERE id = ?", (boost_id,))
#
#     # Удаляем использованный буст
#     conn.commit()
#
#     # Убираем активный буст после применения
#     active_boosts[user_id] = None
#
#     conn.close()
#
#     bot.answer_callback_query(call.id)
#     bot.send_message(call.message.chat.id, f"✅ Boost '{boost_type}' activated!\n{effect_msg}")
#
#
# @bot.message_handler(commands=['show_boosts'])
# def inventory_command(message):
#     show_inventory(message)
#
#
# @bot.callback_query_handler(func=lambda call: True)
# def handle_button(call):
#     if call.data.startswith("select_mask:"):
#         # Обработка выбора маски
#         selected_mask = call.data.split(":")[1]  # Извлекаем маску после "select_mask:"
#         user_id = call.from_user.id
#         chat_id = call.message.chat.id  # Получаем chat_id для редактирования сообщения
#
#         # Обновляем активную маску пользователя в базе данных
#         conn = sqlite3.connect('dick_bot.db')
#         cursor = conn.cursor()
#         cursor.execute("UPDATE info SET active_mask = ? WHERE user = ?", (selected_mask, user_id))
#         conn.commit()
#         conn.close()
#
#         # Подтверждение выбора
#         bot.answer_callback_query(call.id, text=f"You selected: {selected_mask}")
#
#         # Получаем список масок для этого пользователя
#         conn = sqlite3.connect('dick_bot.db')
#         cursor = conn.cursor()
#         cursor.execute("SELECT DISTINCT masks_unicode FROM masks WHERE user = ?", (user_id,))
#         masks = cursor.fetchall()
#
#         # Получаем монеты и активную маску
#         cursor.execute("SELECT coin, active_mask FROM info WHERE user = ?", (user_id,))
#         result = cursor.fetchone()  # Используем fetchone(), так как ожидаем одну строку
#         conn.close()
#
#         if result:
#             coins = result[0]  # Количество монет
#             active_mask = result[1]  # Активная маска
#         else:
#             coins = 0
#             active_mask = "❓"  # Если нет данных, ставим значение по умолчанию
#
#         # Создаем клавиатуру с кнопками для выбора масок
#         markup = types.InlineKeyboardMarkup(row_width=4)  # Максимум 4 кнопок в строке
#         buttons = [
#             types.InlineKeyboardButton(
#                 text=(mask[0] if mask[0] is not None else "❓") + ("👈" if mask[0] == selected_mask else ""),
#                 callback_data=f"select_mask:{mask[0]}"
#             ) for mask in masks
#         ]
#         markup.add(*buttons)  # Добавляем все кнопки в рядок
#         # Формируем сообщение с балансом и активной маской
#         response = f"""🧳  <b>Your inventory: </b>
#
#     <b>Your balance:</b> {coins}💲
#     <b>Active mask:</b> {active_mask}
#
#     <i>Select one of your masks to wear:</i>"""
#
#         # Обновляем старое сообщение с новым контентом и клавиатурой
#         bot.edit_message_text(response, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup,
#                               parse_mode="HTML")
#
#
