import asyncio
import logging
from dotenv import load_dotenv
from pytz import timezone
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from handlers.base import start, menu_command, error_handler, main_menu
from handlers.runes import (
    one_rune_mode, 
    three_runes_mode, 
    four_runes_mode, 
    handle_message,
    fate_mode,
    field_mode
)
from handlers.admin import setup_admin_handlers
from utils.database import init_db, get_user_info_by_user_id
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.scheduler import reset_daily_limits
from data.export_to_cloud import export_to_csv, upload_to_yandex
from utils.payment import payment_message, handle_payment_input
from utils.logging import setup_logging, send_error_to_admin
from config import TELEGRAM_BOT_TOKEN, ADMIN_ID

load_dotenv()

# Инициализация логгера
logger = logging.getLogger(__name__)
setup_logging()


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка параметров меню выбранных пользователем"""
    try:
        if not update.message:
            return

        text = update.message.text

        if text == "Одна руна":
            await one_rune_mode(update, context)
        elif text == "Три руны":
            await three_runes_mode(update, context)
        elif text == "Четыре руны":
            await four_runes_mode(update, context)
        elif text == "Судьба":
            await fate_mode(update, context)
        elif text == "Вспаханное поле":
            await field_mode(update, context)
        elif text == "Как гадать":
            with open('text/how_to_guess.txt', 'r', encoding='utf-8') as file:
                text = file.read()      
            await update.message.reply_text(text)
        elif text == "Мои лимиты":
            success, public_id, limits = await get_user_info_by_user_id(update.effective_user.id)
            if success:
                await update.message.reply_text(
                    f"Ваш public_id: {public_id}\n"
                    f"Ваши лимиты: {limits}"
                )
            else:
                await update.message.reply_text(
                "Не удалось найти ваши данные. Попробуйте снова или напишите в поддержку."
            )
        elif text == "Пополнить лимиты":
            await payment_message(update, context)
        elif text == "Главное меню":
            context.user_data.clear()
            await main_menu(update, context)
    except Exception as e:
        error_message = f"Ошибка в handle_menu: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)


def setup_handlers(application) -> None:
    """Установка всех обработчиков для бота."""
    try:
        # Обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("menu", menu_command))

        # Обработчики меню
        menu_filters = filters.TEXT & (
            filters.Regex("^Одна руна$") |
            filters.Regex("^Три руны$") |
            filters.Regex("^Четыре руны$") |
            filters.Regex("^Судьба$") |
            filters.Regex("^Вспаханное поле$") |
            filters.Regex("^Как гадать$") |
            filters.Regex("^Мои лимиты$") |
            filters.Regex("^Пополнить лимиты$") |
            filters.Regex("^Главное меню$")
        )
        application.add_handler(MessageHandler(menu_filters, handle_menu))

        #  Обработчики администратора
        setup_admin_handlers(application)

        #  Обработчик сообщений об оплате
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.User(int(ADMIN_ID)) & ~menu_filters,
                handle_payment_input
            )
        )

        #  Обработчик сообщений обычных пользователей
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.User(int(ADMIN_ID)), handle_message)
        )

        #  Обработчик ошибок
        application.add_error_handler(error_handler)
    except Exception as e:
        error_message = f"Ошибка в setup_handlers: {e}"
        logger.error(error_message)


def export_and_upload():
    """Экспорт и загрузка файлов в облако."""
    try:
        subs_path, div_path = export_to_csv()
        upload_to_yandex(subs_path, div_path)
    except Exception as e:
        error_message = f"Ошибка в export_and_upload: {e}"
        logger.error(error_message)


async def run_bot() -> None:
    """Основная асинхронная функция для запуска бота"""
    try:
        await init_db()
        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        setup_handlers(application)

        scheduler = AsyncIOScheduler(timezone=timezone("Europe/Moscow"))
        scheduler.add_job(reset_daily_limits, 'cron', hour=0, minute=0)
        scheduler.add_job(export_and_upload, 'cron', hour='*/3', minute=0)
        scheduler.start()

        await application.initialize()
        await application.start()
        await application.updater.start_polling()

        logger.info("Бот запущен и работает...")

        stop_event = asyncio.Event()
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        error_message = f"Ошибка в run_bot: {e}"
        logger.error(error_message)
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