import os
import aiohttp
from pathlib import Path
from typing import Dict, Union, List


YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")


def load_prompt(prompt_type: str = 'one_rune') -> str:
    """Загружает промпт из файла по указанному типу."""
    file_name = f'prompt_{prompt_type}.txt'
    with open(file_name, 'r', encoding='utf-8') as file:
        return file.read()
    

async def ask_gpt(user_question: str, rune_data: dict, prompt_type: str = 'one_rune') -> str:
    """Отправляет запрос к Yandex GPT API для интерпретации рун."""
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

    # Подготовка данных для запроса к Yandex GPT API
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
    }
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
        "messages": [
            {
                "role": "system", 
                "text": "Ты психолог, использующий скандинавские руны как ассоциативные карты. "
                        "Даёшь рациональные интерпретации, основанные на символизме рун и "
                        "современной психологии. Избегай мистики и предсказаний."
            },
            {"role": "user", "text": prompt},
        ],
    }
    
    # Отправка асинхронного запроса
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data) as response:
                response.raise_for_status()
                json_data = await response.json()
                return json_data["result"]["alternatives"][0]["message"]["text"]
        except Exception as e:
            return "Произошла непредвиденная ошибка при обработке запроса"
        
