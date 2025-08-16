import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from utils.logging import setup_logging, send_error_to_admin


# Инициализация логгера
logger = logging.getLogger(__name__)
setup_logging()

BOT_DESCRIPTION = "Описание бота временно недоступно."

# Чтение описания бота из файла
try:
    with open('text/bot_description.txt', 'r', encoding='utf-8') as file:
        BOT_DESCRIPTION = file.read()
except Exception as e:
    error_message = f"Ошибка загрузки файла описания бота: {e}"
    logger.error(error_message)


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает главное меню с кнопками выбора действия."""  
    try:  
        keyboard = [
            ["Одна руна", "Три руны"],
            ["Четыре руны", "Судьба"],
            ["Как гадать", "Мои лимиты"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        context.user_data['mode'] = 'main_menu'

        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
    except Exception as e:
        error_message = f"Ошибка в main_menu: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)

    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Инициализирует бота для пользователя."""
    try:
        context.user_data.clear()
        chat_id = update.message.chat_id

        await context.bot.send_message(
            chat_id=chat_id,
            text=BOT_DESCRIPTION,
            parse_mode="Markdown",
        )
        await main_menu(update, context)
    except Exception as e:
        error_message = f"Произошла ошибка в обработчике start: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE)  -> None:
    """Обработчик команды /menu. Возвращает пользователя в главное меню."""
    try:
        context.user_data.clear()
        await main_menu(update, context)
    except Exception as e:
        error_message = f"Произошла ошибка в menu_command: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок бота."""
    try:
        logger.error(f"Ошибка: {context.error}")

        if update and hasattr(update, 'message'):
            await update.message.reply_text(
                "Произошла ошибка. Возвращаю в главное меню.",
                reply_markup=ReplyKeyboardMarkup([["Главное меню"]], resize_keyboard=True)
            )
    except Exception as e:
        logger.error(f"Ошибка внутри error_handler: {e}") 
        await send_error_to_admin(context.bot, f"Ошибка в error_handler: {e}")

