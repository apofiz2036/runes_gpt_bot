from dotenv import load_dotenv
import os
import json
import random
import csv
from datetime import datetime
from pathlib import Path
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler,
    MessageHandler,
    filters, 
    ContextTypes,
    )
import aiohttp
import asyncio

from handlers.base import start, menu_command, error_handler, main_menu
from handlers.runes import one_rune_mode, three_runes_mode, handle_message
from handlers.admin import handle_forwarded_message

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Одна руна":
        await one_rune_mode(update, context)
    if text == "Три руны":
        await three_runes_mode(update, context)
    if text == "Как гадать":
        with open('how_to_guess.txt', 'r', encoding='utf-8') as file:
            text = file.read()      
        await update.message.reply_text(text)
    if text == "Главное меню":
        await main_menu(update, context)


if __name__ == '__main__':
    def start_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
            
            # Обработчики команд
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("menu", menu_command))

            application.add_handler(MessageHandler(
                filters.TEXT & (
                    filters.Regex("^Одна руна$") |
                    filters.Regex("^Три руны$") |
                    filters.Regex("^Как гадать$") |
                    filters.Regex("^Главное меню$")
                ),
                handle_menu
            ))
            application.add_handler(MessageHandler(
                (filters.TEXT & filters.User(int(ADMIN_ID))) | 
                (filters.FORWARDED & filters.User(int(ADMIN_ID))), 
                handle_forwarded_message
            ))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.User(int(ADMIN_ID)), handle_message))

            # Обработчики ошибок
            application.add_error_handler(error_handler)
            
            application.run_polling()
            
        except KeyboardInterrupt:
            print("Бот остановлен")
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            loop.close()

    start_bot()


