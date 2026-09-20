import json
import os

from gamestate import Gamestate
from province import load_provinces
from unit import load_units, units_by_location
from cli import run_game

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "savegame.json")

POWERS = ["England", "France", "Germany", "Austria-Hungary", "Italy", "Turkey", "Russia"]


def start_game():
    with open(os.path.join(BASE_DIR, "provincedb.json"), "r", encoding="utf-8") as f:
        province_data = json.load(f)
    with open(os.path.join(BASE_DIR, "unitdb.json"), "r", encoding="utf-8") as f:
        unit_data = json.load(f)

    provinces = load_provinces(province_data)
    units = units_by_location(load_units(unit_data))

    supply_center_owner = {
        province_id: province.original_owner
        for province_id, province in provinces.items()
        if province.supply
    }

    gamestate = Gamestate(
        year=1901,
        season="Spring",
        phase="Movement",
        units=units,
        owner=supply_center_owner,
        powers=POWERS,
    )

    run_game(gamestate, provinces, save_path=SAVE_PATH)


if __name__ == "__main__":
    start_game()
