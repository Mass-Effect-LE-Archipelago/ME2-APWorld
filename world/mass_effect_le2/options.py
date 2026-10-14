from dataclasses import dataclass

from Options import Choice, DefaultOnToggle, OptionGroup, OptionSet, PerGameCommonOptions, Range

from .data import DLC_KEYS


class IntelTotal(Range):
    """How many Reaper IFF Intel items are shuffled into the item pool."""

    display_name = "Reaper IFF Intel in Pool"
    range_start = 1
    range_end = 10
    default = 5


class IntelRequired(Range):
    """How many Reaper IFF Intel items open the Derelict Reaper mission (after the Collector Ship). Lowered to the pool
    size if it is larger."""

    display_name = "Reaper IFF Intel Required"
    range_start = 1
    range_end = 10
    default = 3


class EndgameReadiness(Choice):
    """What logic expects before the Omega 4 Relay, so a successful suicide mission is always possible.

    all_loyal: the three Normandy upgrades, and every loyalty mission of every squadmate recruitable in this seed.
    ship_upgrades: the three Normandy upgrades only. Choosing specialists well is up to you."""

    display_name = "Endgame Readiness"
    option_all_loyal = 0
    option_ship_upgrades = 1
    default = 0


class Assignments(Choice):
    """Which side assignments are checks.

    off: none. n7: the N7 assignments found by scanning planets. all: also hub assignments on Omega, the Citadel,
    Illium and Tuchanka, and the Normandy's own tasks."""

    display_name = "Assignments"
    option_off = 0
    option_n7 = 1
    option_all = 2
    default = 1


class EnabledDLC(OptionSet):
    """DLC content that adds checks (and, for Kasumi and Zaeed, their dossiers and loyalty missions). Remove what you do
    not want to play; Legendary Edition includes all of it."""

    display_name = "Enabled DLC"
    valid_keys = frozenset(DLC_KEYS)
    default = frozenset(DLC_KEYS)


class WeaponUnlocks(DefaultOnToggle):
    """Shuffle weapon unlocks (Carnifex, Mattock, Viper, the heavy weapons...) into the pool as useful items. Receiving
    one unlocks that weapon early; the vanilla pickups and research still work as usual."""

    display_name = "Weapon Unlocks"


@dataclass
class MassEffectLE2Options(PerGameCommonOptions):
    intel_total: IntelTotal
    intel_required: IntelRequired
    endgame_readiness: EndgameReadiness
    assignments: Assignments
    enabled_dlc: EnabledDLC
    weapon_unlocks: WeaponUnlocks


options_presets = {
    "Story Focus": {
        "assignments": "off",
        "intel_total": 3,
        "intel_required": 2,
    },
    "Completionist": {
        "assignments": "all",
        "intel_total": 8,
        "intel_required": 6,
    },
}

option_groups = [
    OptionGroup("Goal", [IntelTotal, IntelRequired, EndgameReadiness]),
    OptionGroup("Checks", [Assignments, EnabledDLC]),
    OptionGroup("Items", [WeaponUnlocks]),
]
