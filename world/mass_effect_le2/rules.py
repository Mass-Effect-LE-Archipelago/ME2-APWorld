from __future__ import annotations

from typing import TYPE_CHECKING

from rule_builder.rules import Has, HasAll, HasAny, Rule

from . import data
from .regions import location_included, squad

if TYPE_CHECKING:
    from .world import MassEffectLE2World


def check_rule(loc: data.LocationData) -> Rule | None:
    rule: Rule | None = None
    if loc.needs:
        rule = HasAll(*loc.needs) if len(loc.needs) > 1 else Has(loc.needs[0])
    if loc.any_of:
        extra = HasAny(*loc.any_of)
        rule = extra if rule is None else rule & extra
    return rule


def dlc_access_rule(world: MassEffectLE2World, name: str, loc: data.LocationData) -> Rule | None:
    """D25: a DLC location also needs its DLC's access item (Firewalker: as many copies as its mission's place)."""
    if not world.options.dlc_access or loc.dlc is None:
        return None
    if loc.dlc in data.DLC_ACCESS_ITEMS:
        return Has(data.DLC_ACCESS_ITEMS[loc.dlc])
    if loc.dlc == "Firewalker":
        return Has(data.FIREWALKER_ITEM, data.firewalker_copies(name))
    return None


def set_rules(world: MassEffectLE2World) -> None:
    # Entrance rules are set when regions are created (regions.ENTRANCES).
    for name, loc in data.LOCATIONS.items():
        if not location_included(world, loc):
            continue
        rule = check_rule(loc)
        if (access := dlc_access_rule(world, name, loc)) is not None:
            rule = access if rule is None else rule & access
        if rule is not None:
            world.set_rule(world.get_location(name), rule)

    # Events share their check's rule: an event is "the player did this", the check is "the client sent it".
    for member in squad(world):
        if member in data.RECRUIT_LOCATION and (
                rule := check_rule(data.LOCATIONS[data.RECRUIT_LOCATION[member]])) is not None:
            world.set_rule(world.get_location(data.recruited(member)), rule)
        if (rule := check_rule(data.LOCATIONS[data.LOYALTY_LOCATION[member]])) is not None:
            world.set_rule(world.get_location(data.loyalty_done(member)), rule)

    if world.options.endgame_readiness == world.options.endgame_readiness.option_all_loyal:
        world.set_rule(world.get_location(data.EVENT_VICTORY), HasAll(*(data.loyalty_done(m) for m in squad(world))))
    world.set_completion_rule(Has(data.EVENT_VICTORY))
