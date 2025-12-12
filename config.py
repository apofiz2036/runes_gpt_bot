import os
from dotenv import load_dotenv

load_dotenv()

# Основные настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Yandex API
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

# База данных
SQLITE_DB = os.getenv("SQLITE_DB", "data/runes_bot.db")

# Лимиты
DEFAULT_LIMITS = int(os.getenv("DEFAULT_LIMITS", 50))

# ЮКасса
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")