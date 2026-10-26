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


class StartOnNormandy(DefaultOnToggle):
    """After the character creator, a new career skips Lazarus Station and Freedom's Progress and starts aboard the SR-2
    at the galaxy map, with Miranda and Jacob in the squad and the story state those missions give. Their checks are
    removed, and one first-wave dossier is given at the start instead."""

    display_name = "Start on Normandy"


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


class Research(DefaultOnToggle):
    """Buying a research project in the Normandy's tech lab is a check (44 projects; the three suicide-mission ship
    upgrades are items instead). Logic places these after the Collector Ship with every loyalty mission done."""

    display_name = "Research"


class Collectibles(DefaultOnToggle):
    """Captain's cabin purchases (models, fish, the space hamster) and base-game armor pieces are checks. Logic places
    these after the Collector Ship with every loyalty mission done."""

    display_name = "Collectibles"


class Pickups(Choice):
    """Credit caches, resource nodes and upgrade blueprints picked up in missions and hubs are checks (258 with every
    DLC; weapon pickups are not). Most missions cannot be replayed, so a pickup you walk past is gone for good.

    off: no pickups. safe: pickups hold no progression items, so a missed one never blocks the seed. any: pickups can
    hold anything; sweep each mission before leaving it."""

    display_name = "Pickups"
    option_off = 0
    option_safe = 1
    option_any = 2
    default = 1


class Codex(DefaultOnToggle):
    """Codex entries the game unlocks after the start are checks (73: the starting entries are left out, and each
    Paragon/Renegade pair is one check). Some come from optional conversations, so they never hold progression."""

    display_name = "Codex"


class DLCAccess(DefaultOnToggle):
    """DLC missions need an item to open: Project Overlord ("David's Math Test"), Lair of the Shadow Broker ("Shadow
    Broker Toenail", the Illium cab), Arrival ("Batarian Genocide") and Firewalker ("I'm Sorry (Progressive Firewalker
    Mission)", five copies, one per mission in order). Only for DLC in enabled_dlc."""

    display_name = "DLC Access Items"


class ProgressiveLoyalty(DefaultOnToggle):
    """Loyalty missions need a "Progressive Loyalty Mission" item (one copy per squadmate). Each copy opens the loyalty
    mission of the next squadmate, in a fixed order, who is recruited and not yet loyal. The logic expects every copy
    before any loyalty mission, since which mission a copy opens depends on your progress."""

    display_name = "Progressive Loyalty Missions"


class Salvage(DefaultOnToggle):
    """Missed-checks salvage: once you finish a mission that can't be replayed, the Normandy's research terminal offers
    "<mission> Salvage". Each purchase sends one of that mission's pickup checks you left behind. Only matters with
    pickups on."""

    display_name = "Salvage"


class SalvagePrice(Choice):
    """Credits per salvaged check (each purchase at the research terminal sends one missed pickup)."""

    display_name = "Salvage Price per Check"
    option_free = 0
    option_500 = 1
    option_1000 = 2
    option_2500 = 3
    option_5000 = 4
    default = 2


class WeaponUnlocks(DefaultOnToggle):
    """Shuffle weapon unlocks (Carnifex, Mattock, Viper, the heavy weapons...) into the pool as useful items. Receiving
    one unlocks that weapon early; the vanilla pickups and research still work as usual."""

    display_name = "Weapon Unlocks"


class ME1VirmireSurvivor(Choice):
    """ME1 history (the Genesis comic is skipped): who survived Virmire."""

    display_name = "ME1: Virmire Survivor"
    option_ashley = 0
    option_kaidan = 1
    default = 0


class ME1Romance(Choice):
    """ME1 history: Shepard's romance. Ashley needs a male Shepard and Kaidan a female one, each as the Virmire
    survivor; otherwise the client sets none."""

    display_name = "ME1: Romance"
    option_none = 0
    option_ashley = 1
    option_kaidan = 2
    option_liara = 3
    default = 0


class ME1Rachni(Choice):
    """ME1 history: the Rachni Queen's fate."""

    display_name = "ME1: Rachni Queen"
    option_saved = 0
    option_killed = 1
    default = 0


class ME1Wrex(Choice):
    """ME1 history: Wrex on Virmire."""

    display_name = "ME1: Wrex"
    option_alive = 0
    option_dead = 1
    default = 0


class ME1Council(Choice):
    """ME1 history: the Council at the Battle of the Citadel."""

    display_name = "ME1: Council"
    option_saved = 0
    option_sacrificed = 1
    default = 0


class ME1HumanCouncilor(Choice):
    """ME1 history: humanity's councilor."""

    display_name = "ME1: Human Councilor"
    option_anderson = 0
    option_udina = 1
    default = 0


@dataclass
class MassEffectLE2Options(PerGameCommonOptions):
    intel_total: IntelTotal
    intel_required: IntelRequired
    endgame_readiness: EndgameReadiness
    start_on_normandy: StartOnNormandy
    assignments: Assignments
    enabled_dlc: EnabledDLC
    research: Research
    collectibles: Collectibles
    pickups: Pickups
    codex: Codex
    dlc_access: DLCAccess
    progressive_loyalty: ProgressiveLoyalty
    salvage: Salvage
    salvage_price: SalvagePrice
    weapon_unlocks: WeaponUnlocks
    me1_virmire_survivor: ME1VirmireSurvivor
    me1_romance: ME1Romance
    me1_rachni: ME1Rachni
    me1_wrex: ME1Wrex
    me1_council: ME1Council
    me1_human_councilor: ME1HumanCouncilor


options_presets = {
    "Story Focus": {
        "assignments": "off",
        "research": False,
        "collectibles": False,
        "pickups": "off",
        "intel_total": 3,
        "intel_required": 2,
    },
    "Completionist": {
        "assignments": "all",
        "pickups": "any",
        "intel_total": 8,
        "intel_required": 6,
    },
}

option_groups = [
    OptionGroup("Goal", [IntelTotal, IntelRequired, EndgameReadiness]),
    OptionGroup("Start", [StartOnNormandy]),
    OptionGroup("Checks", [Assignments, Research, Collectibles, Pickups, Codex, DLCAccess, ProgressiveLoyalty, Salvage, SalvagePrice, EnabledDLC]),
    OptionGroup("Items", [WeaponUnlocks]),
    OptionGroup("ME1 History", [ME1VirmireSurvivor, ME1Romance, ME1Rachni, ME1Wrex, ME1Council, ME1HumanCouncilor]),
]
