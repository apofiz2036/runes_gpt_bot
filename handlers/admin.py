import asyncio
import os
from typing import Optional
from telegram import Update, Message, PhotoSize, Video
from telegram.ext import ContextTypes
from utils.database import get_subscribers

ADMIN_ID = int(os.getenv("ADMIN_ID"))

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает сообщения от администратора и рассылает их подписчикам.
    Поддержиает тестовые сообщения, фото (с подписью и без), видео.
    """
    if not _is_admin_message(update):
        return
    
    subscribers = get_subscribers()
    message = update.message

    for user_id in subscribers:
        await _send_message_to_subscriber(context.bot, user_id, message)
        await asyncio.sleep(0.3)


def _is_admin_message(update: Update) -> bool:
    """Проверяет пришло ли сообщение от админа."""
    user = update.effective_user
    forwarded_user = update.message.forward_from

    return (user and user.id == ADMIN_ID) or (forwarded_user and forwarded_user.id == ADMIN_ID)


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
        print(f"Ошибка при отправке пользователю {user_id}: {e}")


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

