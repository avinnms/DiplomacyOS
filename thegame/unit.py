class Unit:
    def __init__(self, unit_type, owner, location):
        self.unit_type = unit_type
        self.owner = owner
        self.location = location


def load_units(data):
    units = {}
    for key, entry in data.items():
        units[key] = Unit(entry["unit_type"], entry["power"], entry["location_id"])
    return units


def units_by_location(units):
    """Re-key a units dict (however it's keyed) by each unit's current
    province, which is how the game engine looks units up on the board."""
    return {unit.location: unit for unit in units.values()}