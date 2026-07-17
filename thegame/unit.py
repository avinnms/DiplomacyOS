class Unit:
    def __init__(self, unit_type, owner, location):
        self.unit_type = unit_type
        self.owner = owner
        self.location = location


def load_units(data):
    units = {}
    for key, entry in data.items():
        units[key] = Unit(entry["unit_type"], entry["owner"], entry["location"])