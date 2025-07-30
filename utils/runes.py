import json
import random
import os

SINGLE_RUNES = ["dagaz", "eihwaz", "gebo", "hagalaz", "inguz", "isa", "jera", "sowilo"]

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


