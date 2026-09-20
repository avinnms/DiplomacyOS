"""Movement-phase order adjudication.

Implements the standard Diplomacy simultaneous-resolution rules (see
``documentation.txt`` for the prose reference) for a single movement
season: hold, move, support, and convoy orders. Retreats and builds are
out of scope for this milestone -- dislodged units are simply removed
from the board rather than entering a retreat phase.

Known simplifications (see the project plan): no self-dislodgement
prevention, and true multi-unit convoy paradoxes are not resolved --
only the common non-paradox cases (simple bounces, supported moves,
support cuts, head-to-head battles, and basic convoys/convoy
disruption) are guaranteed correct, which is what this milestone's
test suite covers.
"""

import collections

from orders import MoveOrder, SupportOrder, ConvoyOrder


class OrderResult:
    def __init__(self, order, success, reason=""):
        self.order = order
        self.success = success
        self.reason = reason

    def __repr__(self):
        return f"<OrderResult {self.order} success={self.success} reason={self.reason!r}>"


def _unit_moves(unit, provinces):
    province = provinces[unit.location]
    return province.army_moves if unit.unit_type == "Army" else province.navy_moves


def _convoy_path_exists(origin, destination, fleet_locations, provinces):
    """True if some chain of fleets in `fleet_locations` links a sea
    adjacent to `origin` through to a sea adjacent to `destination`."""
    if not fleet_locations:
        return False

    origin_province = provinces[origin]
    frontier = {loc for loc in fleet_locations if loc in origin_province.navy_moves}
    if not frontier:
        return False

    destination_province = provinces[destination]
    visited = set()
    queue = collections.deque(frontier)
    while queue:
        loc = queue.popleft()
        if loc in visited:
            continue
        visited.add(loc)
        if loc in destination_province.navy_moves:
            return True
        for neighbor in provinces[loc].navy_moves:
            if neighbor in fleet_locations and neighbor not in visited:
                queue.append(neighbor)
    return False


def _support_is_cut(support, attempted_moves):
    """A support is cut if some attempted move attacks the supporting
    unit's own province, unless that attack comes from the exact
    province the support is helping to take (the defender fighting
    back does not cut the support against itself)."""
    exception_origin = support.supported_destination
    for mover_origin, mover in attempted_moves.items():
        if mover.destination == support.origin and mover_origin != exception_origin:
            return True
    return False


def adjudicate(orders, provinces, units_by_location):
    """Resolve one simultaneous movement phase.

    ``orders``: dict origin-province -> Order, one per unit on the board.
    ``provinces``: dict province id -> Province.
    ``units_by_location``: dict province id -> Unit, the board before resolution.

    Returns (new_units_by_location, results) where ``results`` is a dict
    origin-province -> OrderResult describing what happened to that order.
    """
    move_orders = {o: order for o, order in orders.items() if isinstance(order, MoveOrder)}
    support_orders = [order for order in orders.values() if isinstance(order, SupportOrder)]
    convoy_orders = [order for order in orders.values() if isinstance(order, ConvoyOrder)]

    dislodged = set()
    attempted_moves = {}
    convoy_fails = {}
    winners = set()

    for _ in range(6):  # outer loop: convoy validity depends on dislodgement, and vice versa
        active_fleet_locations = {c.origin for c in convoy_orders if c.origin not in dislodged}

        next_attempted_moves = {}
        next_convoy_fails = {}
        for origin, order in move_orders.items():
            unit = units_by_location[origin]
            if order.destination in _unit_moves(unit, provinces):
                next_attempted_moves[origin] = order
            elif unit.unit_type == "Army" and _convoy_path_exists(
                origin, order.destination, active_fleet_locations, provinces
            ):
                next_attempted_moves[origin] = order
            else:
                next_convoy_fails[origin] = "no valid convoy route"

        next_winners, next_dislodged = _resolve_movement(
            next_attempted_moves, orders, support_orders, units_by_location, provinces
        )

        stable = next_dislodged == dislodged and next_attempted_moves.keys() == attempted_moves.keys()
        attempted_moves, convoy_fails, winners, dislodged = (
            next_attempted_moves,
            next_convoy_fails,
            next_winners,
            next_dislodged,
        )
        if stable:
            break

    results = {}
    for origin, order in orders.items():
        if isinstance(order, MoveOrder):
            if origin in convoy_fails:
                results[origin] = OrderResult(order, False, convoy_fails[origin])
            elif origin in winners:
                results[origin] = OrderResult(order, True, "move succeeds")
            elif origin in dislodged:
                results[origin] = OrderResult(order, False, "dislodged")
            else:
                results[origin] = OrderResult(order, False, "bounced")
        elif isinstance(order, SupportOrder):
            cut = _support_is_cut(order, attempted_moves) or origin in dislodged
            results[origin] = OrderResult(order, not cut, "support cut" if cut else "support holds")
        elif isinstance(order, ConvoyOrder):
            disrupted = origin in dislodged
            results[origin] = OrderResult(order, not disrupted, "convoy disrupted" if disrupted else "convoy holds")
        else:  # HoldOrder
            results[origin] = OrderResult(order, origin not in dislodged, "dislodged" if origin in dislodged else "holds")

    new_units_by_location = {}
    for origin, order in attempted_moves.items():
        if origin in winners:
            new_units_by_location[order.destination] = units_by_location[origin]
    for loc, unit in units_by_location.items():
        if loc in dislodged or loc in winners:
            continue
        new_units_by_location[loc] = unit

    return new_units_by_location, results


