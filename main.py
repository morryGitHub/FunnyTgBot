import sqlite3
import mysql.connector
from urllib.parse import urlparse
import os
import time
from datetime import datetime
import shutil
import logging
import telebot
import threading

from random import randint, random
from telebot import types
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CREATOR = int(os.getenv("CREATOR_ID"))
BACKUP = os.getenv(r"backup_dir")

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(TOKEN)


def migrate_sqlite_to_mysql_in_background():
    """Асинхронное выполнение миграции"""
    threading.Thread(target=migrate_sqlite_to_mysql).start()


def get_db_connection():
    """Получение соединения с базой данных с повторной попыткой в случае блокировки"""
    attempts = 5
    while attempts > 0:
        try:
            conn = sqlite3.connect('dick_bot.db')
            return conn, conn.cursor()
        except sqlite3.OperationalError as e:
            logging.error(f"Ошибка подключения к БД: {e}")
            time.sleep(1)  # Ожидание 1 секунду перед повторной попыткой
            attempts -= 1
    return None, None


# Функция для подключения к MySQL
def get_mysql_connection():
    mysql_url = 'mysql://root:xKIHWqWQNqdTxgkuDSRHyeDLsFGalCYe@caboose.proxy.rlwy.net:18935/railway'
    parsed_url = urlparse(mysql_url)
    db_config = {
        'host': parsed_url.hostname,
        'port': parsed_url.port,
        'user': parsed_url.username,
        'password': parsed_url.password,
        'database': parsed_url.path[1:]
    }

    try:
        connection = mysql.connector.connect(**db_config)
        return connection, connection.cursor()
    except mysql.connector.Error as err:
        logging.error(f"Ошибка подключения к MySQL: {err}")
        return None, None


# Функция для миграции данных из SQLite в MySQL
def migrate_sqlite_to_mysql():
    # 1. Извлечение данных из SQLite
    sqlite_conn, sqlite_cursor = get_db_connection()
    if sqlite_conn and sqlite_cursor:
        try:
            sqlite_cursor.execute(
                "SELECT user, chat_id, name, score, last_used, dice_control, coin, active_mask FROM info")
            rows = sqlite_cursor.fetchall()
            sqlite_conn.close()
        except sqlite3.OperationalError as e:
            logging.error(f"Ошибка при извлечении данных из SQLite: {e}")
            return

    # 2. Подключение к MySQL и вставка данных
    mysql_conn, mysql_cursor = get_mysql_connection()
    if mysql_conn and mysql_cursor:
        # Создание таблицы в MySQL (если не существует)
        create_table_query = """
        CREATE TABLE IF NOT EXISTS info (
            user BIGINT,
            chat_id BIGINT,
            name TEXT,
            score INT DEFAULT 0,
            last_used INTEGER DEFAULT NULL,
            dice_control INTEGER DEFAULT NULL,
            coin INTEGER DEFAULT 0,
            active_mask TEXT DEFAULT NULL,
            PRIMARY KEY (user, chat_id)
        );
        """
        mysql_cursor.execute(create_table_query)
        mysql_conn.commit()

        # Вставка данных из SQLite в MySQL
        insert_query = """
        INSERT INTO info (user, chat_id, name, score, last_used, dice_control, coin, active_mask) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            user = VALUES(user),
            chat_id = VALUES(chat_id),
            name = VALUES(name),
            score = VALUES(score),
            last_used = VALUES(last_used),
            dice_control = VALUES(dice_control),
            coin = VALUES(coin),
            active_mask = VALUES(active_mask);
        """

        for row in rows:
            # print(f"Row data: {row}")  # Отладка: выводим данные строки перед вставкой

            # Проверка, чтобы значение chat_id было в допустимом диапазоне
            chat_id = row[1]
            if abs(chat_id) > 9223372036854775807:
                logging.warning(f"Значение chat_id {chat_id} слишком велико и будет пропущено.")
                continue  # Пропустить эту запись

            # Убедимся, что в row есть все 8 данных
            if len(row) == 8:
                row_data = row  # Если в row уже все данные, просто используем его
            else:
                # Если в row меньше данных (например, нет active_mask), добавляем None
                row_data = row + (None,)  # Добавляем значение для active_mask

            # Выполнение запроса
            try:
                mysql_cursor.execute(insert_query, row_data)
            except mysql.connector.Error as e:
                logging.error(f"Ошибка при вставке данных: {e}, row_data: {row_data}")
                continue  # Пропустить ошибочную запись

        mysql_conn.commit()
        mysql_cursor.close()
        mysql_conn.close()

        print("Данные успешно вставлены в MySQL на Railway!")
    else:
        print("Ошибка подключения к MySQL.")


