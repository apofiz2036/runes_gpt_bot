import json
import os
import random
import asyncio
from typing import List, Dict, Optional, Tuple, Union

RUNES_FILE = os.path.join("runes.json")


async def _load_full_json() -> Dict:
    """Служебная: грузит исходный JSON целиком в отдельном потоке."""
    try:
        return await asyncio.to_thread(_read_json_file, RUNES_FILE)
    except Exception:
        return {}


def _read_json_file(path: str) -> Dict:
    """Блокирующее чтение JSON (используется внутри to_thread)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def load_rune_data() -> Dict[str, Dict]:
    """
    Возвращает словарь с данными рун (ключи — названия рун в нижнем регистре).

    Формат:
    {
        "<rune_key>": {
            "<rune_key>_direct": {"name": "...", "image": "..."},
            "<rune_key>_revers": {"name": "...", "image": "..."},
            # или если без вариантов:
            "name": "...",
            "image": "..."
        },
        ...
    }
    """
    data = await _load_full_json()
    return data.get("one_rune", {})

def _pick_variant_key(rune_key: str, node: Dict) -> Optional[str]:
    """
    Для конкретной руны решает, какой вариант взять:
    - если есть *_direct / *_revers → случайно выбираем один
    - если вариантов нет → None
    """
    direct_key = f"{rune_key}_direct"
    revers_key = f"{rune_key}_revers"

    has_direct = direct_key in node
    has_revers = revers_key in node

    if not has_direct and not has_revers:
        return None
    
    candidates = []
    if has_direct:
        candidates.append(direct_key)
    if has_revers:
        candidates.append(revers_key)

    return random.choice(candidates)


async def get_random_runes(count: int) -> List[Dict[str, Optional[str]]]:
    """
    Универсальный выбор N рун.
    Возвращает список словарей:
        {"rune_key": <str>, "variant": <None|str>}
    """
    rune_data = await load_rune_data()
    rune_keys = list(rune_data.keys())
    if not rune_keys:
        return []
    
    chosen_keys = random.sample(rune_keys, count)
    
    result: List[Dict[str, Optional[str]]] = []
    for rune_key in chosen_keys:
        node = rune_data.get(rune_key, {})
        variant_key = _pick_variant_key(rune_key, node)
        result.append({"rune_key": rune_key, "variant": variant_key})
    
    return result


async def get_random_one_rune() -> Tuple[str, str]:
    """
    Выбирает одну руну и возвращает (имя, путь_к_картинке).
    """
    rune_data = await load_rune_data()
    if not rune_data:
        return "", ""
    
    rune_key = random.choice(list(rune_data.keys()))
    node = rune_data.get(rune_key, {})
    variant_key = _pick_variant_key(rune_key, node)

    if variant_key is None:
        name = node.get("name", "")
        image = node.get("image", "")
    else:
        variant_node = node.get(variant_key, {})
        name = variant_node.get("name", "")
        image = variant_node.get("image", "")
    
    image_path = os.path.join("images", image) if image else ""
    return name, image_path

# Обёртки для обратной совместимости
async def get_random_three_runes() -> List[Dict[str, Optional[str]]]:
    return await get_random_runes(3)

async def get_random_four_runes() -> List[Dict[str, Optional[str]]]:
    return await get_random_runes(4)

async def get_random_six_runes() -> List[Dict[str, Optional[str]]]:
    return await get_random_runes(6)


async def get_random_twelve_runes() -> List[Dict[str, Optional[str]]]:
    return await get_random_runes(12)

