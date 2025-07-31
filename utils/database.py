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
SUBSCRIBERS_FILE = "data/subscribers.csv"
ADMIN_ID = os.getenv("ADMIN_ID")

def save_subscriber(user_id: int):
    """Сохраняет ID подписчика и временную метку"""
    try:
        file_exists = Path(SUBSCRIBERS_FILE).exists()

        with open(SUBSCRIBERS_FILE, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            if not file_exists:
                writer.writerow(["user_id", "first_seen"])

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")    
            writer.writerow([user_id, timestamp])
    except Exception as e:
        error_message = f"Ошибка в save_subscriber: {e}"
        logger.error(error_message)


def get_subscribers():
    """Получает уникальные ID из .csv файла, за исключением админа"""
    try:
        subscribers = []

        if not Path(SUBSCRIBERS_FILE).exists():
            return subscribers

        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)

            unique_subscribers = set()
            for row in reader:
                if not row:
                    continue

                user_id = int(row[0])
                if user_id != int(ADMIN_ID):
                    unique_subscribers.add(user_id)

        return list(unique_subscribers)
    except Exception as e:
        error_message = f"Ошибка в get_subscribers: {e}"
        logger.error(error_message)

