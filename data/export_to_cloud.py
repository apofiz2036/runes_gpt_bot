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
SQLITE_DB = os.path.join(os.path.dirname(__file__), "data/runes_bot.db")
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN")


def export_to_csv():
    try:
        # Указываем полный путь для CSV файлов
        csv_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(csv_dir, exist_ok=True)
        
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        subscribers_path = os.path.join(csv_dir, "subscribers.csv")
        divinations_path = os.path.join(csv_dir, "divinations.csv")

        # Экспорт subscribers
        cursor.execute("SELECT * FROM subscribers")
        with open(subscribers_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([i[0] for i in cursor.description])
            writer.writerows(cursor.fetchall())
        
        # Экспорт divinations
        cursor.execute("SELECT * FROM divinations")
        with open(divinations_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([i[0] for i in cursor.description])
            writer.writerows(cursor.fetchall())

        conn.close()
        return subscribers_path, divinations_path
    except Exception as e:
        error_message = f"Ошибка в export_to_csv {e}"
        logger.error(error_message)

def upload_to_yandex(subscribers_path, divinations_path):
    """Загружает CSV на Яндекс.Диск"""
    try:
        y = YaDisk(token=YANDEX_DISK_TOKEN)
        remote_dir = "runes_jpt_bot_data"

        if not y.exists(remote_dir):
            y.mkdir(remote_dir)
        
        y.upload(subscribers_path, f"{remote_dir}/subscribers.csv", overwrite=True)
        y.upload(divinations_path, f"{remote_dir}/divinations.csv", overwrite=True)
        print("Файлы загружены в Яндекс.Диск!")
    
    except Exception as e:
        error_message = f"Ошибка в upload_to_yandex {e}"
        logger.error(error_message)
        raise


if __name__ == '__main__':
    try:
        subs_path, div_path = export_to_csv()
        upload_to_yandex(subs_path, div_path)
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)
