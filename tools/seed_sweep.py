"""Long seed sweep: every seed of each option set must fill completely and be beatable.

usage (from an Archipelago checkout with worlds/mass_effect_le2): python <repo>/tools/seed_sweep.py [seeds] [set ...]
Sets: default (all defaults), max (every check family on, all DLC, pickups any). Prints failures and a summary.
"""
import sys
import time

import ModuleUpdate

ModuleUpdate.update_ran = True  # don't prompt to install other worlds' requirements (as the test runner)

from worlds.mass_effect_le2.world import MassEffectLE2World  # load the worlds first (Fill imports them)
from Fill import distribute_items_restrictive  # noqa: E402
from test.general import gen_steps, setup_multiworld  # noqa: E402

OPTION_SETS = {
    "default": {},
    "max": {"assignments": "all", "research": True, "collectibles": True, "pickups": "any", "codex": True,
            "enabled_dlc": ["Kasumi", "Zaeed", "Overlord", "Shadow Broker", "Arrival", "Firewalker", "Normandy Crash Site"]},
}


def main() -> int:
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    names = sys.argv[2:] or list(OPTION_SETS)
    failures = 0
    for name in names:
        start, bad = time.time(), []
        for seed in range(seeds):
            try:
                multiworld = setup_multiworld(MassEffectLE2World, gen_steps, seed, OPTION_SETS[name])
                distribute_items_restrictive(multiworld)
                if not multiworld.can_beat_game(multiworld.state) or multiworld.get_unfilled_locations():
                    bad.append(seed)
            except Exception as error:  # a crash is a failure too
                bad.append(f"{seed}:{type(error).__name__}")
        failures += len(bad)
        print(f"{name}: {seeds - len(bad)}/{seeds} ok in {time.time() - start:.0f}s" + (f"; failed {bad[:20]}" if bad else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
