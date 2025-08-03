import asyncio
import os
import logging
from typing import Optional
from telegram import Update, Message, PhotoSize, Video, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from utils.database import get_subscribers
from utils.logging import setup_logging, send_error_to_admin

# Инициализация логгера
logger = logging.getLogger(__name__)
setup_logging()

ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Состояния для администратора
WAITING_FOR_BROADCAST = 1

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton("Рассылка")],
        [KeyboardButton("Подписчики")],
        [KeyboardButton("Пополнить лимиты")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /admin, показывает меню администратора"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    await update.message.reply_text(
        "Меню администратора",
        reply_markup=get_admin_keyboard()
    )


async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопок администратора"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    text = update.message.text
    bot = context.bot

    if text == "Рассылка":
        await update.message.reply_text(
            "Отправьте сообщение для рассылки",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Главное меню")]], resize_keyboard=True)
        )
        context.user_data["admin_state"] = WAITING_FOR_BROADCAST
    
    elif text == "Подписчики":
        subscribers = get_subscribers()
        total_count = len(subscribers)
        message = f"На бот подписано {total_count} подписчиков"
        await bot.send_message(chat_id=ADMIN_ID, text=message)

    elif text == "Пополнить лимиты":
        await bot.send_message(chat_id=ADMIN_ID, text="В разработке")

    elif text == "Главное меню":
        await admin_menu(update, context)
        if "admin_state" in context.user_data:
            del context.user_data["admin_state"] 

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает сообщения от администратора и рассылает их подписчикам.
    Поддержиает тестовые сообщения, фото (с подписью и без), видео.
    """
    try:
        if (update.effective_user.id == ADMIN_ID and 
            context.user_data.get("admin_state") == WAITING_FOR_BROADCAST):
            subscribers = get_subscribers()
            message = update.message
            bot = context.bot

            total_count = len(subscribers)
            start_message = f"Начата рассылка для {total_count} подписчиков"
            logger.info(start_message)
            await bot.send_message(chat_id=ADMIN_ID, text=start_message)

            for user_id in subscribers:
                try:
                    await _send_message_to_subscriber(context.bot, user_id, message)
                    await asyncio.sleep(0.3)
                except Exception as e:
                    error_message = f"Ошибка при отправке пользователю {user_id}: {e}"
                    logger.error(error_message)
                    await send_error_to_admin(context.bot, error_message)
            await admin_menu(update, context)
            del context.user_data["admin_state"]
            return
        if not _is_admin_message(update):
            return
    except Exception as e:
        error_message = f"Критическая ошибка в handle_forwarded_message: {e}"
        logger.critical(error_message)
        await send_error_to_admin(context.bot, error_message)


def _is_admin_message(update: Update) -> bool:
    """Проверяет пришло ли сообщение от админа."""
    try:
        user = update.effective_user
        forwarded_user = update.message.forward_from
        return (user and user.id == ADMIN_ID) or (forwarded_user and forwarded_user.id == ADMIN_ID)
    except Exception as e:
        logger.error(f"Ошибка в _is_admin_message: {e}")
        return False
    


async def _send_message_to_subscriber(bot, user_id: int, message: Message) -> None:
    """Отправляет сообщение подписчику с обработкой различных типов контента."""
    try:
        if message.caption and message.photo:
            await _send_photo_with_caption(bot, user_id, message)
        elif message.text:
            await bot.send_message(chat_id=user_id, text=message.text)
        elif message.photo:
            await _send_photo(bot, user_id, message.photo[-1])
        elif message.video:
            await _send_video(bot, user_id, message)
    except Exception as e:
        error_message = f"Ошибка при отправке пользователю {user_id}: {e}"
        logger.error(error_message)
        raise


async def _send_photo_with_caption(bot, user_id: int, message: Message) -> None:
    """Отправляет фото с подписью."""
    await bot.send_photo(
        chat_id=user_id,
        photo=message.photo[-1].file_id,
        caption=message.caption
    )


async def _send_photo(bot, user_id: int, photo: PhotoSize) -> None:
    """Отправляет фото без подписи."""
    await bot.send_photo(chat_id=user_id, photo=photo.file_id)


async def _send_video(bot, user_id: int, message: Message) -> None:
    """Отправляет видео с подписью (если есть)."""
    await bot.send_video(
        chat_id=user_id,
        video=message.video.file_id,
        caption=message.caption
    )


def setup_admin_handlers(application):
    """Настройка обработчиков для администратора"""
    application.add_handler(CommandHandler("admin", admin_menu, filters=filters.User(ADMIN_ID)))
    application.add_handler(MessageHandler(filters.Text(["Рассылка", "Подписчики", "Пополнить лимиты", "Главное меню"]) & filters.User(ADMIN_ID), handle_admin_buttons))
    application.add_handler(MessageHandler(filters.ALL & filters.User(ADMIN_ID), handle_forwarded_message))