def backup_database_sqlite():
    """Создание резервной копии базы данных."""
    original_db_path = 'dick_bot.db'  # Исходный путь к базе данных

    # Папка для резервных копий
    backup_dir = f'{BACKUP}'

    # Создаем директорию для резервных копий, если её нет
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Формируем имя файла резервной копии с меткой времени
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_db_path = os.path.join(backup_dir, f'dick_bot_backup_{timestamp}.db')

    try:
        # Копируем файл базы данных
        shutil.copy(original_db_path, backup_db_path)
        print(f"Резервная копия базы данных сохранена в: {backup_db_path}")
    except Exception as e:
        print(f"Ошибка при создании резервной копии: {e}")


# Получение списка товаров из базы данных

@bot.message_handler(commands=['help'])
def help_command(message):
    commands_text = """
/start - Register in the database
/dick - Increase your size by a random amount
/game - Play a mini-game to reduce cooldown time
/show_global_top - View the global leaderboard by score
/show_chat_top - View the top users in the current chat
/buy_mask - Buy a mask using your coins
/buy_boost - Buy a boost to reduce cooldown or get bonuses
/show_mask - Show your owned masks
/show_boosts - View available boosts and your boost inventory
/help - All commands
    """
    # Экранирование с использованием MarkdownV2
    commands_text_escaped = commands_text.replace("_", "\\_")

    bot.send_message(message.chat.id, commands_text_escaped, parse_mode="MarkdownV2")


@bot.message_handler(commands=['balance'])
def balance_command(message):
    user_id = message.from_user.id

    conn = sqlite3.connect('dick_bot.db')
    cursor = conn.cursor()

    # Получаем баланс монет пользователя
    cursor.execute("SELECT coin FROM info WHERE user = ?", (user_id,))
    result = cursor.fetchone()

    conn.close()

    if result:
        coins = result[0]
        bot.send_message(message.chat.id, f"💰 Ваш баланс: {coins} монет.")
    else:
        bot.send_message(message.chat.id, "❌ Не удалось найти ваш баланс.")


@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_fullname = message.from_user.full_name or message.from_user.username

    # Вызов миграции при запуске

    conn, cursor = get_db_connection()
    if not conn:
        bot.reply_to(message, "🚫 Ошибка подключения к базе данных.")
        return

    # Проверяем, есть ли уже пользователь в базе данных для текущего чата
    cursor.execute("SELECT chat_id FROM info WHERE user = ? AND chat_id = ?", (user_id, chat_id))
    if cursor.fetchone():
        # Если пользователь уже есть в базе в этом чате, просто отправляем приветственное сообщение
        bot.reply_to(message, "👤 Вы уже зарегистрированы в этом чате! " + r'/dick')
    else:
        # Если пользователя нет в базе для этого чата, добавляем его
        cursor.execute("INSERT OR IGNORE INTO info (chat_id, user, name) VALUES (?, ?, ?)",
                       (chat_id, user_id, user_fullname))
        conn.commit()
        bot.reply_to(message, f"🎉 Привет, {user_fullname}!" + r"Вы добавлены в базу данных этого чата. /dick")

    migrate_sqlite_to_mysql_in_background()
    conn.close()


@bot.message_handler(commands=["show_global_top"])
def show_global_top(message):
    conn, cursor = get_db_connection()
    if not conn:
        bot.reply_to(message, "🚫 Ошибка подключения к базе данных.")
        return

    cursor.execute("SELECT name, MAX(score) max_score, USER FROM info GROUP BY name ORDER BY max_score DESC")
    rows = cursor.fetchall()
    conn.close()

    if rows:
        masked_rows = [(mask_name(row[0], row[2]), row[1]) for row in rows]
        bot.reply_to(message, f"📝 <b>🏆 Hall of Fame: </b>\n\n{show_table(masked_rows)}", parse_mode='HTML')
    else:
        bot.reply_to(message, "🚫 В базе нет пользователей.")


