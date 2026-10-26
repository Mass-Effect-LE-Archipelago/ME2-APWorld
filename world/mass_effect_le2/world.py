from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, ClassVar

from worlds.AutoWorld import World

from . import data, items, regions, rules, web_world
from . import options as me_options  # renamed: World.options is an attribute

logger = logging.getLogger(__name__)

# Spare non-excluded slots kept when clamping intel_total (LE1 precedent: an all-progression pool made restrictive fill
# fail on a few seeds; generation tests in test/test_generation.py exercise the option boundaries).
MIN_FILLER_SLOTS = 4


class MassEffectLE2World(World):
    """
    Shepard wakes on Lazarus Station and takes command of the Normandy SR-2. Dossiers, ship upgrades and Reaper IFF
    intel are scattered across the multiworld: recruit the team, earn their loyalty and stop the Collectors.
    """

    game = data.GAME_NAME
    web = web_world.MassEffectLE2WebWorld()
    options_dataclass = me_options.MassEffectLE2Options
    options: me_options.MassEffectLE2Options
    origin_region_name = data.Region.NORMANDY.value

    item_name_to_id: ClassVar[dict[str, int]] = data.ITEM_NAME_TO_ID
    location_name_to_id: ClassVar[dict[str, int]] = data.LOCATION_NAME_TO_ID
    item_name_groups = data.ITEM_NAME_GROUPS
    location_name_groups = data.LOCATION_NAME_GROUPS

    intel_required: int
    starting_dossier: str | None = None

    def generate_early(self) -> None:
        # Skipping the prologue also skips its two checks, the only ones open at the start: one first-wave dossier is
        # given at the start instead, so the seed always has somewhere to begin.
        if self.options.start_on_normandy:
            self.starting_dossier = data.DOSSIERS[self.random.choice(data.PHASE_1)]
            self.multiworld.push_precollected(self.create_item(self.starting_dossier))
        # slots that can hold progression: not excluded, and not a pickup under pickups: safe
        safe = self.options.pickups == self.options.pickups.option_safe
        open_slots = sum(1 for loc in data.LOCATIONS.values() if regions.location_included(self, loc)
                         and not loc.excluded and not (safe and loc.category == "pickup") and loc.category != "codex")
        fixed = sum(1 for name, item in data.ITEMS.items() if item.count
                    and (name not in items.DLC_DOSSIERS or items.dlc_enabled(self, items.DLC_DOSSIERS[name])))
        room = open_slots - fixed + (self.starting_dossier is not None) - MIN_FILLER_SLOTS
        total = self.options.intel_total
        if total.value > room:
            logger.warning(f"{self.player_name}: intel_total {total.value} lowered to {room} (location count).")
            total.value = max(1, room)
        required = self.options.intel_required
        if required.value > total.value:
            logger.warning(f"{self.player_name}: intel_required {required.value} lowered to {total.value}.")
            required.value = total.value
        self.intel_required = required.value

    def create_regions(self) -> None:
        regions.create_regions(self)

    def create_items(self) -> None:
        items.create_items(self)

    def create_item(self, name: str) -> items.MassEffectLE2Item:
        return items.create_item(self, name)

    def get_filler_item_name(self) -> str:
        return self.random.choice(data.FILLER)

    def set_rules(self) -> None:
        rules.set_rules(self)

    def fill_slot_data(self) -> Mapping[str, Any]:
        return {
            **self.options.as_dict("intel_total", "intel_required", "endgame_readiness", "start_on_normandy", "assignments",
                                 "research", "collectibles", "pickups", "codex", "salvage", "salvage_price", "weapon_unlocks"),
            "enabled_dlc": sorted(self.options.enabled_dlc.value),
            "starting_dossier": self.starting_dossier,
            "me1_history": {key: getattr(self.options, key).current_key for key in data.ME1_HISTORY},
            "slot_data_version": 1,
        }
