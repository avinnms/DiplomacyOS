
from gamestate import Gamestate
from unit import Unit
from unit import load_units
from province import load_provinces
from province import Province


def start_game():
    load_provinces(data)
    year = 1901
    season = "spring"
    phase = "movement"
    units = Unit.load
    powers = ["England", "France", "Germany", "Austria-Hungary", "Italy", "Turkey", "Russia"]
    supply_center_owner = {}
    for key, entry in data.items():
        supply_center_owner[key] = Province()
