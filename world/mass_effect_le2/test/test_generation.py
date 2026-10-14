"""Seed sweeps across option boundaries: every seed must fill and be beatable (LE1 lesson: tight progression pools
fail restrictive fill on a few seeds in hundreds, so one default seed proves little)."""
import unittest

from Fill import distribute_items_restrictive
from test.general import gen_steps, setup_multiworld

from ..world import MassEffectLE2World

SEEDS = 40  # per option set here; tools/seed_sweep.py runs the long sweep
OPTION_SETS = (
    {},
    {"assignments": "off", "enabled_dlc": [], "research": False, "collectibles": False, "intel_total": 10,
     "intel_required": 10, "weapon_unlocks": False},
    {"assignments": "off", "enabled_dlc": [], "research": False, "collectibles": False, "intel_total": 1,
     "intel_required": 1},
    {"assignments": "all", "endgame_readiness": "ship_upgrades"},
    {"assignments": "n7", "enabled_dlc": ["Kasumi"], "intel_total": 10, "intel_required": 7},
    {"assignments": "off", "enabled_dlc": [], "research": False, "collectibles": False, "pickups": "any",
     "intel_total": 10, "intel_required": 10},
    {"assignments": "all", "pickups": "off", "weapon_unlocks": False},
)


class TestSeedSweep(unittest.TestCase):
    def test_option_sets_fill_and_beat(self) -> None:
        for options in OPTION_SETS:
            for seed in range(SEEDS):
                with self.subTest(options=options, seed=seed):
                    multiworld = setup_multiworld(MassEffectLE2World, gen_steps, seed, options)
                    distribute_items_restrictive(multiworld)
                    self.assertTrue(multiworld.can_beat_game(multiworld.state), f"seed {seed} not beatable")
                    self.assertFalse(multiworld.get_unfilled_locations(), f"seed {seed} left locations empty")
