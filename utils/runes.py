import json
import random
import os
from typing import Dict, List, Tuple, Union

# Руны, которые имеют только одно значение
SINGLE_RUNES = ["dagaz", "eihwaz", "gebo", "hagalaz", "inguz", "isa", "jera", "sowilo"]

def load_rune_data() -> Dict:
    """Загружает данные о рунах из JSON-файла.
    
    Возвращает: Словарь с данными о рунах (только раздел 'one_rune')"""
    with open('runes.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data['one_rune']
    

def get_random_one_rune() -> Tuple[str, str]:
    """Выбирает случайную руну и возвращает её описание и путь к изображению."""
    rune_data = load_rune_data()
    all_runes = list(rune_data.keys())
    random_rune = random.choice(all_runes)

    # Обработка рун с вариантами и без
    if random_rune in SINGLE_RUNES:
        rune_info = rune_data[random_rune]
    else:
        variant = random.choice(list(rune_data[random_rune].keys()))
        rune_info = rune_data[random_rune][variant]

    image_path = os.path.join('images', rune_info['image'])
    return rune_info['name'], image_path


def get_random_three_runes() -> List[Dict[str, Union[str, None]]]:
    """Выбирает три случайные руны для гадания
    Возвращает: Список словарей с информацией о рунах:
        [{
            'rune_key': ключ руны,
            'variant': вариант руны (None для рун без вариантов)
        }, ...]
    """
    rune_data = load_rune_data()
    all_runes_keys = list(rune_data.keys())
    selected_runes = random.sample(all_runes_keys, 3)

    result = []
    for rune_key in selected_runes:
        variant = None
        if rune_key not in SINGLE_RUNES:
            variant = random.choice(list(rune_data[rune_key].keys()))

        result.append({
            'rune_key': rune_key,
            'variant': variant
        })
    
    return result


