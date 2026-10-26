from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Item, ItemClassification, Location, LocationProgressType, Region
from rule_builder.field_resolvers import FromWorldAttr
from rule_builder.rules import Has, HasAll, HasAny, Rule, True_

from . import data
from .data import Region as R, recruited
from .items import MassEffectLE2Item, dlc_enabled

if TYPE_CHECKING:
    from .world import MassEffectLE2World


class MassEffectLE2Location(Location):
    game = data.GAME_NAME


HAS_HORIZON: Rule = Has(data.EVENT_HORIZON)
HAS_INTEL: Rule = Has(data.IFF_INTEL, count=FromWorldAttr("intel_required"))
HAS_SHIP_UPGRADES: Rule = HasAll(*data.SHIP_UPGRADES)

# Galaxy-map entrances from the Normandy. Story order stays vanilla (D3); the rules are conservative, never looser than
# the game's own triggers as far as they are known (D7, research items in docs/SCOPE.md).
ENTRANCES: dict[R, Rule] = {
    R.OMEGA: True_(),
    R.CITADEL: True_(),
    R.PURGATORY: Has(data.DOSSIERS["Jack"]),
    R.KORLUS: Has(data.DOSSIERS["Grunt"]),
    # Horizon follows Mordin's recruitment in vanilla; logic waits for the whole first dossier wave.
    R.HORIZON: HasAll(*(recruited(name) for name in data.PHASE_1)),
    R.ILLIUM: HAS_HORIZON,  # the second dossier wave (Thane, Samara) arrives after Horizon
    R.HAESTROM: HAS_HORIZON & Has(data.DOSSIERS["Tali'Zorah vas Neema"]),
    R.TUCHANKA: HAS_HORIZON & HasAny(recruited("Grunt"), recruited("Mordin Solus")),  # opened by either loyalty request
    R.COLLECTOR_SHIP: HAS_HORIZON & HasAll(*(recruited(name) for name in data.PHASE_2)),
    R.DERELICT_REAPER: Has(data.EVENT_COLLECTOR_SHIP) & HAS_INTEL,  # D6: the AP endgame key
    R.LOYALTY: True_(),  # each loyalty mission carries its own rule
    R.UNCHARTED: True_(),
    R.DLC: True_(),
    R.COLLECTOR_BASE: Has(data.EVENT_IFF) & HAS_SHIP_UPGRADES,  # plus the readiness rule (rules.py)
}


def location_included(world: MassEffectLE2World, loc: data.LocationData) -> bool:
    if not dlc_enabled(world, loc.dlc):
        return False
    if loc.prologue and world.options.start_on_normandy:
        return False
    if loc.category == "n7":
        return world.options.assignments.value >= world.options.assignments.option_n7
    if loc.category == "hub":
        return world.options.assignments.value == world.options.assignments.option_all
    if loc.category == "research":
        return bool(world.options.research)
    if loc.category == "collectible":
        return bool(world.options.collectibles)
    if loc.category == "pickup":
        return world.options.pickups.value != world.options.pickups.option_off
    if loc.category == "codex":
        return bool(world.options.codex)
    return True


def squad(world: MassEffectLE2World) -> list[str]:
    """Squadmates in this seed: everyone whose recruitment or loyalty can happen before Omega 4."""
    members = list(data.STARTING_SQUAD) + list(data.PHASE_1) + list(data.PHASE_2) + ["Legion"]
    members += [name for name, key in zip(data.DLC_SQUAD, ("Zaeed", "Kasumi")) if dlc_enabled(world, key)]
    return members


def create_regions(world: MassEffectLE2World) -> None:
    regions = {r: Region(r.value, world.player, world.multiworld) for r in R}
    world.multiworld.regions += regions.values()

    normandy = regions[R.NORMANDY]
    for target, rule in ENTRANCES.items():
        world.create_entrance(normandy, regions[target], rule, name=f"Galaxy Map -> {target.value}")
    # D16: the late game waits for the Collector Ship and every loyalty mission that can happen before the IFF.
    late = Has(data.EVENT_COLLECTOR_SHIP) & HasAll(*(data.loyalty_done(m) for m in squad(world) if m != "Legion"))
    world.create_entrance(normandy, regions[R.LATE_GAME], late, name=f"Normandy -> {R.LATE_GAME.value}")

    for name, loc in data.LOCATIONS.items():
        if not location_included(world, loc):
            continue
        location = MassEffectLE2Location(world.player, name, data.LOCATION_NAME_TO_ID[name], regions[loc.region])
        if loc.excluded:
            location.progress_type = LocationProgressType.EXCLUDED
        elif (loc.category == "pickup" and world.options.pickups == world.options.pickups.option_safe) \
                or loc.category == "codex":  # codex pages can come from optional conversations
            location.item_rule = _not_progression
        regions[loc.region].locations.append(location)

    # Events mirror the checks the logic depends on (rules.py gives them the same rule as their check).
    for member in squad(world):
        if member in data.RECRUIT_LOCATION:
            check = data.LOCATIONS[data.RECRUIT_LOCATION[member]]
            _add_event(world, regions[check.region], recruited(member))
        check = data.LOCATIONS[data.LOYALTY_LOCATION[member]]
        _add_event(world, regions[check.region], data.loyalty_done(member))
    _add_event(world, regions[R.HORIZON], data.EVENT_HORIZON)
    _add_event(world, regions[R.COLLECTOR_SHIP], data.EVENT_COLLECTOR_SHIP)
    _add_event(world, regions[R.DERELICT_REAPER], data.EVENT_IFF)
    _add_event(world, regions[R.COLLECTOR_BASE], data.EVENT_VICTORY)


def _not_progression(item: Item) -> bool:
    return not item.advancement


def _add_event(world: MassEffectLE2World, region: Region, name: str) -> None:
    location = MassEffectLE2Location(world.player, name, None, region)
    location.place_locked_item(MassEffectLE2Item(name, ItemClassification.progression, None, world.player))
    region.locations.append(location)
