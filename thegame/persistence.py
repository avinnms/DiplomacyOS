import json

from gamestate import Gamestate


def save_game(gamestate, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(gamestate.to_dict(), f, indent=2)


def load_game(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Gamestate.from_dict(data)