def _resolve_movement(attempted_moves, all_orders, support_orders, units_by_location, provinces):
    """Fixed-point resolution of one set of attempted moves against the
    current board. Returns (winners, dislodged): ``winners`` is the set
    of origin provinces whose move succeeds; ``dislodged`` is the set of
    origin provinces whose original occupant is forced out."""

    cut_supports = {s.origin for s in support_orders if _support_is_cut(s, attempted_moves)}

    def strength(origin, as_move):
        target = all_orders[origin].destination if as_move else None
        count = 0
        for support in support_orders:
            if support.origin in cut_supports:
                continue
            if support.supported_origin == origin and support.supported_destination == target:
                count += 1
        return 1 + count

    winners = set()

    # Head-to-head swaps are resolved directly: each side's move-strength
    # opposes the other, independent of the general "who defends this
    # square" logic below (two units may never simply trade places).
    head_to_head_members = set()
    for origin, order in attempted_moves.items():
        partner = order.destination
        partner_order = attempted_moves.get(partner)
        if partner_order is not None and partner_order.destination == origin and origin < partner:
            s1, s2 = strength(origin, True), strength(partner, True)
            head_to_head_members.add(origin)
            head_to_head_members.add(partner)
            if s1 > s2:
                winners.add(origin)
            elif s2 > s1:
                winners.add(partner)
            # tie: neither wins, both stay in place (bounce)

    winners_from_head_to_head = set(winners)
    remaining_movers = {o: order for o, order in attempted_moves.items() if o not in head_to_head_members}
    stays = {loc for loc in units_by_location if loc not in attempted_moves}

    # A destination's battle can depend on whether ITS OWN occupant (if any)
    # turns out to stay -- which itself depends on a different battle (at
    # that occupant's destination). So re-resolve every contest from
    # scratch each pass until the set of units that end up staying in
    # place stabilizes, rather than trying to patch individual verdicts.
    for _ in range(len(units_by_location) + 2):
        contest = collections.defaultdict(list)
        for origin, order in remaining_movers.items():
            contest[order.destination].append(origin)

        winners = set(winners_from_head_to_head)
        for dest, attacker_origins in contest.items():
            candidates = [(o, strength(o, True)) for o in attacker_origins]
            if dest in stays:
                candidates.append((dest, strength(dest, False)))
            candidates.sort(key=lambda pair: -pair[1])
            top_strength = candidates[0][1]
            top_origins = [o for o, s in candidates if s == top_strength]
            if len(top_origins) == 1 and top_origins[0] != dest:
                winners.add(top_origins[0])

        new_stays = set(stays)
        for origin in remaining_movers:
            if origin not in winners:
                new_stays.add(origin)

        if new_stays == stays:
            break
        stays = new_stays

    dislodged = set()
    for origin, order in attempted_moves.items():
        if origin in winners:
            dest = order.destination
            if dest in units_by_location and dest not in winners:
                dislodged.add(dest)

    return winners, dislodged
