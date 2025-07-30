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

load_dotenv()
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

SUBSCRIBERS_FILE = "subscribers.csv"
SINGLE_RUNES = ["dagaz", "eihwaz", "gebo", "hagalaz", "inguz", "isa", "jera", "sowilo"]

with open('bot_description.txt', 'r', encoding='utf-8') as file:
    BOT_DESCRIPTION = file.read()


def save_subscriber(user_id: int):
    file_exists = Path(SUBSCRIBERS_FILE).exists()

    with open(SUBSCRIBERS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["user_id", "first_seen"])
        writer.writerow([user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Одна руна", "Три руны"],
        ["Как гадать"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.user_data['mode'] = 'main_menu'
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text=BOT_DESCRIPTION,
        parse_mode="Markdown",
    )
    await main_menu(update, context)


def load_rune_data():
    with open('runes.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data['one_rune']
    

def get_random_one_rune():
    rune_data = load_rune_data()
    all_runes = list(rune_data.keys())
    random_rune = random.choice(all_runes)

    if random_rune in SINGLE_RUNES:
        name = rune_data[random_rune]['name']
        image = rune_data[random_rune]['image']
    else:
        variant = random.choice(list(rune_data[random_rune].keys()))
        name = rune_data[random_rune][variant]['name']
        image = rune_data[random_rune][variant]['image']

    image_path = os.path.join('images', image)
    return name, image_path


def get_random_three_runes():
    rune_data = load_rune_data()
    all_runes_keys = list(rune_data.keys())
    selected_runes = random.sample(all_runes_keys, 3)

    result = []
    for rune_key in selected_runes:
        if rune_key in SINGLE_RUNES:
            variant = None
        else:
            variant = random.choice(list(rune_data[rune_key].keys()))

        result.append({
            'rune_key': rune_key,
            'variant': variant
        })
    
    return result


def load_prompt(prompt_type: str = 'one_rune'):
    file_name = f'prompt_{prompt_type}.txt'
    with open(file_name, 'r', encoding='utf-8') as f:
        return f.read()


async def ask_gpt(user_question: str, rune_data: dict, prompt_type: str = 'one_rune'):
    if prompt_type == 'one_rune':
        prompt = load_prompt('one_rune').format(
            question=user_question,
            rune=rune_data['name']
        )
    elif prompt_type == 'three_runes':
        prompt = load_prompt('three_runes').format(
            question=user_question,
            rune1=rune_data[0]['name'],
            rune2=rune_data[1]['name'],
            rune3=rune_data[2]['name'],
        )

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
    }
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
        "messages": [
            {"role": "system", "text": "Ты психолог, использующий скандинавские руны как ассоциативные карты. Даёшь рациональные интерпретации, основанные на символизме рун и современной психологии. Избегай мистики и предсказаний."},
            {"role": "user", "text": prompt},
        ],
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data) as response:
                response.raise_for_status()
                json_data = await response.json()
                return json_data["result"]["alternatives"][0]["message"]["text"]
        except Exception as e:
            return "Упс, произошла ошибка"


async def one_rune_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['Главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.user_data['mode'] = 'one_rune'
    context.user_data['prompt_type'] = 'one_rune'
    await update.message.reply_text("Задайте ваш вопрос для гадания на одной руне:", reply_markup=reply_markup)


async def three_runes_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['Главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.user_data['mode'] = 'three_rune'
    context.user_data['prompt_type'] = 'three_runes'

    context.user_data['selected_runes'] = get_random_three_runes()
    
    await update.message.reply_text(
        "Задайте ваш вопрос для гадания на трёх рунах",
        reply_markup=reply_markup
    )


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Одна руна":
        await one_rune_mode(update, context)
    if text == "Три руны":
        await three_runes_mode(update, context)
    if text == "Как гадать":
        await update.message.reply_text("Выбрано как гадать (функционал в разработке)")
    if text == "Главное меню":
        await main_menu(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_mode = context.user_data.get('mode')

    if current_mode not in ['one_rune', 'three_rune']:
        await main_menu(update, context)
        return

    if not context.user_data.get('is_subscribed'):
        user = update.message.from_user
        save_subscriber(user.id)
        context.user_data['is_subscribed'] = True
    
    user_question = update.message.text

    if current_mode == 'one_rune':
        rune_name, rune_image = get_random_one_rune()
        with open(rune_image, 'rb') as photo:
            await update.message.reply_photo(photo)
        gpt_response = await ask_gpt(user_question, {'name': rune_name}, 'one_rune')
    elif current_mode == 'three_rune':
        runes = context.user_data['selected_runes']
        rune_data = load_rune_data()

        for rune in runes:
            if rune['variant'] is None:
                image = rune_data[rune['rune_key']]['image']
            else:
                image = rune_data[rune['rune_key']][rune['variant']]['image']
            
            image_path = os.path.join('images', image)
            with open(image_path, 'rb') as photo:
                await update.message.reply_photo(photo)

        runes_for_prompt = []
        for rune in runes:
            if rune['variant'] is None:
                name = rune_data[rune['rune_key']]['name']
            else:
                name = rune_data[rune['rune_key']][rune['variant']]['name']
            runes_for_prompt.append({'name': name})

        gpt_response = await ask_gpt(user_question, runes_for_prompt, 'three_runes')

    await update.message.reply_text(gpt_response)
    await main_menu(update, context)


def get_subscribers():
    subscribers = []

    if not Path(SUBSCRIBERS_FILE).exists():
        return subscribers

    with open(SUBSCRIBERS_FILE, 'r', encoding='utf8') as f:
        reader = csv.reader(f)
        next(reader)

        unique_subscribers = set()
        for row in reader:
            if not row:
                continue

            user_id = int(row[0])
            if user_id != int(ADMIN_ID):
                unique_subscribers.add(user_id)

    return list(unique_subscribers)


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


if __name__ == '__main__':
    def start_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
            
            application.add_handler(CommandHandler("start", start))
            application.add_handler(MessageHandler(
                filters.TEXT & (
                    filters.Regex("^Одна руна$") |
                    filters.Regex("^Три руны$") |
                    filters.Regex("^Как гадать$")
                ),
                handle_menu
            ))
            application.add_handler(MessageHandler(
                (filters.TEXT & filters.User(int(ADMIN_ID))) | 
                (filters.FORWARDED & filters.User(int(ADMIN_ID))), 
                handle_forwarded_message
            ))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.User(int(ADMIN_ID)), handle_message))
            
            application.run_polling()
            
        except KeyboardInterrupt:
            print("Бот остановлен")
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            loop.close()

    start_bot()


