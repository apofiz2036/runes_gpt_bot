from pathlib import Path
import csv
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
SUBSCRIBERS_FILE = "data/subscribers.csv"
ADMIN_ID = os.getenv("ADMIN_ID")

def save_subscriber(user_id: int):
    """Сохраняет ID подписчика и временную метку"""
    file_exists = Path(SUBSCRIBERS_FILE).exists()

    with open(SUBSCRIBERS_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["user_id", "first_seen"])

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")    
        writer.writerow([user_id, timestamp])


def get_subscribers():
    """Получает уникальные ID из .csv файла, за исключением админа"""
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

