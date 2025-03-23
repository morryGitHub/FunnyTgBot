import os
import shutil
import sqlite3
import time
from datetime import datetime

import telebot
import logging

from random import randint
from telebot import types
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CREATOR = int(os.getenv("CREATOR_ID"))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(TOKEN)


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
        # cursor.execute("""
        #     UPDATE info
        #     SET score = -1000
        #     WHERE user = 782585931
        #
        # """)
        conn.commit()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS info (
            user INTEGER,
            chat_id INTEGER,
            name TEXT,
            score INT DEFAULT 0,
            last_used INTEGER DEFAULT NULL,
            PRIMARY KEY (user, chat_id)
        )
        """)
        conn.commit()
        conn.close()


create_table()


def backup_database_sqlite():
    """Создание резервной копии базы данных."""
    original_db_path = 'dick_bot.db'  # Исходный путь к базе данных

    # Папка для резервных копий
    backup_dir = fr'{backup_dir}'

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

    conn, cursor = get_db_connection()
    if not conn:
        bot.reply_to(message, "🚫 Ошибка подключения к базе данных.")
        return

    # Проверяем, есть ли уже пользователь в базе данных для текущего чата
    cursor.execute("SELECT chat_id FROM info WHERE user = ? AND chat_id = ?", (user_id, chat_id))
    if cursor.fetchone():
        # Если пользователь уже есть в базе в этом чате, просто отправляем приветственное сообщение
        bot.reply_to(message, "👤 Вы уже зарегистрированы в этом чате!" + r'\dick')
    else:
        # Если пользователя нет в базе для этого чата, добавляем его
        cursor.execute("INSERT INTO info (chat_id, user, name) VALUES (?, ?, ?)", (chat_id, user_id, user_fullname))
        conn.commit()
        bot.reply_to(message, f"🎉 Привет, {user_fullname}!" + r"Вы добавлены в базу данных этого чата. \dick")

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
    # [f"{reward(i + 1)} {i + 1}. <b>{row[0]}</b> {"🠙" if row[1] > 0 else "🠛"} <b>{row[1]} см</b>" for i, row in enumerate(table)])


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
        # Если команда уже использовалась, и прошло меньше 24 часов
        if last_used is not None and now - last_used < waiting_time:
            remaining = waiting_time - (now - last_used)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            bot.reply_to(message,
                         f"🚫 Вы уже использовали эту команду в этом чате. Попробуйте снова через {hours}ч {minutes}м.")
            conn.close()
            return

        # Если прошло достаточно времени или команда вызывается впервые
        grow = randint(-5, 10)
        updated_score = score + grow
        cursor.execute("UPDATE info SET score = ?, last_used = ? WHERE user = ? AND chat_id = ?",
                       (updated_score, now, user_id, chat_id))
        conn.commit()
        bot.reply_to(message,
                     f"🌱 Ваш член в этом чате вырос на <b>{grow}</b> см.\n📏 Теперь размер: <b>{updated_score}</b> см.",
                     parse_mode='HTML')
    else:
        bot.reply_to(message, "🚫 Вы не зарегистрированы в этом чате. Введите /start.")
    conn.close()


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


def reward(place):
    return ["🥇", "🥈", "🥉", "🎗"][min(place - 1, 3)]


bot.polling(none_stop=True)
