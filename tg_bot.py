from dotenv import load_dotenv
import os
import requests
from telegram.ext import Updater, MessageHandler, Filters

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def ask_gpt(text):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
    }
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
        "messages": [
            {"role": "system", "text": "Ты — оракул рун. Отвечай мистически, 1-2 предложениями."},
            {"role": "user", "text": text},
        ],
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Проверяем HTTP-ошибки
        result = response.json()
        
        if "result" not in result:
            print("Ошибка в ответе API:", result)  # Логируем неправильный ответ
            return "Произошла ошибка. Попробуй ещё раз позже."
            
        return result["result"]["alternatives"][0]["message"]["text"]
        
    except Exception as e:
        print("Ошибка при запросе к YandexGPT:", e)
        return "Я не смог погадать. Попробуй ещё раз."

def handle_message(update, context):
    reply = ask_gpt(update.message.text)
    update.message.reply_text(reply)

updater = Updater(TELEGRAM_TOKEN)
updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_message))
updater.start_polling()
print("Бот запущен!")
updater.idle()