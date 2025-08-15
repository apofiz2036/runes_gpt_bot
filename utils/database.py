import aiosqlite
from pathlib import Path
import csv
import secrets
import os
import logging
from datetime import datetime
from utils.logging import setup_logging, send_error_to_admin
from config import SQLITE_DB, ADMIN_ID

# Инициализация логгера
logger = logging.getLogger(__name__)
setup_logging()


async def init_db():
    """
    Создайт базу данных с двумя таблицами
    - subscribers: хранит информацию о пользователях (user_id, first_seen, limits).
    - divinations: хранит историю гаданий (user_id, date, divination_type)
    """
    try:
        # Создаём папку если её ещё нет
        
        Path ("data").mkdir(exist_ok=True)

        # Подключаемся к базе данных
        conn = await aiosqlite.connect(SQLITE_DB)
        cursor = await conn.cursor()

        # Создаём таблицу subscribers
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                first_seen TEXT NOT NULL,
                limits INTEGER DEFAULT 50
            )
        """)

        # Создаём таблицу divinations
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS divinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                divination_type TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES subscribers (user_id)
            )
        """)

        # Сохраняем таблицу
        await conn.commit()
        await conn.close()

        await migrate_db() 
    except Exception as e:
        error_message = "Ошибка при создании базы данных"
        logger.error(error_message)


async def migrate_db(): 
    """Добавляет столбец public_id в таблицу subscribers, если его нет."""
    try:
        conn = await aiosqlite.connect(SQLITE_DB)
        cursor = await conn.cursor()
        
        # Проверяем существование столбца
        await cursor.execute("PRAGMA table_info(subscribers)")
        columns = [column[1] for column in await cursor.fetchall()]

        if "public_id" not in columns:
            # 1. Добавляем столбец БЕЗ UNIQUE сначала
            await cursor.execute("ALTER TABLE subscribers ADD COLUMN public_id TEXT")
            await conn.commit()
            logger.info("Добавлен столбец public_id (без UNIQUE)")

            # 2. Генерируем public_id для существующих пользователей
            await cursor.execute("SELECT user_id FROM subscribers WHERE public_id IS NULL")
            users = await cursor.fetchall()
            
            for (user_id,) in users:
                public_id = f"RUNES-{secrets.token_hex(3).upper()}"  # Например, RUNES-A1B2C3
                await cursor.execute(
                    "UPDATE subscribers SET public_id = ? WHERE user_id = ?",
                    (public_id, user_id)
                )
            
            await conn.commit()
            logger.info(f"Сгенерированы public_id для {len(users)} пользователей")

            # 3. Добавляем ограничение UNIQUE через новую таблицу
            await cursor.execute("""
                CREATE TABLE subscribers_new (
                    user_id INTEGER PRIMARY KEY,
                    first_seen TEXT NOT NULL,
                    limits INTEGER DEFAULT 50,
                    public_id TEXT UNIQUE
                )
            """)
            
            # Копируем данные из старой таблицы в новую
            await cursor.execute("""
                INSERT INTO subscribers_new 
                SELECT user_id, first_seen, limits, public_id 
                FROM subscribers
            """)
            
            # Удаляем старую таблицу и переименовываем новую
            await cursor.execute("DROP TABLE subscribers")
            await cursor.execute("ALTER TABLE subscribers_new RENAME TO subscribers")
            await conn.commit()
            logger.info("Добавлено ограничение UNIQUE для public_id")
        
    except Exception as e:
        error_message = f"Ошибка в migrate_db: {e}"
        logger.error(error_message)
        send_error_to_admin(error_message)
    finally:
        await conn.close()
        

async def save_subscriber(user_id: int):
    """Сохраняет подписчика в SQLite (или пропускает, если он уже есть)."""
    try:
        conn = await aiosqlite.connect(SQLITE_DB)
        cursor = await conn.cursor()

        # Проверяем существование пользователя
        await cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
        exist = await cursor.fetchone()

        if not exist:
            # Добавляем нового пользователя
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            public_id = f"RUNES-{secrets.token_hex(3).upper()}"
            await cursor.execute(
                "INSERT INTO subscribers (user_id, first_seen, public_id) VALUES (?, ?, ?)",
                (user_id, timestamp, public_id)
            )
            await conn.commit()
        await conn.close()
    except Exception as e:
        error_message = f"Ошибка в save_subscriber: {e}"
        logger.error(error_message)
        send_error_to_admin(error_message)


