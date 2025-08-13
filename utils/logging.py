import logging
from logging.handlers import RotatingFileHandler
import os
from telegram import Bot
from config import ADMIN_ID


def setup_logging():
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    file_handler = RotatingFileHandler(
        'bot_errors.log',
        maxBytes=1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.ERROR)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            file_handler,
            logging.StreamHandler()
        ]
    )


async def send_error_to_admin(bot: Bot, error_message: str):
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Ошибка: {error_message}"
    )
