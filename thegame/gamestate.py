class Gamestate:
    def __init__(self, year, season, phase, units, owner, powers):
        self.year = year
        self.season = season
        self.phase = phase
        self.units = units  # dict: province id -> Unit
        self.supply_center_owner = owner
        self.powers = powers

    def apply_adjudication(self, new_units):
        self.units = new_units

    def to_dict(self):
        return {
            "year": self.year,
            "season": self.season,
            "phase": self.phase,
            "units": {
                loc: {"unit_type": unit.unit_type, "owner": unit.owner, "location": unit.location}
                for loc, unit in self.units.items()
            },
            "supply_center_owner": self.supply_center_owner,
            "powers": self.powers,
        }

    @classmethod
    def from_dict(cls, data):
        from unit import Unit

        units = {
            loc: Unit(entry["unit_type"], entry["owner"], entry["location"])
            for loc, entry in data["units"].items()
        }
        return cls(data["year"], data["season"], data["phase"], units, data["supply_center_owner"], data["powers"])

