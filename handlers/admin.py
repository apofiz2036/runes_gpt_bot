import os
from telegram import Update
from telegram.ext import ContextTypes
from utils.database import get_subscribers
import asyncio

ADMIN_ID = os.getenv("ADMIN_ID")

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin_message = (
        update.message.from_user.id == int(ADMIN_ID) or
        (update.message.forward_from and update.message.forward_from.id == int(ADMIN_ID))
    )

    subscribers = get_subscribers()
    
    for user_id in subscribers:
        try:
            # Если есть текст И фото
            if update.message.caption and update.message.photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption
                )
            # Если просто текст
            elif update.message.text:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=update.message.text
                )
            # Если просто фото без текста
            elif update.message.photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=update.message.photo[-1].file_id
                )
            # Если видео
            elif update.message.video:
                await context.bot.send_video(
                    chat_id=user_id,
                    video=update.message.video.file_id,
                    caption=update.message.caption
                )
            else:
                pass
                
            await asyncio.sleep(0.3)
            
        except Exception as e:
            continue