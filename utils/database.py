from pathlib import Path
import csv
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
SUBSCRIBERS_FILE = "data/subscribers.csv"
ADMIN_ID = os.getenv("ADMIN_ID")

def save_subscriber(user_id: int):
    file_exists = Path(SUBSCRIBERS_FILE).exists()

    with open(SUBSCRIBERS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["user_id", "first_seen"])
        writer.writerow([user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])


def get_subscribers():
    subscribers = []

    if not Path(SUBSCRIBERS_FILE).exists():
        return subscribers

    with open(SUBSCRIBERS_FILE, 'r', encoding='utf8') as f:
        reader = csv.reader(f)
        next(reader)

        unique_subscribers = set()
        for row in reader:
            if not row:
                continue

            user_id = int(row[0])
            if user_id != int(ADMIN_ID):
                unique_subscribers.add(user_id)

    return list(unique_subscribers)

