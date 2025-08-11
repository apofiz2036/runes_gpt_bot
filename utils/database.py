import sqlite3
from pathlib import Path
import csv
import secrets
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
        migrate_db() 
        Path ("data").mkdir(exist_ok=True)

        # Подключаемся к базе данных
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        # Создаём таблицу subscribers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
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


def migrate_db(): 
    """Добавляет столбец public_id в таблицу subscribers, если его нет."""
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()
        
        # Проверяем существование столбца
        cursor.execute("PRAGMA table_info(subscribers)")
        columns = [column[1] for column in cursor.fetchall()]

        if "public_id" not in columns:
            # 1. Добавляем столбец БЕЗ UNIQUE сначала
            cursor.execute("ALTER TABLE subscribers ADD COLUMN public_id TEXT")
            conn.commit()
            logger.info("Добавлен столбец public_id (без UNIQUE)")

            # 2. Генерируем public_id для существующих пользователей
            cursor.execute("SELECT user_id FROM subscribers WHERE public_id IS NULL")
            users = cursor.fetchall()
            
            for (user_id,) in users:
                public_id = f"RUNES-{secrets.token_hex(3).upper()}"  # Например, RUNES-A1B2C3
                cursor.execute(
                    "UPDATE subscribers SET public_id = ? WHERE user_id = ?",
                    (public_id, user_id)
                )
            
            conn.commit()
            logger.info(f"Сгенерированы public_id для {len(users)} пользователей")

            # 3. Добавляем ограничение UNIQUE через новую таблицу
            cursor.execute("""
                CREATE TABLE subscribers_new (
                    user_id INTEGER PRIMARY KEY,
                    first_seen TEXT NOT NULL,
                    limits INTEGER DEFAULT 50,
                    public_id TEXT UNIQUE
                )
            """)
            
            # Копируем данные из старой таблицы в новую
            cursor.execute("""
                INSERT INTO subscribers_new 
                SELECT user_id, first_seen, limits, public_id 
                FROM subscribers
            """)
            
            # Удаляем старую таблицу и переименовываем новую
            cursor.execute("DROP TABLE subscribers")
            cursor.execute("ALTER TABLE subscribers_new RENAME TO subscribers")
            conn.commit()
            logger.info("Добавлено ограничение UNIQUE для public_id")
        
    except Exception as e:
        error_message = f"Ошибка в migrate_db: {e}"
        logger.error(error_message)
        send_error_to_admin(error_message)
    finally:
        conn.close()
        

def save_subscriber(user_id: int):
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
            public_id = f"RUNES-{secrets.token_hex(3).upper()}"
            cursor.execute(
                "INSERT INTO subscribers (user_id, first_seen, public_id) VALUES (?, ?, ?)",
                (user_id, timestamp, public_id)
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


def top_up_limits(public_id: str, amount: int) -> tuple[bool, int]:
    """
    Пополняет лимиты пользователя по public_id.
    Возвращает (success, user_id), где:
    - success: True если операция успешна
    - user_id: ID пользователя или None если не найден
    """
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        # Получаем user_id перед обновлением
        cursor.execute(
            "SELECT user_id FROM subscribers WHERE LOWER(public_id) = LOWER(?)",
            (public_id.strip(),)
        )
        user = cursor.fetchone()
        
        if not user:
            return (False, None)
        
        user_id = user[0]

        public_id = public_id.strip()
        logger.info(f"Ищу public_id: '{public_id}'")

        # Обновляем лимиты
        cursor.execute(
            "UPDATE subscribers SET limits = limits + ? WHERE LOWER(public_id) = LOWER(?)",
            (amount, public_id.strip())
        )
        
        conn.commit()
        return (True, user_id)
    except Exception as e:
        logger.error(f"Ошибка в top_up_limits: {e}")
        return (False, None)
    finally:
        conn.close()


def get_user_limits(public_id: str) -> tuple[bool, int, int]:
    """
    Возвращает (success, limits, user_id) для пользователя по public_id.
    - success: True если найден
    - limits: количество лимитов
    - user_id: Telegram ID пользователя
    """
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT limits, user_id FROM subscribers WHERE LOWER(public_id) = LOWER(?)",
            (public_id.strip(),)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return (True, row[0], row[1])
        else:
            return (False, 0, None)
    except Exception as e:
        logger.error(f"Ошибка в get_user_limits: {e}")
        return (False, 0, None)


def get_user_info_by_user_id(user_id: int) -> tuple[bool, str, int]:
    """
    Возвращает (success, public_id, limits) для пользователя по его Telegram ID.
    - success: True если найден
    - public_id: его публичный ID
    - limits: количество лимитов
    """
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT public_id, limits FROM subscribers WHERE user_id = ?",
            (user_id, )
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return (True, row[0], row[1])
        else:
            return (False, "", 0)
    except Exception as e:
        logger.error(f"get_user_info_by_user_id: {e}")
        return (False, "", 0)
    