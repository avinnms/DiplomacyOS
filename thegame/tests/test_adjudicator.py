import json
import os

import pytest

from adjudicator import adjudicate
from orders import parse_order
from province import load_provinces
from unit import Unit

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def provinces():
    with open(os.path.join(BASE_DIR, "provincedb.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    return load_provinces(data)


def make_units(placements):
    """placements: dict location -> (unit_type, owner)"""
    return {loc: Unit(unit_type, owner, loc) for loc, (unit_type, owner) in placements.items()}


def orders_from(texts, units, provinces):
    orders = {}
    for text in texts:
        order = parse_order(text, units, provinces)
        orders[order.origin] = order
    return orders


def test_simple_unopposed_move(provinces):
    units = make_units({"Par": ("Army", "France")})
    orders = orders_from(["A Par - Bur"], units, provinces)

    new_units, results = adjudicate(orders, provinces, units)

    assert "Bur" in new_units and new_units["Bur"].owner == "France"
    assert "Par" not in new_units
    assert results["Par"].success is True


def test_simple_hold(provinces):
    units = make_units({"Par": ("Army", "France")})
    orders = orders_from(["A Par H"], units, provinces)

    new_units, results = adjudicate(orders, provinces, units)

    assert new_units["Par"] is units["Par"]
    assert results["Par"].success is True


def test_bounce_no_support(provinces):
    units = make_units({"Bur": ("Army", "France"), "Kie": ("Army", "Germany")})
    orders = orders_from(["A Bur - Mun", "A Kie - Mun"], units, provinces)

    new_units, results = adjudicate(orders, provinces, units)

    assert "Mun" not in new_units
    assert new_units["Bur"].owner == "France"
    assert new_units["Kie"].owner == "Germany"
    assert results["Bur"].success is False and results["Bur"].reason == "bounced"
    assert results["Kie"].success is False and results["Kie"].reason == "bounced"


def test_supported_move_beats_unsupported(provinces):
    units = make_units({
        "Bur": ("Army", "France"),
        "Ruh": ("Army", "France"),
        "Sil": ("Army", "Germany"),
    })
    orders = orders_from(
        ["A Bur - Mun", "A Ruh S A Bur - Mun", "A Sil - Mun"], units, provinces
    )

    new_units, results = adjudicate(orders, provinces, units)

    assert new_units["Mun"].owner == "France"
    assert results["Bur"].success is True
    assert results["Sil"].success is False and results["Sil"].reason == "bounced"
    # The unsupported attacker stays put rather than being dislodged.
    assert new_units["Sil"].owner == "Germany"


def test_support_is_cut_by_attack_on_supporter(provinces):
    units = make_units({
        "Bur": ("Army", "France"),
        "Ruh": ("Army", "France"),
        "Sil": ("Army", "Germany"),
        "Hol": ("Army", "Germany"),
    })
    orders = orders_from(
        [
            "A Bur - Mun",
            "A Ruh S A Bur - Mun",
            "A Sil - Mun",
            "A Hol - Ruh",
        ],
        units,
        provinces,
    )

    new_units, results = adjudicate(orders, provinces, units)

    assert results["Ruh"].success is False and results["Ruh"].reason == "support cut"
    # With the support cut, Bur (1) and Sil (1) tie for Mun -- both bounce.
    assert "Mun" not in new_units
    assert results["Bur"].success is False and results["Bur"].reason == "bounced"
    assert results["Sil"].success is False and results["Sil"].reason == "bounced"
    # Hol's attack on Ruh itself also bounces (Ruh defends with strength 1).
    assert results["Hol"].success is False and results["Hol"].reason == "bounced"
    assert new_units["Ruh"].owner == "France"


def test_head_to_head_bounce(provinces):
    units = make_units({"Bur": ("Army", "France"), "Mun": ("Army", "Germany")})
    orders = orders_from(["A Bur - Mun", "A Mun - Bur"], units, provinces)

    new_units, results = adjudicate(orders, provinces, units)

    assert results["Bur"].success is False
    assert results["Mun"].success is False
    assert new_units["Bur"].owner == "France"
    assert new_units["Mun"].owner == "Germany"


def test_head_to_head_supported_side_wins_and_dislodges(provinces):
    units = make_units({
        "Bur": ("Army", "France"),
        "Ruh": ("Army", "France"),
        "Mun": ("Army", "Germany"),
    })
    orders = orders_from(
        ["A Bur - Mun", "A Ruh S A Bur - Mun", "A Mun - Bur"], units, provinces
    )

    new_units, results = adjudicate(orders, provinces, units)

    assert results["Bur"].success is True
    assert results["Mun"].success is False and results["Mun"].reason == "dislodged"
    assert new_units["Mun"].owner == "France"
    assert "Bur" not in new_units  # the dislodged German unit is removed, not swapped in


def test_convoy_success(provinces):
    units = make_units({"Lon": ("Army", "England"), "Nth": ("Fleet", "England")})
    orders = orders_from(["A Lon - Nwy", "F Nth C A Lon - Nwy"], units, provinces)

    new_units, results = adjudicate(orders, provinces, units)

    assert results["Lon"].success is True
    assert new_units["Nwy"].owner == "England"
    assert "Lon" not in new_units
    assert new_units["Nth"].owner == "England"  # the convoying fleet stays put


def test_convoy_disrupted_by_dislodged_fleet(provinces):
    units = make_units({
        "Lon": ("Army", "England"),
        "Nth": ("Fleet", "England"),
        "Hel": ("Fleet", "Germany"),
        "Den": ("Fleet", "Germany"),
    })
    orders = orders_from(
        [
            "A Lon - Nwy",
            "F Nth C A Lon - Nwy",
            "F Hel - Nth",
            "F Den S F Hel - Nth",
        ],
        units,
        provinces,
    )

    new_units, results = adjudicate(orders, provinces, units)

    assert results["Lon"].success is False and results["Lon"].reason == "no valid convoy route"
    assert new_units["Lon"].owner == "England"  # army never left, convoy failed
    assert results["Hel"].success is True
    assert new_units["Nth"].owner == "Germany"  # Hel's fleet dislodged the convoying fleet
