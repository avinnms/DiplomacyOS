class OrderParseError(Exception):
    pass


class Order:
    def __init__(self, unit, origin):
        self.unit = unit
        self.origin = origin

    def __repr__(self):
        return f"{self.__class__.__name__}({self.origin})"


class HoldOrder(Order):
    order_type = "hold"


class MoveOrder(Order):
    order_type = "move"

    def __init__(self, unit, origin, destination):
        super().__init__(unit, origin)
        self.destination = destination

    def __repr__(self):
        return f"MoveOrder({self.origin} -> {self.destination})"


class SupportOrder(Order):
    order_type = "support"

    def __init__(self, unit, origin, supported_origin, supported_destination=None):
        super().__init__(unit, origin)
        self.supported_origin = supported_origin
        # None means "support the unit to hold" rather than to move.
        self.supported_destination = supported_destination

    def __repr__(self):
        if self.supported_destination:
            return f"SupportOrder({self.origin} S {self.supported_origin} -> {self.supported_destination})"
        return f"SupportOrder({self.origin} S {self.supported_origin} hold)"


class ConvoyOrder(Order):
    order_type = "convoy"

    def __init__(self, unit, origin, convoyed_origin, convoyed_destination):
        super().__init__(unit, origin)
        self.convoyed_origin = convoyed_origin
        self.convoyed_destination = convoyed_destination

    def __repr__(self):
        return f"ConvoyOrder({self.origin} C {self.convoyed_origin} -> {self.convoyed_destination})"


_TYPE_CODES = {"A": "Army", "F": "Fleet"}


def _moves_for(unit_type, province):
    return province.army_moves if unit_type == "Army" else province.navy_moves


def parse_order(text, units_by_location, provinces):
    """Parse one line of order notation for a single unit.

    Supported notation:
        A Par H                     -- hold
        A Par - Bur                 -- move
        F Bre S A Par               -- support a hold
        F Bre S A Par - Bur         -- support a move
        F Nth C A Lon - Nwy         -- convoy

    Raises OrderParseError with a human-readable message on anything invalid.
    """
    tokens = text.split()
    if len(tokens) < 3:
        raise OrderParseError(f"Could not parse order: {text!r}")

    unit_code, origin, verb = tokens[0], tokens[1], tokens[2]
    if unit_code not in _TYPE_CODES:
        raise OrderParseError(f"Unknown unit type {unit_code!r} (expected A or F)")
    unit_type = _TYPE_CODES[unit_code]

    if origin not in provinces:
        raise OrderParseError(f"Unknown province {origin!r}")
    unit = units_by_location.get(origin)
    if unit is None:
        raise OrderParseError(f"No unit at {origin}")
    if unit.unit_type != unit_type:
        raise OrderParseError(f"Unit at {origin} is a {unit.unit_type}, not a {unit_type}")

    if verb == "H":
        if len(tokens) != 3:
            raise OrderParseError(f"Hold orders take no destination: {text!r}")
        return HoldOrder(unit, origin)

    if verb == "-":
        if len(tokens) != 4:
            raise OrderParseError(f"Move orders need exactly one destination: {text!r}")
        destination = tokens[3]
        if destination not in provinces:
            raise OrderParseError(f"Unknown destination province {destination!r}")
        return MoveOrder(unit, origin, destination)

    if verb == "S":
        return _parse_support(tokens, unit, origin, units_by_location, provinces)

    if verb == "C":
        return _parse_convoy(tokens, unit, origin, units_by_location, provinces)

    raise OrderParseError(f"Unknown order verb {verb!r} in {text!r}")


def _parse_support(tokens, unit, origin, units_by_location, provinces):
    # tokens: F Bre S A Par [- Bur]
    if len(tokens) not in (5, 7):
        raise OrderParseError(f"Malformed support order: {' '.join(tokens)!r}")

    supported_unit_code, supported_origin = tokens[3], tokens[4]
    if supported_unit_code not in _TYPE_CODES:
        raise OrderParseError(f"Unknown unit type {supported_unit_code!r} in support order")
    if supported_origin not in provinces:
        raise OrderParseError(f"Unknown supported province {supported_origin!r}")
    if supported_origin not in units_by_location:
        raise OrderParseError(f"No unit at {supported_origin} to support")

    supported_destination = None
    if len(tokens) == 7:
        if tokens[5] != "-":
            raise OrderParseError(f"Malformed support-move order: {' '.join(tokens)!r}")
        supported_destination = tokens[6]
        if supported_destination not in provinces:
            raise OrderParseError(f"Unknown supported destination {supported_destination!r}")

    supporter_province = provinces[origin]
    target = supported_destination if supported_destination else supported_origin
    if target not in _moves_for(unit.unit_type, supporter_province):
        raise OrderParseError(
            f"{unit.unit_type} at {origin} cannot reach {target} and so cannot support there"
        )

    return SupportOrder(unit, origin, supported_origin, supported_destination)


def _parse_convoy(tokens, unit, origin, units_by_location, provinces):
    # tokens: F Nth C A Lon - Nwy
    if len(tokens) != 7 or tokens[5] != "-":
        raise OrderParseError(f"Malformed convoy order: {' '.join(tokens)!r}")
    if unit.unit_type != "Fleet":
        raise OrderParseError(f"Only fleets may convoy (unit at {origin} is {unit.unit_type})")
    if provinces[origin].kind != "Ocean":
        raise OrderParseError(f"{origin} is not a sea province and cannot convoy")

    convoyed_unit_code, convoyed_origin = tokens[3], tokens[4]
    if convoyed_unit_code != "A":
        raise OrderParseError("Only armies may be convoyed")
    if convoyed_origin not in provinces:
        raise OrderParseError(f"Unknown province {convoyed_origin!r}")
    if convoyed_origin not in units_by_location:
        raise OrderParseError(f"No army at {convoyed_origin} to convoy")

    convoyed_destination = tokens[6]
    if convoyed_destination not in provinces:
        raise OrderParseError(f"Unknown destination {convoyed_destination!r}")

    return ConvoyOrder(unit, origin, convoyed_origin, convoyed_destination)
