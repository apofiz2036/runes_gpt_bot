import json
import os

PRICES_FILE = os.path.join("data", "prices.json")

def load_prices():
    with open(PRICES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