async def get_subscribers():
    """Получает уникальные ID из SQLite, за исключением админа"""
    try:
        conn = await aiosqlite.connect(SQLITE_DB)
        cursor = await conn.cursor()

        # Запрос для получения всех user_id, кроме админа
        await cursor.execute("""
            SELECT user_id FROM subscribers
            WHERE user_id != ?               
        """, (int(ADMIN_ID),))

        # Собираем уникальные ID в список
        subscribers = [row[0] for row in await cursor.fetchall()]
        await conn.close()

        return subscribers        
    except Exception as e:
        error_message = f"Ошибка в get_subscribers: {e}"
        logger.error(error_message)
        return []


async def save_divination(user_id: int, divination_type: str):
    """Сохраняет информацию о гадании в базу данных."""
    try:
        conn = await aiosqlite.connect(SQLITE_DB)
        cursor = await conn.cursor()

        # Проверяем существование пользователя
        await cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
        if not await cursor.fetchone():
            await save_subscriber(user_id)
        
        # Добавляем запись о гадании
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await cursor.execute(
            "INSERT INTO divinations (user_id, date, divination_type) VALUES (?, ?, ?)",
            (user_id, timestamp, divination_type)
        )

        await conn.commit()
    except Exception as e:
        error_message = f"Ошибка при сохранении гадания: {e}"
        logger.error(error_message)
        send_error_to_admin(error_message)
    finally:
        await conn.close()


async def top_up_limits(public_id: str, amount: int) -> tuple[bool, int]:
    """
    Пополняет лимиты пользователя по public_id.
    Возвращает (success, user_id), где:
    - success: True если операция успешна
    - user_id: ID пользователя или None если не найден
    """
    try:
        conn = await aiosqlite.connect(SQLITE_DB)
        cursor = await conn.cursor()

        # Получаем user_id перед обновлением
        await cursor.execute(
            "SELECT user_id FROM subscribers WHERE LOWER(public_id) = LOWER(?)",
            (public_id.strip(),)
        )
        user = await cursor.fetchone()
        
        if not user:
            return (False, None)
        
        user_id = user[0]

        public_id = public_id.strip()
        logger.info(f"Ищу public_id: '{public_id}'")

        # Обновляем лимиты
        await cursor.execute(
            "UPDATE subscribers SET limits = limits + ? WHERE LOWER(public_id) = LOWER(?)",
            (amount, public_id.strip())
        )
        
        await conn.commit()
        return (True, user_id)
    except Exception as e:
        logger.error(f"Ошибка в top_up_limits: {e}")
        return (False, None)
    finally:
        await conn.close()


async def get_user_limits(public_id: str) -> tuple[bool, int, int]:
    """
    Возвращает (success, limits, user_id) для пользователя по public_id.
    - success: True если найден
    - limits: количество лимитов
    - user_id: Telegram ID пользователя
    """
    try:
        conn = await aiosqlite.connect(SQLITE_DB)
        cursor = await conn.cursor()

        await cursor.execute(
            "SELECT limits, user_id FROM subscribers WHERE LOWER(public_id) = LOWER(?)",
            (public_id.strip(),)
        )

        row = await cursor.fetchone()
        await conn.close()

        if row:
            return (True, row[0], row[1])
        else:
            return (False, 0, None)
    except Exception as e:
        logger.error(f"Ошибка в get_user_limits: {e}")
        return (False, 0, None)


async def get_user_info_by_user_id(user_id: int) -> tuple[bool, str, int]:
    """
    Возвращает (success, public_id, limits) для пользователя по его Telegram ID.
    - success: True если найден
    - public_id: его публичный ID
    - limits: количество лимитов
    """
    try:
        conn = await aiosqlite.connect(SQLITE_DB)
        cursor = await conn.cursor()

        await cursor.execute(
            "SELECT public_id, limits FROM subscribers WHERE user_id = ?",
            (user_id, )
        )
        row = await cursor.fetchone()
        await conn.close()

        if row:
            return (True, row[0], row[1])
        else:
            return (False, "", 0)
    except Exception as e:
        logger.error(f"get_user_info_by_user_id: {e}")
        return (False, "", 0)


async def deduct_limits(user_id: int, amount: int) -> bool:
    """
    Списывает amount лимитов у пользователя.
    Возвращает True, если успешно (лимитов хватило), иначе False.
    """
    try:
        conn = await aiosqlite.connect(SQLITE_DB)
        cursor = await conn.cursor()

        # Проверяем текущее количество
        await cursor.execute("SELECT limits FROM subscribers WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            await conn.close()
            return False
        
        current_limits = row[0]
        if current_limits < amount:
            await conn.close()
            return False
        
        # Списываем
        await cursor.execute(
            "UPDATE subscribers SET limits = limits - ? WHERE user_id = ?",
            (amount, user_id)
        )
        await conn.commit()
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка в deduct_limits: {e}")
        return False