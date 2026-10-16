from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Item, LocationProgressType

from . import data

if TYPE_CHECKING:
    from .world import MassEffectLE2World


class MassEffectLE2Item(Item):
    game = data.GAME_NAME


def dlc_enabled(world: MassEffectLE2World, key: str | None) -> bool:
    return key is None or key in world.options.enabled_dlc.value


DLC_DOSSIERS = {data.DOSSIERS["Zaeed Massani"]: "Zaeed", data.DOSSIERS["Kasumi Goto"]: "Kasumi"}


def create_item(world: MassEffectLE2World, name: str) -> MassEffectLE2Item:
    return MassEffectLE2Item(name, data.ITEMS[name].classification, data.ITEM_NAME_TO_ID[name], world.player)


def create_items(world: MassEffectLE2World) -> None:
    pool: list[MassEffectLE2Item] = []
    for name, item in data.ITEMS.items():
        if name in DLC_DOSSIERS and not dlc_enabled(world, DLC_DOSSIERS[name]):
            continue
        count = item.count - (name == world.starting_dossier)
        pool += [create_item(world, name) for _ in range(count)]
    pool += [create_item(world, data.IFF_INTEL) for _ in range(world.options.intel_total.value)]

    unfilled = world.multiworld.get_unfilled_locations(world.player)
    if len(pool) > len(unfilled):
        # generate_early already guarantees room; this guards future table edits
        raise RuntimeError(f"{data.GAME_NAME}: {len(pool)} items for {len(unfilled)} locations")

    # Weapons are useful: they cannot go to excluded locations, which keep that many filler slots.
    excluded = sum(1 for loc in unfilled if loc.progress_type == LocationProgressType.EXCLUDED)
    if world.options.weapon_unlocks:
        weapons = list(data.WEAPONS)
        world.random.shuffle(weapons)
        room = max(0, len(unfilled) - excluded - len(pool))
        pool += [create_item(world, name) for name in weapons[:room]]

    pool += [create_item(world, world.get_filler_item_name()) for _ in range(len(unfilled) - len(pool))]
    world.multiworld.itempool += pool
