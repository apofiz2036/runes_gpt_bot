import sqlite3
from pathlib import Path
import csv
import os
import logging
from dotenv import load_dotenv
from datetime import datetime
from utils.logging import setup_logging, send_error_to_admin

# Инициализация логгера
logger = logging.getLogger(__name__)
setup_logging()

load_dotenv()
ADMIN_ID = os.getenv("ADMIN_ID")
SQLITE_DB = "data/runes_bot.db"

def init_db():
    """
    Создайт базу данных с двумя таблицами
    - subscribers: хранит информацию о пользователях (user_id, first_seen, limits).
    - divinations: хранит историю гаданий (user_id, date, divination_type)
    """
    try:
        # Создаём папку если её ещё нет
        migrate_db() # ПОТОМ УДАЛИТЬ!!!!!!!!!!!!!!!!!!!
        Path ("data").mkdir(exist_ok=True)

        # Подключаемся к базе данных
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        # Создаём таблицу subscribers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                user_name TEXT,
                first_seen TEXT NOT NULL,
                limits INTEGER DEFAULT 50
            )
        """)

        # Создаём таблицу divinations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS divinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                divination_type TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES subscribers (user_id)
            )
        """)

        # Сохраняем таблицу
        conn.commit()
        conn.close()
    except Exception as e:
        error_message = "Ошибка при создании базы данных"
        logger.error(error_message)


def migrate_db(): # ПОТОМ УДАЛИТЬ!!!!!!!!!!!!!!!!!!!!!!!!
    """Добавляет user_name в существующую таблицу subscribers, если его нет."""
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()
        
        # Проверяем, есть ли столбец user_name
        cursor.execute("PRAGMA table_info(subscribers)")
        columns = [column[1] for column in cursor.fetchall()]  # Список всех столбцов
        
        if "user_name" not in columns:
            # Добавляем столбец, если его нет
            cursor.execute("ALTER TABLE subscribers ADD COLUMN user_name TEXT")
            conn.commit()
            logger.info("Добавлен столбец user_name в таблицу subscribers")
            
        conn.close()
    except Exception as e:
        error_message = f"Ошибка миграции: {e}"
        logger.error(error_message)
        send_error_to_admin(error_message)
        

def save_subscriber(user_id: int, user_name: str = None):
    """Сохраняет подписчика в SQLite (или пропускает, если он уже есть)."""
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        # Проверяем существование пользователя
        cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
        exist = cursor.fetchone()

        if not exist:
            # Добавляем нового пользователя
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO subscribers (user_id, first_seen, user_name) VALUES (?, ?, ?)",
                (user_id, timestamp, user_name)
            )
            conn.commit()
        conn.close()
    except Exception as e:
        error_message = f"Ошибка в save_subscriber: {e}"
        logger.error(error_message)
        send_error_to_admin(error_message)


def get_subscribers():
    """Получает уникальные ID из SQLite, за исключением админа"""
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        # Запрос для получения всех user_id, кроме админа
        cursor.execute("""
            SELECT user_id FROM subscribers
            WHERE user_id != ?               
        """, (int(ADMIN_ID),))

        # Собираем уникальные ID в список
        subscribers = [row[0] for row in cursor.fetchall()]
        conn.close()

        return subscribers        
    except Exception as e:
        error_message = f"Ошибка в get_subscribers: {e}"
        logger.error(error_message)
        return []


def save_divination(user_id: int, divination_type: str):
    """Сохраняет информацию о гадании в базу данных."""
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        # Проверяем существование пользователя
        cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            save_subscriber(user_id)
        
        # Добавляем запись о гадании
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO divinations (user_id, date, divination_type) VALUES (?, ?, ?)",
            (user_id, timestamp, divination_type)
        )

        conn.commit()
    except Exception as e:
        error_message = f"Ошибка при сохранении гадания: {e}"
        logger.error(error_message)
        send_error_to_admin(error_message)
    finally:
        conn.close()


def update_user_name(user_id: int, new_name: str) -> None:
    """Обновляет имя пользователя, если оно изменилось или было NULL."""
    try:
        if not new_name:  # Если имя пустое, пропускаем
            return
            
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()
        
        # Проверяем текущее имя
        cursor.execute("SELECT user_name FROM subscribers WHERE user_id = ?", (user_id,))
        current_name = cursor.fetchone()
        
        # Если имени нет (NULL) или оно отличается — обновляем
        if current_name is None or current_name[0] != new_name:
            cursor.execute(
                "UPDATE subscribers SET user_name = ? WHERE user_id = ?",
                (new_name, user_id)
            )
            logger.info(f"Обновлено имя для user_id={user_id}: {new_name}")
        
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка в update_user_name: {e}")
    finally:
        conn.close()

        