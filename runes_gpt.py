from dotenv import load_dotenv
import os
import json
import random
import requests
import csv
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

load_dotenv()
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

SUBSCRIBERS_FILE = "subscribers.csv"

BOT_DESCRIPTION = """
🔮 *Рунический ПсихоБот* 

Я помогаю взглянуть на ситуацию через призму скандинавских рун, используя их как ассоциативные карты. 

*Как это работает:*
1. Задаёте вопрос или описываете ситуацию
2. Я "вытягиваю" случайную руну
3. Даю психологическую интерпретацию символа

Нет мистики — только работа с образами и подсознанием!

Примеры вопросов:
• Почему я чувствую тревогу?
• Как улучшить отношения с коллегой?
• Какие ресурсы мне сейчас нужны?
"""


def save_subscriber(user_id: int):
    file_exists = Path(SUBSCRIBERS_FILE).exists()

    with open(SUBSCRIBERS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["user_id", "first_seen"])
        writer.writerow([user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

def send_intro(chat_id, bot):
    bot.send_message(
        chat_id=chat_id,
        text=BOT_DESCRIPTION,
        parse_mode="Markdown"
    )


def start(update: Update, context):
    send_intro(update.message.chat_id, context.bot)


def help_command(update: Update, context):
    send_intro(update.message.chat_id, context.bot)


def load_rune_data():
    with open('runes.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data['one_rune']
    

def get_random_rune():
    rune_data = load_rune_data()
    all_runes = list(rune_data.keys())
    random_rune = random.choice(all_runes)

    single_runes = ["dagaz", "eihwaz", "gebo", "hagalaz", "inguz", "isa", "jera", "sowilo"]

    if random_rune in single_runes:
        name = rune_data[random_rune]['name']
        image = rune_data[random_rune]['image']
    else:
        variant = random.choice(list(rune_data[random_rune].keys()))
        name = rune_data[random_rune][variant]['name']
        image = rune_data[random_rune][variant]['image']

    image_path = os.path.join('images', image)
    return name, image_path

def load_prompt():
    with open('prompt.txt', 'r', encoding='utf-8') as f:
        return f.read()


def ask_gpt(user_question: str, rune_name: str):
    prompt = load_prompt().format(question=user_question, rune=rune_name)

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
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["result"]["alternatives"][0]["message"]["text"]
    except Exception as e:
        return "Упс, произошла ошибка"


def handle_message(update: Update, context):
    if not context.user_data.get('is_subscribed'):
        user = update.message.from_user
        save_subscriber(user.id)
        context.user_data['is_subscribed'] = True

    user_question = update.message.text
    rune_name, rune_image = get_random_rune()

    with open(rune_image, 'rb') as photo:
        update.message.reply_photo(photo)

    gpt_response = ask_gpt(user_question, rune_name)
    update.message.reply_text(gpt_response)


def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text, handle_message))

    updater.bot.send_message(
        chat_id=ADMIN_ID,
        text=' 🔮 Бот запущен и готов к работе!'
    )

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()