@bot.message_handler(commands=["show_chat_top"])
def show_chat_top(message):
    chat_id = message.chat.id
    conn, cursor = get_db_connection()
    if not conn:
        bot.reply_to(message, "🚫 Ошибка подключения к базе данных.")
        return

    cursor.execute("SELECT name, score, USER FROM info WHERE chat_id = ? ORDER BY score DESC", (chat_id,))
    rows = cursor.fetchall()
    conn.close()

    if rows:
        masked_rows = [(mask_name(row[0], row[2]), row[1]) for row in rows]
        bot.reply_to(message, f"📝 <b>Топ пользователей чата:</b>\n\n{show_table(masked_rows)}", parse_mode='HTML')
    else:
        bot.reply_to(message, "🚫 В базе нет пользователей.")


def show_table(table):
    return "\n".join(
        [f"{reward(i + 1)} {i + 1}. <b>{row[0]}</b>: <b>{row[1]} см</b>" for i, row in enumerate(table)]
    )


def mask_name(name, user):
    """Добавляет эмодзи или маску перед ником пользователя."""

    # Получаем активную маску пользователя из базы данных
    conn = sqlite3.connect('dick_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT active_mask FROM info WHERE user = ?", (user,))
    active_mask = cursor.fetchone()
    conn.close()

    # Если маска найдена, добавляем её перед именем
    if active_mask and active_mask[0]:
        return f"{active_mask[0]} {name}"
    else:
        # Если маска не найдена, просто возвращаем имя
        return f"{name}"


@bot.message_handler(commands=['dick', 'penis'])
def grow_penis(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    now = int(time.time())  # текущее время в секундах

    conn, cursor = get_db_connection()
    if not conn:
        bot.reply_to(message, "🚫 Ошибка подключения к базе данных.")
        return

    cursor.execute("SELECT score, last_used FROM info WHERE user = ? AND chat_id = ?", (user_id, chat_id))
    result = cursor.fetchone()
    if result:
        score, last_used = result
        waiting_time = 43200  # 12 hours
        # Если команда уже использовалась, и прошло меньше 12 часов
        if last_used is not None and now - last_used < waiting_time:
            remaining = waiting_time - (now - last_used)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            bot.reply_to(message,
                         f"🚫 Вы уже использовали эту команду в этом чате. Попробуйте снова через {hours}ч {minutes}м.")
            conn.close()
            return

        # Если прошло достаточно времени или команда вызывается впервые
        grow = custom_randint()  # -5, 10
        updated_score = score + grow
        cursor.execute("SELECT coin FROM info WHERE user = ? ", (user_id,))
        result_coin = cursor.fetchone()
        if result_coin:
            coin = result_coin[0]  # Извлекаем монеты из кортежа
        coin += randint(1, 5)

        cursor.execute("UPDATE info SET score = ?, last_used = ? WHERE user = ? AND chat_id = ? ",
                       (updated_score, now, user_id, chat_id))

        cursor.execute("UPDATE info SET coin = ? WHERE user = ? ",
                       (coin, user_id))

        conn.commit()

        # Миграция данных в MySQL с обновленным score
        backup_database_sqlite()
        migrate_sqlite_to_mysql_in_background()

        bot.reply_to(message,
                     f"🌱 Ваш член в этом чате вырос на <b>{grow}</b> см.\n📏 Теперь размер: <b>{updated_score}</b> см.",
                     parse_mode='HTML')
    else:
        bot.reply_to(message, "🚫 Вы не зарегистрированы в этом чате. Введите /start.")

    conn.close()


def custom_randint():
    while True:
        grow = randint(-5, 10)
        if grow >= 0 or random() < 0.5:  # 50% шанс пропустить отрицательное число
            return grow


@bot.message_handler(commands=['clear_table'])
def clear_database(message):
    if message.from_user.id == CREATOR:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Да", callback_data="clear_yes"))
        markup.add(types.InlineKeyboardButton("Нет", callback_data="clear_no"))
        bot.reply_to(message, "Вы уверены, что хотите удалить все данные?", reply_markup=markup)
    else:
        bot.reply_to(message, "🚫 Только создатель бота может выполнить это действие.")


@bot.callback_query_handler(func=lambda call: call.data in ["clear_yes", "clear_no"])
def handle_confirmation(call):
    if call.data == "clear_yes":
        conn, cursor = get_db_connection()
        if conn:
            cursor.execute("DELETE FROM info")
            conn.commit()
            conn.close()
            bot.send_message(call.message.chat.id, "✅ Все данные удалены.")
        else:
            bot.send_message(call.message.chat.id, "🚫 Ошибка подключения к базе данных.")
    else:
        bot.send_message(call.message.chat.id, "❌ Удаление отменено.")

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)


@bot.message_handler(commands=["clear_mysql_data"])
def clear_mysql_data(message):
    if message.from_user.id == CREATOR:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Да", callback_data="clear_mysql_yes"))
        markup.add(types.InlineKeyboardButton("Нет", callback_data="clear_mysql_no"))
        bot.reply_to(message, "Вы уверены, что хотите удалить все данные из MySQL?", reply_markup=markup)
    else:
        bot.reply_to(message, "🚫 Только создатель бота может выполнить это действие.")


@bot.callback_query_handler(func=lambda call: call.data in ["clear_mysql_yes", "clear_mysql_no"])
def handle_mysql_clear_confirmation(call):
    if call.data == "clear_mysql_yes":
        mysql_conn, mysql_cursor = get_mysql_connection()
        if mysql_conn and mysql_cursor:
            try:
                # Удаление всех данных из таблицы info в MySQL
                mysql_cursor.execute("DELETE FROM info")
                mysql_conn.commit()
                mysql_cursor.close()
                mysql_conn.close()
                bot.send_message(call.message.chat.id, "✅ Все данные из MySQL удалены.")
            except mysql.connector.Error as err:
                logging.error(f"Ошибка при удалении данных из MySQL: {err}")
                bot.send_message(call.message.chat.id, "🚫 Ошибка при удалении данных.")
        else:
            bot.send_message(call.message.chat.id, "🚫 Ошибка подключения к MySQL.")
    else:
        bot.send_message(call.message.chat.id, "❌ Удаление отменено.")

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)


