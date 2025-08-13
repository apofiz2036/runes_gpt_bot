import sqlite3
import csv
import logging
from pathlib import Path
from dotenv import load_dotenv
from yadisk import YaDisk

from utils.logging import setup_logging
from config import SQLITE_DB, YANDEX_DISK_TOKEN

load_dotenv()

# Инициализация логгера
logger = logging.getLogger(__name__)
setup_logging()


def export_to_csv():
    """Загружает данные из SQLite в .csv файл"""
    try:
        # Указываем полный путь для CSV файлов
        db_path = Path(SQLITE_DB)
        csv_dir = db_path.parent
        csv_dir.mkdir(parents=True, exist_ok=True)

        subscribers_path = csv_dir / "subscribers.csv"
        divinations_path = csv_dir / "divinations.csv"

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
       
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

        return str(subscribers_path), str(divinations_path)
    except Exception as e:
        logger.exception(f"Ошибка в export_to_csv: {e}")

def upload_to_yandex(subscribers_path, divinations_path):
    """Загружает CSV на Яндекс.Диск"""
    try:
        y = YaDisk(token=YANDEX_DISK_TOKEN)
        remote_dir = "runes_jpt_bot_data"

        if not y.exists(remote_dir):
            y.mkdir(remote_dir)
        
        y.upload(subscribers_path, f"{remote_dir}/subscribers.csv", overwrite=True)
        y.upload(divinations_path, f"{remote_dir}/divinations.csv", overwrite=True)

        logger.info("Файлы успешно загружены в Яндекс.Диск.")
    except Exception as e:
        logger.exception(f"Ошибка в upload_to_yandex: {e}")
        raise


if __name__ == '__main__':
    try:
        subs_path, div_path = export_to_csv()
        upload_to_yandex(subs_path, div_path)
    except Exception as e:
        logger.exception(f"Critical error при выгрузке на облако: {e}")
