class Province:
    def __init__(self, id, fullname, type, is_supply_center, country_owner, army_moves, navy_moves):
        self.id = id
        self.full = fullname
        self.kind = type
        self.supply = is_supply_center
        self.original_owner = country_owner
        self.army_moves = army_moves
        self.navy_moves = navy_moves



def load_provinces(data):
    result = {}
    for key, entry in data.items():
        result[key] = Province(entry["id"], entry["full"], entry["kind"], entry["supply"], entry["original_owner"],
                               entry["army_moves"], entry["navy_moves"])
    return result 