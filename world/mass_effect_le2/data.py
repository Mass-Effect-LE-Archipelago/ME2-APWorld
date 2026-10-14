"""Static tables for the Mass Effect 2 (LE2) world.

IDs are an append-only ledger (docs/DECISIONS.md D1): never renumber or reuse an ID, only add new ones.

`plot` fields are check predicates the client evaluates through the LE2APBridge ("bool N", "bool A or B",
"int N >= V"). They come from Trilogy Save Editor's `me2_plot_db.ron` (cross-checked against Legendary Explorer's
embedded `le2.json` where docs/CHECKS-CATALOG.md says so). Generation never reads them. Every predicate is a candidate
until a live LE2 test confirms it (CHECKS-CATALOG.md "status").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from BaseClasses import ItemClassification

ID_BASE = 0x4D32_0000  # "M2": deliberately not LE1's 0x4D45_0000 (feasibility plan, "Runtime contract")
# Offsets inside ID_BASE: items 0x0000-0x0FFF, locations 0x1000-0x7FFF:
#   0x1000 prologue and story, 0x1100 recruitment, 0x1200 loyalty, 0x1300 Collector Base, 0x1400 N7 assignments,
#   0x1500 hub assignments, 0x1600 DLC missions.
GAME_NAME = "Mass Effect Legendary Edition 2"


class Region(str, Enum):
    NORMANDY = "Normandy"  # origin: the prologue is played as normal and ends aboard the SR-2
    OMEGA = "Omega"
    CITADEL = "Citadel"
    ILLIUM = "Illium"
    TUCHANKA = "Tuchanka"
    PURGATORY = "Purgatory"  # Jack
    KORLUS = "Korlus"  # Grunt
    HAESTROM = "Haestrom"  # Tali
    HORIZON = "Horizon"
    COLLECTOR_SHIP = "Collector Ship"
    DERELICT_REAPER = "Derelict Reaper"
    LOYALTY = "Loyalty Missions"  # each loyalty mission is its own world; rules carry the per-character gate
    UNCHARTED = "Uncharted Worlds"  # N7 assignments
    DLC = "DLC Missions"
    COLLECTOR_BASE = "Collector Base"


@dataclass(frozen=True)
class ItemData:
    offset: int
    classification: ItemClassification
    count: int = 1  # copies in the pool; option-driven items use 0 and are added by items.create_items
    groups: frozenset[str] = field(default_factory=frozenset)
    grant: str | None = None  # client delivery op (client.py GRANTS); None = counted by the client only


_P = ItemClassification.progression
_U = ItemClassification.useful
_F = ItemClassification.filler

# Mission access (D4): each dossier opens one recruitment mission's galaxy-map destination (mod bool 21000 + offset).
DOSSIERS = {
    "Mordin Solus": "Dossier: The Professor",
    "Garrus Vakarian": "Dossier: Archangel",
    "Jack": "Dossier: The Convict",
    "Grunt": "Dossier: The Warlord",
    "Thane Krios": "Dossier: The Assassin",
    "Samara": "Dossier: The Justicar",
    "Tali'Zorah vas Neema": "Dossier: Tali",
    "Zaeed Massani": "Dossier: Zaeed Massani",
    "Kasumi Goto": "Dossier: Kasumi Goto",
}
PHASE_1 = ("Mordin Solus", "Garrus Vakarian", "Jack", "Grunt")
PHASE_2 = ("Thane Krios", "Samara", "Tali'Zorah vas Neema")
DLC_SQUAD = ("Zaeed Massani", "Kasumi Goto")
STARTING_SQUAD = ("Miranda Lawson", "Jacob Taylor")

SHIP_UPGRADES = ("Heavy Ship Armor", "Multicore Shielding", "Thanix Cannon")  # the three suicide-mission upgrades
IFF_INTEL = "Reaper IFF Intel"  # endgame key (D6): enough of these opens the Derelict Reaper
FILLER = ("Credits", "Element Zero", "Iridium", "Palladium", "Platinum")

# Weapon unlocks: plot int that the armory reads (me2_plot_db "research_upgrades/Weapons"), set to 1 (D8, unverified).
WEAPONS = {
    "M-6 Carnifex": 149,
    "M-5 Phalanx": 854,
    "M-9 Tempest": 124,
    "M-12 Locust": 725,
    "M-15 Vindicator": 152,
    "M-96 Mattock": 852,
    "Geth Pulse Rifle": 495,
    "M-27 Scimitar": 88,
    "M-22 Eviscerator": 847,
    "Geth Plasma Shotgun": 853,
    "M-97 Viper": 177,
    "M-29 Incisor": 855,
    "M-100 Grenade Launcher": 151,
    "ML-77 Missile Launcher": 460,
    "M-451 Firestorm": 663,
    "M-622 Avalanche": 461,
    "M-920 Cain": 496,
}

ITEMS: dict[str, ItemData] = {
    # 0x00-0x1F dossiers (mission access)
    **{name: ItemData(i, _P, groups=frozenset({"Dossiers"}), grant="access")
       for i, name in enumerate(DOSSIERS.values())},
    # 0x20-0x2F Normandy upgrades: progression for the Omega 4 readiness rule
    "Heavy Ship Armor": ItemData(0x20, _P, groups=frozenset({"Ship Upgrades"}), grant="ship"),
    "Multicore Shielding": ItemData(0x21, _P, groups=frozenset({"Ship Upgrades"}), grant="ship"),
    "Thanix Cannon": ItemData(0x22, _P, groups=frozenset({"Ship Upgrades"}), grant="ship"),
    # 0x30 endgame key, counted by option
    IFF_INTEL: ItemData(0x30, ItemClassification.progression_skip_balancing, count=0),
    # 0x40-0x4F filler (resource bundles)
    "Credits": ItemData(0x40, _F, count=0, grant="resource"),
    "Element Zero": ItemData(0x41, _F, count=0, grant="resource"),
    "Iridium": ItemData(0x42, _F, count=0, grant="resource"),
    "Palladium": ItemData(0x43, _F, count=0, grant="resource"),
    "Platinum": ItemData(0x44, _F, count=0, grant="resource"),
    # 0x100-0x1FF weapon unlocks (weapon_unlocks option)
    **{name: ItemData(0x100 + i, _U, count=0, groups=frozenset({"Weapons"}), grant="weapon")
       for i, name in enumerate(WEAPONS)},
}

ITEM_NAME_TO_ID = {name: ID_BASE + data.offset for name, data in ITEMS.items()}
ITEM_NAME_GROUPS = {
    group: {name for name, data in ITEMS.items() if group in data.groups}
    for group in sorted({g for data in ITEMS.values() for g in data.groups})
}


@dataclass(frozen=True)
class LocationData:
    offset: int
    region: Region
    plot: str  # check predicate, see the module docstring
    needs: tuple[str, ...] = ()  # items/events logic requires beyond the region's entrance
    any_of: tuple[str, ...] = ()  # at least one of these items/events
    category: str = "story"  # story, recruitment, loyalty, n7, hub, dlc, endgame
    dlc: str | None = None  # enabled_dlc key that must be on
    excluded: bool = False  # filler only (point of no return, or the predicate can be skipped by a choice)


# Events (locked items on event locations, no IDs). The logic counts what the player has done in game.
EVENT_HORIZON = "Horizon Complete"
EVENT_COLLECTOR_SHIP = "Collector Ship Complete"
EVENT_IFF = "Reaper IFF Acquired"
EVENT_VICTORY = "Victory"


def recruited(name: str) -> str:
    return f"{name} Recruited"


def loyalty_done(name: str) -> str:
    return f"{name} Loyalty Mission Complete"


_L = 0x1000
_H = (EVENT_HORIZON,)
LOCATIONS: dict[str, LocationData] = {
    # Prologue and story (rewards bools 5794-5816 are each mission's completion reward state)
    "Lazarus Station: Awakening": LocationData(_L + 0x00, Region.NORMANDY, "bool 5794"),
    "Freedom's Progress: Complete": LocationData(_L + 0x01, Region.NORMANDY, "bool 5795"),
    "Horizon: Complete": LocationData(_L + 0x02, Region.HORIZON, "bool 5796"),
    "Collector Ship: Complete": LocationData(_L + 0x03, Region.COLLECTOR_SHIP, "bool 5797"),
    "Derelict Reaper: Acquire the IFF": LocationData(_L + 0x04, Region.DERELICT_REAPER, "bool 5816 or 1256"),
    # Recruitment: dossier mission completion, never the in-party/selectable bools (LE1 lesson: delivery can set those)
    "Omega: Recruit Mordin": LocationData(_L + 0x100, Region.OMEGA, "bool 5814", ("Dossier: The Professor",), category="recruitment"),
    "Omega: Recruit Garrus": LocationData(_L + 0x101, Region.OMEGA, "bool 5813", ("Dossier: Archangel",), category="recruitment"),
    "Purgatory: Recruit Jack": LocationData(_L + 0x102, Region.PURGATORY, "bool 5815", category="recruitment"),
    "Korlus: Recruit Grunt": LocationData(_L + 0x103, Region.KORLUS, "bool 5812", category="recruitment"),
    "Illium: Recruit Thane": LocationData(_L + 0x104, Region.ILLIUM, "bool 5818", ("Dossier: The Assassin",), category="recruitment"),
    "Illium: Recruit Samara": LocationData(_L + 0x105, Region.ILLIUM, "bool 5819", ("Dossier: The Justicar",), category="recruitment"),
    "Haestrom: Recruit Tali": LocationData(_L + 0x106, Region.HAESTROM, "bool 5817", category="recruitment"),
    # Legion: activated or handed to Cerberus, either choice counts (bool 1247 / 1248)
    "Normandy: Legion's Fate": LocationData(_L + 0x107, Region.DERELICT_REAPER, "bool 1247 or 1248", category="recruitment"),
    # DLC recruits have no dossier reward bool in the save-editor DB: "in party" is the candidate (D5; no AP delivery
    # writes it while recruitment stays vanilla)
    "Omega: Recruit Zaeed": LocationData(_L + 0x108, Region.OMEGA, "bool 44", ("Dossier: Zaeed Massani",), category="recruitment", dlc="Zaeed"),
    "Citadel: Recruit Kasumi": LocationData(_L + 0x109, Region.CITADEL, "bool 37", ("Dossier: Kasumi Goto",), category="recruitment", dlc="Kasumi"),
    # Loyalty missions: completion reward bools, branch-neutral (any outcome counts, loyal or not)
    "Miranda: The Prodigal": LocationData(_L + 0x200, Region.LOYALTY, "bool 5810 or 1496", _H, category="loyalty"),
    "Jacob: The Gift of Greatness": LocationData(_L + 0x201, Region.LOYALTY, "bool 5802 or 1497", _H, category="loyalty"),
    "Mordin: Old Blood": LocationData(_L + 0x202, Region.TUCHANKA, "bool 5807 or 1504", (recruited("Mordin Solus"),), category="loyalty"),
    "Garrus: Eye for an Eye": LocationData(_L + 0x203, Region.LOYALTY, "bool 5811 or 1501", (EVENT_HORIZON, recruited("Garrus Vakarian")), category="loyalty"),
    "Jack: Subject Zero": LocationData(_L + 0x204, Region.LOYALTY, "bool 5805 or 1498", (EVENT_HORIZON, recruited("Jack")), category="loyalty"),
    "Grunt: Rite of Passage": LocationData(_L + 0x205, Region.TUCHANKA, "bool 5806 or 1505", (recruited("Grunt"),), category="loyalty"),
    "Thane: Sins of the Father": LocationData(_L + 0x206, Region.LOYALTY, "bool 5804 or 1502", (recruited("Thane Krios"),), category="loyalty"),
    "Samara: The Ardat-Yakshi": LocationData(_L + 0x207, Region.LOYALTY, "bool 5808 or 1506", (recruited("Samara"),), category="loyalty"),
    "Tali: Treason": LocationData(_L + 0x208, Region.LOYALTY, "bool 5809 or 1503", (recruited("Tali'Zorah vas Neema"),), category="loyalty"),
    "Legion: A House Divided": LocationData(_L + 0x209, Region.DERELICT_REAPER, "bool 5803 or 1499", (recruited("Legion"),), category="loyalty"),
    "Zaeed: The Price of Revenge": LocationData(_L + 0x20A, Region.LOYALTY, "bool 1507", (EVENT_HORIZON, recruited("Zaeed Massani")), category="loyalty", dlc="Zaeed"),
    "Kasumi: Stealing Memory": LocationData(_L + 0x20B, Region.LOYALTY, "bool 1500", (EVENT_HORIZON, recruited("Kasumi Goto")), category="loyalty", dlc="Kasumi"),
    # Collector Base: past the point of no return, so filler only (sent before the goal, useful to other slots)
    "Omega 4 Relay: Stop the Collectors": LocationData(_L + 0x300, Region.COLLECTOR_BASE, "bool 5798", category="endgame", excluded=True),
    "Collector Base: Tartarus Debris Field": LocationData(_L + 0x301, Region.COLLECTOR_BASE, "bool 5799", category="endgame", excluded=True),
    "Collector Base: Infiltration": LocationData(_L + 0x302, Region.COLLECTOR_BASE, "bool 5800", category="endgame", excluded=True),
    "Collector Base: The Long Walk": LocationData(_L + 0x303, Region.COLLECTOR_BASE, "bool 5801", category="endgame", excluded=True),
}

# N7 assignments (assignments option). Conservative logic: after Horizon (D7) until each one's trigger is traced.
N7_ASSIGNMENTS = {
    "N7: Archeological Dig Site": 5823,
    "N7: MSV Strontium Mule": 5824,
    "N7: Blue Suns Base": 5825,
    "N7: Anomalous Weather Detected": 5826,
    "N7: Blood Pack Communications Relay": 5827,
    "N7: Wrecked Merchant Freighter": 5828,
    "N7: Blood Pack Base": 5829,
    "N7: Hahne-Kedar Facility": 5830,
    "N7: Abandoned Research Station": 5832,
    "N7: MSV Estevanico": 5833,
    "N7: Captured Mining Facility": 5834,
    "N7: Eclipse Smuggling Depot": 5835,
    "N7: Quarian Crash Site": 5836,
    "N7: Mining the Canyon": 5837,
    "N7: Imminent Ship Crash": 5838,
    "N7: Lost Operative": 5839,
    "N7: Endangered Research Station": 5840,
    "N7: Javelin Missiles Launched": 5841,
    "N7: Abandoned Mine": 5843,
}
LOCATIONS.update({name: LocationData(_L + 0x400 + i, Region.UNCHARTED, f"bool {plot}", _H, category="n7")
                  for i, (name, plot) in enumerate(N7_ASSIGNMENTS.items())})

# Hub assignments (assignments: all). Only those whose hub is known with confidence; the rest of the save-editor
# rewards block (omgoracle, omgsun, pradaniel, ...) is catalogued as unplaced in CHECKS-CATALOG.md.
HUB_ASSIGNMENTS: dict[str, tuple[Region, int, tuple[str, ...]]] = {
    "Omega: Packages for Ish": (Region.OMEGA, 5858, ()),
    "Omega: Batarian Bartender": (Region.OMEGA, 5861, ()),
    "Omega: Help the Injured Batarian": (Region.OMEGA, 5873, ("Dossier: The Professor",)),  # inside Mordin's mission
    "Citadel: Crime in Progress": (Region.CITADEL, 5867, ()),
    "Citadel: Spoke to Khalisah": (Region.CITADEL, 5868, ()),
    "Citadel: False Positives": (Region.CITADEL, 5869, ()),
    "Illium: Blue Rose of Illium": (Region.ILLIUM, 5850, ()),
    "Illium: Conrad Verner": (Region.ILLIUM, 5851, ()),
    "Illium: Medical Scans": (Region.ILLIUM, 5852, ()),
    "Illium: Gianna Parasini": (Region.ILLIUM, 5853, ()),
    "Illium: Indentured Service": (Region.ILLIUM, 5854, ()),
    "Illium: Salarian Family Data": (Region.ILLIUM, 5856, ()),
    "Tuchanka: Combustion Manifold": (Region.TUCHANKA, 5865, ()),
    "Tuchanka: Krogan Sushi": (Region.TUCHANKA, 5866, ()),
    "Tuchanka: Missing Scout": (Region.TUCHANKA, 5875, ()),
    "Normandy: Special Ingredients": (Region.NORMANDY, 5845, _H),
    "Normandy: Serrice Ice Brandy": (Region.NORMANDY, 5846, _H),
    "Normandy: FBA Couplings": (Region.NORMANDY, 5847, _H),
}
LOCATIONS.update({name: LocationData(_L + 0x500 + i, region, f"bool {plot}", needs, category="hub")
                  for i, (name, (region, plot, needs)) in enumerate(HUB_ASSIGNMENTS.items())})

# DLC missions (enabled_dlc). Conservative: after Horizon. Arrival is reachable only late and is filler only (D9).
LOCATIONS.update({
    "Project Overlord: Complete": LocationData(_L + 0x600, Region.DLC, "bool 6512", _H, category="dlc", dlc="Overlord"),
    "Lair of the Shadow Broker: Complete": LocationData(_L + 0x601, Region.ILLIUM, "bool 6815", category="dlc", dlc="Shadow Broker"),
    "Arrival: Complete": LocationData(_L + 0x602, Region.DLC, "bool 7451", (EVENT_IFF,), category="dlc", dlc="Arrival", excluded=True),
    "Firewalker: Volcano Station": LocationData(_L + 0x603, Region.DLC, "bool 5820", _H, category="dlc", dlc="Firewalker"),
    "Firewalker: Prothean Site": LocationData(_L + 0x604, Region.DLC, "bool 5821", _H, category="dlc", dlc="Firewalker"),
    "Firewalker: Survey Sites Located": LocationData(_L + 0x605, Region.DLC, "bool 5822", _H, category="dlc", dlc="Firewalker"),
    "Firewalker: Rosalie Lost": LocationData(_L + 0x606, Region.DLC, "bool 5842", _H, category="dlc", dlc="Firewalker"),
    "Firewalker: Geth Incursions": LocationData(_L + 0x607, Region.DLC, "bool 5831", _H, category="dlc", dlc="Firewalker"),
    "Normandy Crash Site: Recover Shepard's Helmet": LocationData(_L + 0x608, Region.DLC, "bool 6157", _H, category="dlc", dlc="Normandy Crash Site"),
})

DLC_KEYS = ("Kasumi", "Zaeed", "Overlord", "Shadow Broker", "Arrival", "Firewalker", "Normandy Crash Site")

LOCATION_NAME_TO_ID = {name: ID_BASE + data.offset for name, data in LOCATIONS.items()}
LOCATION_NAME_GROUPS: dict[str, set[str]] = {
    region.value: {name for name, data in LOCATIONS.items() if data.region is region} for region in Region
}
for _category, _group in (("recruitment", "Recruitment"), ("loyalty", "Loyalty Missions"), ("n7", "N7 Assignments"),
                          ("hub", "Hub Assignments"), ("dlc", "DLC")):
    LOCATION_NAME_GROUPS[_group] = {name for name, data in LOCATIONS.items() if data.category == _category}
LOCATION_NAME_GROUPS = {group: names for group, names in LOCATION_NAME_GROUPS.items() if names}

# Squad whose loyalty the "all_loyal" readiness policy requires (D10): everyone recruitable before Omega 4 in the seed.
LOYALTY_LOCATION = {
    "Miranda Lawson": "Miranda: The Prodigal",
    "Jacob Taylor": "Jacob: The Gift of Greatness",
    "Mordin Solus": "Mordin: Old Blood",
    "Garrus Vakarian": "Garrus: Eye for an Eye",
    "Jack": "Jack: Subject Zero",
    "Grunt": "Grunt: Rite of Passage",
    "Thane Krios": "Thane: Sins of the Father",
    "Samara": "Samara: The Ardat-Yakshi",
    "Tali'Zorah vas Neema": "Tali: Treason",
    "Legion": "Legion: A House Divided",
    "Zaeed Massani": "Zaeed: The Price of Revenge",
    "Kasumi Goto": "Kasumi: Stealing Memory",
}
RECRUIT_LOCATION = {
    "Mordin Solus": "Omega: Recruit Mordin",
    "Garrus Vakarian": "Omega: Recruit Garrus",
    "Jack": "Purgatory: Recruit Jack",
    "Grunt": "Korlus: Recruit Grunt",
    "Thane Krios": "Illium: Recruit Thane",
    "Samara": "Illium: Recruit Samara",
    "Tali'Zorah vas Neema": "Haestrom: Recruit Tali",
    "Legion": "Normandy: Legion's Fate",
    "Zaeed Massani": "Omega: Recruit Zaeed",
    "Kasumi Goto": "Citadel: Recruit Kasumi",
}
