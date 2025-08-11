import asyncio
import os
import logging
from typing import Optional
from telegram import Update, Message, PhotoSize, Video, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from utils.database import get_subscribers, top_up_limits, get_user_limits
from utils.logging import setup_logging, send_error_to_admin

# Инициализация логгера
logger = logging.getLogger(__name__)
setup_logging()

ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Состояния для администратора
WAITING_FOR_BROADCAST = 1
WAITING_FOR_TOP_UP = 2
WAITING_FOR_LIMITS_CHECK = 3

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton("Рассылка"), KeyboardButton("Подписчики")],
        [KeyboardButton("Пополнить лимиты"), KeyboardButton("Узнать лимиты пользователя")],
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
        await update.message.reply_text(
            "Введите данные в формате 'RUNES-ABC123 500'",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Главное меню")]], resize_keyboard=True)
        )
        context.user_data["admin_state"] = WAITING_FOR_TOP_UP

    elif text == "Узнать лимиты пользователя":
        await update.message.reply_text(
            "Введите public_id пользователя в формате 'RUNES-ABC123'",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Главное меню")]], resize_keyboard=True)
        )
        context.user_data["admin_state"] = WAITING_FOR_LIMITS_CHECK

    elif text == "Главное меню":
        await admin_menu(update, context)
        if "admin_state" in context.user_data:
            del context.user_data["admin_state"] 

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает сообщения от администратора
    """
    try:
        if update.effective_user.id != ADMIN_ID:
            return
        admin_state = context.user_data.get("admin_state")
        if not admin_state:
            return
        
        admin_state = context.user_data.get("admin_state")

        # Обработка состояния рассылки
        if admin_state == WAITING_FOR_BROADCAST:
            subscribers = get_subscribers()
            message = update.message
            bot = context.bot

            total_count = len(subscribers)
            start_message = f"Начата рассылка для {total_count} подписчиков"
            logger.info(start_message)
            await bot.send_message(chat_id=ADMIN_ID, text=start_message)

            blocked_users = 0
            other_errors = 0

            for user_id in subscribers:
                try:
                    await _send_message_to_subscriber(context.bot, user_id, message)
                    await asyncio.sleep(0.3)
                except Exception as e:
                    if "bot was blocked by the user" in str(e):
                        blocked_users += 1
                        logger.debug(f"Пользователь {user_id} заблокировал бота")
                    else:
                        other_errors += 1
                        error_message = f"Ошибка при отправке пользователю {user_id}: {e}"
                        logger.error(error_message)

            result_message = f"Рассылка завершена!\n\n"
            result_message += f"Успешно отправлено: {total_count - blocked_users - other_errors}\n"
            if blocked_users > 0:
                result_message += f"Заблокировали бота: {blocked_users}\n"
            if other_errors > 0:
                result_message += f"Другие ошибки: {other_errors}\n"
            
            await bot.send_message(chat_id=ADMIN_ID, text=result_message)
            await admin_menu(update, context)
            del context.user_data["admin_state"]
            return
        
        # Оработчик для пополнения лимитов
        if admin_state == WAITING_FOR_TOP_UP:
            message_text = update.message.text.strip()
            parts = message_text.split()

            if len(parts) != 2:
                await update.message.reply_text(
                    "Неверный формат. Введите данные как:\npublic_id 500"
                )
                return
            
            public_id = parts[0]
            amount_str = parts[1]
            
            try:
                amount = int(amount_str)
            except ValueError:
                await update.message.reply_text("Сумма должна быть числом")
                return
            
            success, user_id = top_up_limits(public_id, amount)

            if success:
                await update.message.reply_text(
                    f"Лимиты пользователя {public_id} успешно пополнены на {amount}",
                    reply_markup=get_admin_keyboard()
                )
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"Ваши лимиты изменены на {amount}. Текущий баланс можно проверить в меню."
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
            else:
                await update.message.reply_text(
                    f"Пользователь {public_id} не найден",
                    reply_markup=get_admin_keyboard()
                )

            # Выходим из состояния
            del context.user_data["admin_state"]
            return
        
        # Обработчик инфо лимитов пользователя
        if admin_state == WAITING_FOR_LIMITS_CHECK:
            public_id = update.message.text.strip()
            success, limits, user_id = get_user_limits(public_id)
            if success:
                await update.message.reply_text(
                    f"Телеграм id: {user_id}, public_id: {public_id}, Лимитов: {limits}"
                )
        else:
            await update.message.reply_text(
                    f"Пользователь {public_id} не найден.",
                    reply_markup=get_admin_keyboard()
                )
        del context.user_data['admin_state']
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
    application.add_handler(MessageHandler(filters.Text(["Рассылка", "Подписчики", "Пополнить лимиты", "Узнать лимиты пользователя", "Главное меню"]) & filters.User(ADMIN_ID), handle_admin_buttons))
    application.add_handler(MessageHandler(filters.ALL & filters.User(ADMIN_ID), handle_forwarded_message))

