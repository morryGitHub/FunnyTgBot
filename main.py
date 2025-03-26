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

from random import randint, random, choice
from telebot import types
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CREATOR = int(os.getenv("CREATOR_ID"))
BACKUP = os.getenv("backup_dir")

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(TOKEN)
GAMES = ['🎯', '🏀', '⚽', '🎳', '🎲']
message_ID = None


def select_game():
    return choice(GAMES)


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


def create_table():
    conn, cursor = get_db_connection()
    if conn and cursor:
        conn.commit()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS info (
            user INTEGER,
            chat_id INTEGER,
            name TEXT,
            score INT DEFAULT 0,
            last_used INTEGER DEFAULT NULL,
            dice_control INTEGER DEFAULT NULL,
            PRIMARY KEY (user, chat_id)
        )
        """)
        conn.commit()
        conn.close()


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
    # Создание таблицы в SQLite, если она не существует
    create_table()

    # 1. Извлечение данных из SQLite
    sqlite_conn, sqlite_cursor = get_db_connection()
    if sqlite_conn and sqlite_cursor:
        try:
            sqlite_cursor.execute("SELECT user, chat_id, name, score, last_used, dice_control FROM info")
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
            PRIMARY KEY (user, chat_id)
        );
        """
        mysql_cursor.execute(create_table_query)
        mysql_conn.commit()

        # Вставка данных из SQLite в MySQL
        insert_query = """
        INSERT INTO info (user, chat_id, name, score, last_used, dice_control) 
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            name = VALUES(name),
            score = VALUES(score),
            last_used = VALUES(last_used),
            dice_control = VALUES(dice_control);
        """

        for row in rows:
            # Проверка, чтобы значение chat_id было в допустимом диапазоне
            chat_id = row[1]
            if abs(chat_id) > 9223372036854775807:
                logging.warning(f"Значение chat_id {chat_id} слишком велико и будет пропущено.")
                continue  # Пропустить эту запись

            mysql_cursor.execute(insert_query, row)

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


backup_database_sqlite()


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

    cursor.execute("SELECT name, MAX(score) as max_score FROM info GROUP BY name ORDER BY max_score DESC")
    rows = cursor.fetchall()
    conn.close()

    if rows:
        bot.reply_to(message, f"📝 <b>Топ пользователей: </b>\n\n{show_table(rows)}", parse_mode='HTML')
    else:
        bot.reply_to(message, "🚫 В базе нет пользователей.")


@bot.message_handler(commands=["show_chat_top"])
def show_chat_top(message):
    chat_id = message.chat.id
    conn, cursor = get_db_connection()
    if not conn:
        bot.reply_to(message, "🚫 Ошибка подключения к базе данных.")
        return

    cursor.execute("SELECT name, score FROM info WHERE chat_id = ? ORDER BY score DESC", (chat_id,))
    rows = cursor.fetchall()
    conn.close()

    if rows:
        bot.reply_to(message, f"📝 <b>Топ пользователей:</b>\n\n{show_table(rows)}", parse_mode='HTML')
    else:
        bot.reply_to(message, "🚫 В базе нет пользователей.")


def show_table(table):
    return "\n".join(
        [f"{reward(i + 1)} {i + 1}. <b>{row[0]}</b>: <b>{row[1]} см</b>" for i, row in enumerate(table)])


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
        cursor.execute("UPDATE info SET score = ?, last_used = ? WHERE user = ? AND chat_id = ?",
                       (updated_score, now, user_id, chat_id))
        conn.commit()

        # Миграция данных в MySQL с обновленным score
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

    cursor.execute("SELECT score, dice_control, last_used FROM info WHERE user = ? AND chat_id = ?", (user_id, chat_id))
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

        cursor.execute("UPDATE info SET dice_control = ? WHERE user = ? AND chat_id = ?", (now, user_id, chat_id))
        conn.commit()

        migrate_sqlite_to_mysql_in_background()

        bot.send_message(message.chat.id, "🎲 Игра начинается! Удачи! 🍀")

    else:
        bot.reply_to(message, "🚫 Вы не зарегистрированы в этом чате. Введите /start для регистрации.")

    conn.close()


def process_dice_result(message, sent_dice):
    result = sent_dice.dice.value  # Получаем результат
    user_id = message.from_user.id
    chat_id = message.chat.id
    conn, cursor = get_db_connection()
    if not conn:
        bot.reply_to(message, "🚫 Ошибка подключения к базе данных. Пожалуйста, попробуйте позже.")
        return

    if result == 6:
        # Если выиграл
        bot.reply_to(message, f"🎉 Поздравляю, победа! Ты сокращаешь время ожидания на 3 часа! 🌟")

        cursor.execute("SELECT last_used FROM info WHERE user = ? AND chat_id = ?",
                       (user_id, chat_id))
        result_last_used = cursor.fetchone()

        # Сокращаем время на 3 часа от last_used
        new_last_used = result_last_used[0] - 10800  # Вычитаем 3 часа (10800 секунд)
        if new_last_used < 0:
            new_last_used = 0

        # Обновляем поле last_used в базе данных
        cursor.execute("UPDATE info SET last_used = ? WHERE user = ? AND chat_id = ?",
                       (new_last_used, user_id, chat_id))
        conn.commit()

        return True
    else:
        # Если проиграл
        bot.reply_to(message, "😢 Увы, ты проиграл. Попробуй снова! 🎲")
        return False


bot.polling(non_stop=True)
