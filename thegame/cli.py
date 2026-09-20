"""Hotseat terminal interface for a single Diplomacy movement phase.

All seven great powers are played by humans taking turns at the same
terminal. Each power enters one order per unit it owns; once everyone
has submitted, all orders are adjudicated simultaneously and the
results are printed.
"""

from adjudicator import adjudicate
from orders import OrderParseError, parse_order
from persistence import save_game

ORDER_HELP = """\
Order notation:
  A Par H              hold
  A Par - Bur          move
  F Bre S A Par        support a hold
  F Bre S A Par - Bur  support a move
  F Nth C A Lon - Nwy  convoy an army
"""


def print_board(gamestate, provinces):
    print(f"\n{gamestate.season} {gamestate.year} -- {gamestate.phase} phase")
    for power in gamestate.powers:
        units = [
            f"{unit.unit_type[0]} {loc} ({provinces[loc].full})"
            for loc, unit in sorted(gamestate.units.items())
            if unit.owner == power
        ]
        if units:
            print(f"  {power}: " + ", ".join(units))


def collect_orders(gamestate, provinces):
    orders = {}
    for power in gamestate.powers:
        owned_locations = sorted(loc for loc, unit in gamestate.units.items() if unit.owner == power)
        if not owned_locations:
            continue
        print(f"\n-- {power}'s orders --")
        print(ORDER_HELP)
        for loc in owned_locations:
            unit = gamestate.units[loc]
            while True:
                text = input(f"  {unit.unit_type} {loc}> ").strip()
                try:
                    order = parse_order(text, gamestate.units, provinces)
                except OrderParseError as exc:
                    print(f"    {exc}")
                    continue
                if order.origin != loc:
                    print("    That order isn't for this unit.")
                    continue
                orders[loc] = order
                break
    return orders


def print_results(results, provinces):
    print("\n-- Results --")
    for origin in sorted(results):
        result = results[origin]
        status = "OK" if result.success else "FAILED"
        print(f"  {result.order} [{status}] {result.reason}")


def run_game(gamestate, provinces, save_path=None):
    print_board(gamestate, provinces)
    orders = collect_orders(gamestate, provinces)
    new_units, results = adjudicate(orders, provinces, gamestate.units)
    gamestate.apply_adjudication(new_units)
    print_results(results, provinces)
    print_board(gamestate, provinces)

    if save_path:
        answer = input(f"\nSave game to {save_path}? [y/N] ").strip().lower()
        if answer == "y":
            save_game(gamestate, save_path)
            print(f"Saved to {save_path}")
