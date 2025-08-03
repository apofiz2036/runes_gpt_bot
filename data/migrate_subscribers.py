import sqlite3
import csv
from pathlib import Path
from datetime import datetime
import os

CSV_FILE = "subscribers.csv"
SQLITE_DB = "runes_bot.db"

def migrate():
    if not Path(CSV_FILE).exists():
        print('Файл CSV_FILE не найден')
        return

    with sqlite3.connect(SQLITE_DB) as conn:
        cursor = conn.cursor()

        #Читаем .csv файл
        with open(CSV_FILE, 'r', encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)

            for row in reader:
                if not row:
                    continue
                
                user_id = int(row[0])
                first_seen = row[1] if len (row) > 1 else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Проверяем существование пользователя
                cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
                if cursor.fetchone():
                    continue

                cursor.execute(
                    "INSERT INTO subscribers (user_id, first_seen, limits) VALUES (?, ?, 50)",
                    (user_id, first_seen)
                )

        conn.commit()
        print("Все данные перенесены")


if __name__ == "__main__":
    migrate()