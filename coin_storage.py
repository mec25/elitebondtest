import json
import os

COIN_FILE = "coins.json"

def load_coins():
    if not os.path.exists(COIN_FILE):
        return {}
    with open(COIN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_coins(data):
    with open(COIN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def get_user_data(user_id):
    data = load_coins()
    if str(user_id) not in data:
        data[str(user_id)] = {"coins": 0, "last_claim": "1970-01-01T00:00:00"}
        save_coins(data)
    return data[str(user_id)]

def update_user_data(user_id, coins=None, last_claim=None):
    data = load_coins()
    if str(user_id) not in data:
        data[str(user_id)] = {"coins": 0, "last_claim": "1970-01-01T00:00:00"}
    if coins is not None:
        data[str(user_id)]["coins"] = coins
    if last_claim is not None:
        data[str(user_id)]["last_claim"] = last_claim
    save_coins(data)