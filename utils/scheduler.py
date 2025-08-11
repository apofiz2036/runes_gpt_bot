import sqlite3
import logging
from datetime import datetime
from pytz import timezone
from utils.database import SQLITE_DB

logger = logging.getLogger(__name__)

def reset_daily_limits():
    """Обновляет лимиты всех пользователей до 50, если они меньше 50."""
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE subscribers
            SET limits = 50
            WHERE limits < 50
        """)

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка в reset_daily_limits: {e}")