import sqlite3
import csv
import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
from yadisk import YaDisk

sys.path.append(str(Path(__file__).parent.parent))
from utils.logging import setup_logging

# Инициализация логгера
logger = logging.getLogger(__name__)
setup_logging()

load_dotenv()
SQLITE_DB = "data/runes_bot.db"
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN")


def export_to_csv():
    """Экспортирует данные из SQLite в .csv"""
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        # Экспорт subscribers
        cursor.execute("SELECT * FROM subscribers")
        with open("subscribers.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([i[0] for i in cursor.description])
            writer.writerows(cursor.fetchall())
        
        # Экспорт divinations
        cursor.execute("SELECT * FROM divinations")
        with open("divinations.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([i[0] for i in cursor.description])
            writer.writerows(cursor.fetchall())

        conn.close()
        print("Экспорт данных завершён")
    except Exception as e:
        error_message = f"Ошибка в export_to_csv {e}"
        logger.error(error_message)

def upload_to_yandex():
    """Загружает CSV на Яндекс.Диск"""
    try:
        y = YaDisk(token=YANDEX_DISK_TOKEN)
        remote_dir = "runes_jpt_bot_data"

        # Создаём папку если её нет
        if not y.exists(remote_dir):
            y.mkdir(remote_dir)
        
        # Загружаем файлы
        y.upload("subscribers.csv", f"{remote_dir}/subscribers.csv", overwrite=True)
        y.upload("divinations.csv", f"{remote_dir}/divinations.csv", overwrite=True)
        print("Файлы загружены в Яндекс.Диск!")
    
    except Exception as e:
        error_message = f"Ошибка в upload_to_yandex {e}"
        logger.error(error_message)


if __name__ == '__main__':
    export_to_csv()
    upload_to_yandex()
