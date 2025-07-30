from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from pathlib import Path
import csv
from datetime import datetime

SUBSCRIBERS_FILE = "subscribers.csv"
with open('bot_description.txt', 'r', encoding='utf-8') as file:
    BOT_DESCRIPTION = file.read()


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Одна руна", "Три руны"],
        ["Как гадать"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.user_data['mode'] = 'main_menu'
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    chat_id = update.message.chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text=BOT_DESCRIPTION,
        parse_mode="Markdown",
    )
    await main_menu(update, context)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await main_menu(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Ошибка {context.error}")

    if update and hasattr(update, 'message'):
        await update.message.reply_text(
            "Произошла ошибка. Возвращаю в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        ) 