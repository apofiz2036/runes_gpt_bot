import asyncio
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters, 
    )

from handlers.base import start, menu_command, error_handler, main_menu
from handlers.runes import one_rune_mode, three_runes_mode, handle_message
from handlers.admin import handle_forwarded_message

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка параметров меню выбранных пользователем"""
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


def setup_handlers(application) -> None:
    """Установка всех обработчиков для бота"""
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))

    # Обработчики меню
    menu_filters = filters.TEXT & (
        filters.Regex("^Одна руна$") |
                    filters.Regex("^Три руны$") |
                    filters.Regex("^Как гадать$") |
                    filters.Regex("^Главное меню$")
    )
    application.add_handler(MessageHandler(menu_filters, handle_menu))

    # Обработчики админа
    admin_filters = (
        (filters.TEXT & filters.User(int(ADMIN_ID))) | 
        (filters.FORWARDED & filters.User(int(ADMIN_ID)))
    )
    application.add_handler(MessageHandler(admin_filters, handle_forwarded_message))

    # Обработчик сообщений обычных пользователей
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.User(int(ADMIN_ID)), handle_message)
    )

    # Обработчик ошибок
    application.add_error_handler(error_handler)


async def run_bot() -> None:
    """Основная асинхронная функция для запуска бота"""
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    setup_handlers(application)
    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        print("Бот запущен и работает...")
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main() -> None:
    """Основная точка запуска бота"""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("Бот остановлен")
    except Exception as e:
        print(f"Ошибка: {e}")
    

if __name__ == '__main__':
    main()