def reward(place):
    return ["🥇", "🥈", "🥉", "🎗"][min(place - 1, 3)]


# minigames


@bot.message_handler(commands=["game"])
def handle_dice(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    now = int(time.time())  # текущее время в секундах

    conn, cursor = get_db_connection()
    if not conn:
        bot.reply_to(message, "🚫 Ошибка подключения к базе данных. Пожалуйста, попробуйте позже.")
        return

    cursor.execute("SELECT score, dice_control, last_used FROM info WHERE user = ? AND chat_id = ?",
                   (user_id, chat_id))

    result = cursor.fetchone()

    if result:
        score, dice_control, last_used = result
        waiting_time = 10800  # 3 часа

        if last_used is None or last_used == 0:
            bot.send_message(message.chat.id, "Чтобы сократить время, нужно чтобы оно было у вас. Введите /dick")
            return

        if dice_control is not None and now - dice_control < waiting_time:
            remaining = waiting_time - (now - dice_control)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            bot.reply_to(message,
                         f"🚫 Вы уже использовали эту команду недавно. Попробуйте снова через {hours}ч {minutes}м.")
            conn.close()
            return

        try:
            sent_dice = bot.send_dice(message.chat.id, emoji='🎲')
            threading.Timer(5, process_dice_result, args=(message, sent_dice)).start()
        except Exception as e:
            logging.error(f"Ошибка при отправке кубика: {e}")
            bot.reply_to(message, "🚫 Ошибка при отправке кубика.")

        cursor.execute("UPDATE info SET dice_control = ? WHERE user = ? ", (now, user_id,))

        conn.commit()

        migrate_sqlite_to_mysql_in_background()

        bot.send_message(message.chat.id, "🎲 Игра начинается! Удачи! 🍀")

    else:
        bot.reply_to(message, "🚫 Вы не зарегистрированы в этом чате. Введите /start для регистрации.")

    conn.close()


def process_dice_result(message, sent_dice):
    result = sent_dice.dice.value
    user_id = message.from_user.id
    chat_id = message.chat.id
    conn, cursor = get_db_connection()
    if not conn:
        bot.reply_to(message, "🚫 Ошибка подключения к базе данных. Пожалуйста, попробуйте позже.")
        return

    if result in [4, 5, 6]:
        time_hour = result - 6 + 3
        # Если выиграл
        bot.reply_to(message, f"🎉 Поздравляю, победа! Ты сокращаешь время ожидания на {time_hour} час(а)! 🌟")

        cursor.execute("SELECT last_used FROM info WHERE user = ? and chat_id = ? ",
                       (user_id, chat_id))

        result_last_used = cursor.fetchone()

        cursor.execute("SELECT coin FROM info WHERE user = ? ",
                       (user_id,))
        result_coin = cursor.fetchone()

        coin = result_coin[0]
        coin += time_hour

        # Сокращаем время на 3 часа от last_used
        new_last_used = result_last_used[0] - 3600 * time_hour
        if new_last_used < 0:
            new_last_used = 0

        # Обновляем поле last_used в базе данных
        cursor.execute("UPDATE info SET last_used = ? WHERE user = ? AND chat_id = ?",
                       (new_last_used, user_id, chat_id))

        cursor.execute("UPDATE info SET coin = ? WHERE user = ? ",
                       (coin, user_id))
        conn.commit()

        return True
    else:
        # Если проиграл
        bot.reply_to(message, "😢 Увы, ты проиграл. Попробуй снова! 🎲")
        return False


def get_shop_items_page(page: int = 1, items_per_page: int = 5):
    # Расчёт смещения для SQL-запроса
    offset = (page - 1) * items_per_page

    conn = sqlite3.connect('dick_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT mask_id, masks_unicode, price FROM shop LIMIT ? OFFSET ?", (items_per_page, offset))
    items = cursor.fetchall()
    conn.close()

    return items


def show_shop(message, page=1):
    items = get_shop_items_page(page)
    markup = types.InlineKeyboardMarkup()

    for item in items:
        mask_id, masks_unicode, price = item
        button = types.InlineKeyboardButton(f"{masks_unicode} - {price} Coins", callback_data=f"buy_mask:{mask_id}")
        markup.add(button)

    # Добавление кнопок для навигации
    navigation_buttons = []

    if page > 1:  # Если это не первая страница, добавляем кнопку "Назад"
        navigation_buttons.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"page:{page - 1}"))

    navigation_buttons.append(types.InlineKeyboardButton(f"Page {page}", callback_data="current_page"))
    # Проверяем, есть ли товары на следующей странице
    next_page_items = get_shop_items_page(page + 1)
    if next_page_items:  # Если на следующей странице есть товары, добавляем кнопку "Next"
        navigation_buttons.append(types.InlineKeyboardButton("➡️ Next", callback_data=f"page:{page + 1}"))

    markup.add(*navigation_buttons)

    try:
        # Попробуем отредактировать старое сообщение с новым контентом и клавиатурой
        bot.edit_message_text("Welcome to the Shop! Choose a mask to buy:", chat_id=message.chat.id,
                              message_id=message.message_id, reply_markup=markup)
    except Exception as e:
        # Если редактирование не удалось, отправим новое сообщение
        print(f"Error editing message: {e}")
        bot.send_message(message.chat.id, "Welcome to the Shop! Choose a mask to buy:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("page:"))
def handle_page_navigation(call):
    # Получаем текущую страницу из callback_data
    page = int(call.data.split(":")[1])
    show_shop(call.message, page)  # Отображаем магазин с новой страницей
    bot.answer_callback_query(call.id)  # Отвечаем на запрос, чтобы убрать индикатор загрузки


@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_mask:"))
def handle_buy_mask(call):
    mask_id = int(call.data.split(":")[1])
    user_id = call.from_user.id
    buy_mask(mask_id, user_id, call.message)


def buy_mask(mask_id: int, user_id: int, message):
    conn = sqlite3.connect('dick_bot.db')
    cursor = conn.cursor()

    # Получаем данные маски из магазина
    cursor.execute("SELECT masks_unicode, price FROM shop WHERE mask_id = ?", (mask_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        bot.send_message(message.chat.id, "❌ Mask not found in the shop.")
        return

    masks_unicode, price = item

    # Проверяем, есть ли уже такая маска у пользователя
    cursor.execute("SELECT 1 FROM masks WHERE user = ? AND masks_unicode = ?", (user_id, masks_unicode))
    already_owned = cursor.fetchone()

    if already_owned:
        conn.close()
        bot.send_message(message.chat.id, f"You already own {masks_unicode}.")
        return

    # Получаем количество монет у пользователя
    cursor.execute("SELECT coin FROM info WHERE user = ?", (user_id,))
    user_coins = cursor.fetchone()

    if not user_coins:
        conn.close()
        bot.send_message(message.chat.id, "❌ Could not find your coin balance.")
        return

    user_coins = user_coins[0]

    if user_coins < price:
        conn.close()
        bot.send_message(message.chat.id, f"💸 Not enough coins to buy {masks_unicode}. You need {price} coins.")
        return

    # Совершаем покупку: списываем монеты и добавляем маску
    cursor.execute("UPDATE info SET coin = coin - ? WHERE user = ?", (price, user_id))
    cursor.execute("INSERT INTO masks (user, masks_unicode) VALUES (?, ?)", (user_id, masks_unicode))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, f"✅ You bought {masks_unicode} for {price} coins.")


@bot.message_handler(commands=['buy_mask'])
def shop(message):
    show_shop(message, page=1)  # По умолчанию показываем первую страницу


@bot.message_handler(commands=['show_mask'])
def my_masks(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    conn = sqlite3.connect('dick_bot.db')
    cursor = conn.cursor()

    # Получаем маски пользователя
    cursor.execute("SELECT DISTINCT masks_unicode FROM masks WHERE user = ?", (user_id,))
    masks = cursor.fetchall()

    # Получаем монеты и активную маску
    cursor.execute("SELECT coin, active_mask FROM info WHERE user = ? ", (user_id,))
    result = cursor.fetchone()  # Используем fetchone(), так как ожидаем одну строку

    conn.close()

    if result:
        coins = result[0]  # Количество монет
        active_mask = result[1]  # Активная маска
    else:
        coins = 0
        active_mask = "❓"  # Если нет данных, ставим значение по умолчанию

    if masks:
        markup = types.InlineKeyboardMarkup(row_width=4)  # Максимум 4 кнопок в строке
        buttons = [
            types.InlineKeyboardButton(
                text=(mask[0] if mask[0] is not None else "❓") + ("👈" if mask[0] == active_mask else ""),
                callback_data=f"select_mask:{mask[0]}"
            ) for mask in masks
        ]
        markup.add(*buttons)  # Добавляем все кнопки в рядок

        # Формируем сообщение с балансом и активной маской
        response = f"""🧳  <b>Your inventory: </b>

<b>Your balance:</b> {coins}💲
<b>Active mask:</b> {active_mask}

<i>Select one of your masks to wear:</i>"""

        bot.send_message(message.chat.id, response, reply_markup=markup, parse_mode="HTML")
    else:
        response = """😔 <b>No masks found!</b>

🛒 <i>Go to the shop and buy one!</i> /shop"""
        bot.send_message(message.chat.id, response, parse_mode="HTML")


################################################


def get_boosts_page(page: int = 1, items_per_page: int = 5):
    offset = (page - 1) * items_per_page

    conn = sqlite3.connect('dick_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT boost_id, boost_type, price FROM boosts_shop LIMIT ? OFFSET ?", (items_per_page, offset))
    items = cursor.fetchall()
    conn.close()

    return items


def show_boosts_shop(message, page=1):
    items = get_boosts_page(page)
    markup = types.InlineKeyboardMarkup()

    for item in items:
        boost_id, boost_type, price = item
        button = types.InlineKeyboardButton(f"{boost_type} - {price} Coins", callback_data=f"buy_boost:{boost_id}")
        markup.add(button)

    # Навигация по страницам
    navigation_buttons = []

    if page > 1:
        navigation_buttons.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"boosts_page:{page - 1}"))

    navigation_buttons.append(types.InlineKeyboardButton(f"Page {page}", callback_data="current_boosts_page"))

    # Проверяем, есть ли бусты на следующей странице
    next_page_items = get_boosts_page(page + 1)
    if next_page_items:
        navigation_buttons.append(types.InlineKeyboardButton("➡️ Next", callback_data=f"boosts_page:{page + 1}"))

    if navigation_buttons:
        markup.add(*navigation_buttons)

    try:
        bot.edit_message_text("⚡ Boost Shop! Choose a boost to buy:", chat_id=message.chat.id,
                              message_id=message.message_id, reply_markup=markup)
    except Exception as e:
        print(f"Error editing message: {e}")
        bot.send_message(message.chat.id, "⚡ Boost Shop! Choose a boost to buy:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("boosts_page:"))
def handle_boosts_page_navigation(call):
    page = int(call.data.split(":")[1])
    show_boosts_shop(call.message, page)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_boost:"))
def handle_buy_boost(call):
    boost_id = int(call.data.split(":")[1])
    user_id = call.from_user.id
    buy_boost(boost_id, user_id, call.message)


def buy_boost(boost_id: int, user_id: int, message):
    conn = sqlite3.connect('dick_bot.db')
    cursor = conn.cursor()

    # Получаем данные буста
    cursor.execute("SELECT boost_type, price FROM boosts_shop WHERE boost_id = ?", (boost_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        bot.send_message(message.chat.id, "❌ Boost not found.")
        return

    boost_type, price = item

    # Получаем монеты пользователя
    cursor.execute("SELECT coin FROM info WHERE user = ?", (user_id,))
    user_coins = cursor.fetchone()

    if not user_coins:
        conn.close()
        bot.send_message(message.chat.id, "❌ Could not find your coin balance.")
        return

    user_coins = user_coins[0]

    if user_coins < price:
        conn.close()
        bot.send_message(message.chat.id, f"💸 Not enough coins to buy {boost_type}. You need {price} coins.")
        return

    # Совершаем покупку: списываем монеты и добавляем буст
    cursor.execute("UPDATE info SET coin = coin - ? WHERE user = ?", (price, user_id))
    cursor.execute("INSERT INTO boosts (user, boost_type) VALUES (?, ?)", (user_id, boost_type))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, f"✅ You bought boost: {boost_type} for {price} coins.")


@bot.message_handler(commands=['buy_boost'])
def boosts_command(message):
    show_boosts_shop(message, page=1)


def get_user_boosts(user_id):
    conn = sqlite3.connect('dick_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, boost_type, purchased_count FROM boosts WHERE user = ?", (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items


def show_inventory(message):
    user_id = message.from_user.id
    boosts = get_user_boosts(user_id)

    if not boosts:
        bot.send_message(message.chat.id, "🎒 Your inventory is empty.")
        return

    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []

    for boost_id, boost_type, used in boosts:
        if used:
            continue  # Пропускаем использованные
        label = f"🧪 {boost_type}"
        button = types.InlineKeyboardButton(label, callback_data=f"use_boost:{boost_id}")
        buttons.append(button)

    if not buttons:
        bot.send_message(message.chat.id, "🎒 All your boosts have been used.")
        return

    for i in range(0, len(buttons), 3):
        markup.row(*buttons[i:i + 3])

    bot.send_message(message.chat.id, "🎒 Your Boost Inventory:", reply_markup=markup)


active_boosts = {}


@bot.callback_query_handler(func=lambda call: call.data.startswith("use_boost:"))
def handle_use_boost(call):
    boost_id = int(call.data.split(":")[1])
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    conn = sqlite3.connect('dick_bot.db')
    cursor = conn.cursor()

    # Получаем тип буста и его статус (использован или нет)
    cursor.execute("SELECT boost_type, purchased_count FROM boosts WHERE id = ? AND user = ?", (boost_id, user_id))
    row = cursor.fetchone()

    if not row:
        conn.close()
        bot.answer_callback_query(call.id, "❌ Boost not found.")
        return

    boost_type, used = row
    effect_msg = ""

    # Проверка, использовал ли пользователь буст
    if used:
        conn.close()
        bot.answer_callback_query(call.id, "⛔ You have already used this boost.")
        return

    # Проверка, активен ли уже какой-либо буст у пользователя
    if user_id in active_boosts and active_boosts[user_id] is not None:
        conn.close()
        bot.answer_callback_query(call.id, "⛔ You already have an active boost. Wait until it is used.")
        return

    # Применяем эффект в зависимости от типа
    if boost_type == "3 hours":
        cursor.execute("UPDATE info SET last_used = last_used - ? WHERE user = ? AND chat_id = ?",
                       (10800, user_id, chat_id))  # 3 часа
        effect_msg = "🕒 Cooldown reduced by 3 hours!"
    elif boost_type == "6 hours":
        cursor.execute("UPDATE info SET last_used = last_used - ? WHERE user = ? AND chat_id = ?",
                       (21600, user_id, chat_id))  # 6 часов
        effect_msg = "🕒 Cooldown reduced by 6 hours!"
    elif boost_type == "Unlimited":
        cursor.execute("UPDATE info SET last_used = 0 WHERE user = ? AND chat_id = ?",
                       (user_id, chat_id))
        effect_msg = "🕒 Cooldown fully reset! Unlimited access!"
    else:
        effect_msg = f"⚡ Unknown boost type: {boost_type}"

    # Устанавливаем активный буст для пользователя
    active_boosts[user_id] = boost_id

    # Помечаем буст как использованный в базе данных
    cursor.execute("UPDATE boosts SET purchased_count = 1 WHERE id = ?", (boost_id,))

    # Удаляем использованный буст
    conn.commit()

    # Убираем активный буст после применения
    active_boosts[user_id] = None

    conn.close()

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"✅ Boost '{boost_type}' activated!\n{effect_msg}")


@bot.message_handler(commands=['show_boosts'])
def inventory_command(message):
    show_inventory(message)


@bot.callback_query_handler(func=lambda call: True)
def handle_button(call):
    if call.data.startswith("select_mask:"):
        # Обработка выбора маски
        selected_mask = call.data.split(":")[1]  # Извлекаем маску после "select_mask:"
        user_id = call.from_user.id
        chat_id = call.message.chat.id  # Получаем chat_id для редактирования сообщения

        # Обновляем активную маску пользователя в базе данных
        conn = sqlite3.connect('dick_bot.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE info SET active_mask = ? WHERE user = ?", (selected_mask, user_id))
        conn.commit()
        conn.close()

        # Подтверждение выбора
        bot.answer_callback_query(call.id, text=f"You selected: {selected_mask}")

        # Получаем список масок для этого пользователя
        conn = sqlite3.connect('dick_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT masks_unicode FROM masks WHERE user = ?", (user_id,))
        masks = cursor.fetchall()

        # Получаем монеты и активную маску
        cursor.execute("SELECT coin, active_mask FROM info WHERE user = ?", (user_id,))
        result = cursor.fetchone()  # Используем fetchone(), так как ожидаем одну строку
        conn.close()

        if result:
            coins = result[0]  # Количество монет
            active_mask = result[1]  # Активная маска
        else:
            coins = 0
            active_mask = "❓"  # Если нет данных, ставим значение по умолчанию

        # Создаем клавиатуру с кнопками для выбора масок
        markup = types.InlineKeyboardMarkup(row_width=4)  # Максимум 4 кнопок в строке
        buttons = [
            types.InlineKeyboardButton(
                text=(mask[0] if mask[0] is not None else "❓") + ("👈" if mask[0] == selected_mask else ""),
                callback_data=f"select_mask:{mask[0]}"
            ) for mask in masks
        ]
        markup.add(*buttons)  # Добавляем все кнопки в рядок
        # Формируем сообщение с балансом и активной маской
        response = f"""🧳  <b>Your inventory: </b>

    <b>Your balance:</b> {coins}💲
    <b>Active mask:</b> {active_mask}

    <i>Select one of your masks to wear:</i>"""

        # Обновляем старое сообщение с новым контентом и клавиатурой
        bot.edit_message_text(response, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup,
                              parse_mode="HTML")


bot.polling(non_stop=True)
