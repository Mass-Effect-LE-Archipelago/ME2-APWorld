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

from .codex import CODEX
from .pickups import PICKUPS

ID_BASE = 0x4D32_0000  # "M2": deliberately not LE1's 0x4D45_0000 (feasibility plan, "Runtime contract")
# Offsets inside ID_BASE: items 0x0000-0x0FFF, locations 0x1000-0x7FFF:
#   0x1000 prologue and story, 0x1100 recruitment, 0x1200 loyalty, 0x1300 Collector Base, 0x1400 N7 assignments,
#   0x1500 hub assignments, 0x1600 DLC missions, 0x1700 research, 0x1800 collectibles, 0x1900-0x1BFF pickups.
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
    LATE_GAME = "Late Game"  # after the Collector Ship with every loyalty mission done (D16): research, shops, unplaced


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
    category: str = "story"  # story, recruitment, loyalty, n7, hub, dlc, endgame, research, collectible, pickup
    dlc: str | None = None  # enabled_dlc key that must be on
    excluded: bool = False  # filler only (point of no return, or the predicate can be skipped by a choice)
    prologue: bool = False  # Lazarus Station / Freedom's Progress: removed when the seed starts on the Normandy


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
    "Lazarus Station: Awakening": LocationData(_L + 0x00, Region.NORMANDY, "bool 5794", prologue=True),
    "Freedom's Progress: Complete": LocationData(_L + 0x01, Region.NORMANDY, "bool 5795", prologue=True),
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
    "Citadel: Krogan Sushi": (Region.CITADEL, 5866, ()),  # XP_citfish
    # XP_prlbrain: the scout's body is found during Mordin's loyalty mission on Tuchanka
    "Tuchanka: Missing Scout": (Region.TUCHANKA, 5875, (recruited("Mordin Solus"),)),
    "Normandy: Special Ingredients": (Region.NORMANDY, 5845, _H),
    "Normandy: Serrice Ice Brandy": (Region.NORMANDY, 5846, _H),
    "Normandy: FBA Couplings": (Region.NORMANDY, 5847, _H),
    "Illium: Liara: Systems Hacking": (Region.ILLIUM, 5848, ()),
    "Illium: Liara: The Observer": (Region.ILLIUM, 5849, ()),
    # Placed from le2.json Global/Experience map codes (XP_omgaria, XP_twrlocket, ...): asa/mwa are the Assassin and
    # Justicar recruitment missions on Illium, kro is Tuchanka. IDs keep their original order (append-only).
    "Omega: Aria's Datapad": (Region.OMEGA, 5862, ()),
    "Illium: Lost Locket": (Region.ILLIUM, 5855, ()),
    "Illium: Stolen Goods": (Region.ILLIUM, 5857, ()),
    "Illium: Smuggling Evidence": (Region.ILLIUM, 5871, ("Dossier: The Justicar",)),
    "Illium: Report Elnora": (Region.ILLIUM, 5870, ("Dossier: The Justicar",)),
    "Tuchanka: Killing Pyjacks": (Region.TUCHANKA, 5864, ()),
    "Illium: Help Nassana's Workers": (Region.ILLIUM, 5863, ("Dossier: The Assassin",)),
    "Hub: Astrosmash": (Region.LATE_GAME, 5844, ()),  # no map code in its XP name; stays late until traced
    # Not placed before: names from the XP codes, provisional until seen in game
    "Omega: The Oracle": (Region.OMEGA, 5859, ()),
    "Omega: Sun Assignment": (Region.OMEGA, 5860, ()),
    "Omega: Daniel": (Region.OMEGA, 5874, ("Dossier: The Professor",)),  # XP_pradaniel: inside Mordin's mission
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

# Research purchases in the Normandy's tech lab (research option): each project's "unlocked" bool (me2_plot_db
# research_upgrades). The three suicide-mission ship upgrades are items, and their delivery sets the unlocked bool, so
# they are never checks. Late game (D16) because blueprints are found across the whole campaign.
RESEARCH: dict[str, tuple[int, str | None]] = {
    "Research: Assault Rifle Damage": (6051, None),
    "Research: Assault Rifle Accuracy": (5134, None),
    "Research: Assault Rifle Penetration": (5133, None),
    "Research: SMG Damage": (6052, None),
    "Research: SMG Shield Piercing": (5135, None),
    "Research: SMG Extra Rounds": (5136, None),
    "Research: Heavy Pistol Damage": (6056, None),
    "Research: Heavy Pistol Penetration": (5139, None),
    "Research: Heavy Pistol Critical": (5140, None),
    "Research: Shotgun Damage": (6061, None),
    "Research: Shotgun Shield Piercing": (5152, None),
    "Research: Shotgun Extra Rounds": (5153, None),
    "Research: Sniper Rifle Damage": (6062, None),
    "Research: Sniper Rifle Penetration": (5148, None),
    "Research: Sniper Rifle Headshot Damage": (5149, None),
    "Research: Heavy Weapon Ammo": (6055, None),
    "Research: ML-77 Missile Launcher": (5137, None),
    "Research: M-622 Avalanche": (5138, None),
    "Research: M-920 Cain": (5290, None),
    "Research: Medi-Gel Capacity": (6058, None),
    "Research: Trauma Module": (5141, None),
    "Research: Emergency Shielding": (5142, None),
    "Research: Shield Damage Protection": (6060, None),
    "Research: Hard Shields": (5147, None),
    "Research: Redundant Field Generator": (5146, None),
    "Research: Biotic Damage": (6053, None),
    "Research: Biotic Cooldown": (5155, None),
    "Research: Biotic Duration": (5154, None),
    "Research: Tech Damage": (6063, None),
    "Research: Tech Cooldowns": (5151, None),
    "Research: Tech Duration": (5150, None),
    "Research: Dermal Regeneration": (6144, None),
    "Research: Heavy Skin Weave": (6059, None),
    "Research: Heavy Bone Weave": (5144, None),
    "Research: Heavy Muscle Weave": (5145, None),
    "Research: Extended Fuel Cells": (5644, None),
    "Research: Modular Probe Bay": (5646, None),
    "Research: Advanced Mineral Scanner": (5647, None),
    "Research: Krogan Vitality": (6054, "Grunt"),
    "Research: Krogan Shotgun": (5638, "Grunt"),
    "Research: Subject Zero Biotic Boost": (5639, "Jack"),
    "Research: Mordin's Omni-tool": (5641, "Mordin Solus"),
    "Research: Geth Shield Strength": (6057, "Legion"),
    "Research: Legion's Sniper Rifle": (5640, "Legion"),
}
LOCATIONS.update({name: LocationData(_L + 0x700 + i, Region.LATE_GAME, f"bool {plot}",
                                     (recruited(who),) if who else (), category="research")
                  for i, (name, (plot, who)) in enumerate(RESEARCH.items())})

# Collectibles (collectibles option): captain's cabin purchases and base-game armor pieces, bought or found across the
# hubs. Pre-order and DLC-pack armor (Terminus, Blood Dragon, Inferno, Collector, Cerberus, Kestrel, the Aegis pack and
# the Genesis/Equalizer helmets) is left out: Legendary Edition may grant it at the start (LE1 lesson: starting flags
# completed checks on the first run).
COLLECTIBLES: dict[str, tuple[int, str | None]] = {
    "Cabin: Space Hamster": (3321, None),
    "Cabin: Normandy SR-1 Model": (3326, None),
    "Cabin: Destiny Ascension Model": (3328, None),
    "Cabin: Sovereign Model": (3329, None),
    "Cabin: Turian Cruiser Model": (3330, None),
    "Cabin: Alliance Cruiser Model": (3331, None),
    "Cabin: Flotilla Vessel Model": (3332, None),
    "Cabin: Kodiak Drop Shuttle Model": (3334, None),
    "Cabin: Athabasca Freighter Model": (3337, None),
    "Cabin: Geth Ship Model": (3338, None),
    "Cabin: Illium Skald Fish": (3322, None),
    "Cabin: Thessian Sunfish": (3323, None),
    "Cabin: Prejek Paddle Fish": (3324, None),
    "Cabin: Shadow Broker Base Model": (7200, "Shadow Broker"),
    "Cabin: Prothean Relic": (6206, "Firewalker"),
    "Armor: Kuwashii Visor": (4433, None),
    "Armor: Death Mask": (4450, None),
    "Armor: Capacitor Chestplate": (4438, None),
    "Armor: Shield Harness": (4453, None),
    "Armor: Amplifier Plates": (4423, None),
    "Armor: Asymmetric Defense Layer": (4451, None),
    "Armor: Strength Boost Pads": (4437, None),
    "Armor: Heavy Damping Gauntlets": (4449, None),
    "Armor: Stabilization Gauntlets": (4435, None),
    "Armor: Stimulator Conduits": (4436, None),
    "Armor: Ordnance Packs": (4434, None),
}
LOCATIONS.update({name: LocationData(_L + 0x800 + i, Region.LATE_GAME, f"bool {plot}", category="collectible", dlc=dlc)
                  for i, (name, (plot, dlc)) in enumerate(COLLECTIBLES.items())})

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

# Pickups (pickups option): treasure "found" bools, each in the mission or hub where it lies (pickups.py). A mission's
# pickups share its check's region and rule, so a loyalty mission's pickups wait for that loyalty mission.
_STORY_AREAS = {
    "lazarus": (Region.NORMANDY, ()), "freedom": (Region.NORMANDY, ()), "horizon": (Region.HORIZON, ()),
    "collector_ship": (Region.COLLECTOR_SHIP, ()), "reaper": (Region.DERELICT_REAPER, ()),
    "citadel": (Region.CITADEL, ()), "omega": (Region.OMEGA, ()), "illium": (Region.ILLIUM, ()),
    "tuchanka": (Region.TUCHANKA, ()),
}
_CHECK_AREAS = {
    "mordin_acq": RECRUIT_LOCATION["Mordin Solus"], "garrus_acq": RECRUIT_LOCATION["Garrus Vakarian"],
    "jack_acq": RECRUIT_LOCATION["Jack"], "grunt_acq": RECRUIT_LOCATION["Grunt"],
    "thane_acq": RECRUIT_LOCATION["Thane Krios"], "samara_acq": RECRUIT_LOCATION["Samara"],
    "tali_acq": RECRUIT_LOCATION["Tali'Zorah vas Neema"],
    "miranda_l": LOYALTY_LOCATION["Miranda Lawson"], "jacob_l": LOYALTY_LOCATION["Jacob Taylor"],
    "mordin_l": LOYALTY_LOCATION["Mordin Solus"], "garrus_l": LOYALTY_LOCATION["Garrus Vakarian"],
    "jack_l": LOYALTY_LOCATION["Jack"], "grunt_l": LOYALTY_LOCATION["Grunt"],
    "thane_l": LOYALTY_LOCATION["Thane Krios"], "samara_l": LOYALTY_LOCATION["Samara"],
    "tali_l": LOYALTY_LOCATION["Tali'Zorah vas Neema"], "legion_l": LOYALTY_LOCATION["Legion"],
    "zaeed_l": LOYALTY_LOCATION["Zaeed Massani"], "kasumi_l": LOYALTY_LOCATION["Kasumi Goto"],
    "lotsb": "Lair of the Shadow Broker: Complete", "arrival": "Arrival: Complete",
    "overlord": "Project Overlord: Complete", "firewalker": "Firewalker: Prothean Site",
}


def _pickup(offset: int, plot: int, area: str) -> LocationData:
    if area in _STORY_AREAS:
        region, needs = _STORY_AREAS[area]
        return LocationData(offset, region, f"bool {plot}", needs, category="pickup",
                            prologue=area in ("lazarus", "freedom"))
    check = LOCATIONS[_CHECK_AREAS[area]]
    return LocationData(offset, check.region, f"bool {plot}", check.needs, check.any_of, "pickup", check.dlc,
                        check.excluded)


LOCATIONS.update({name: _pickup(_L + 0x900 + i, plot, area) for i, (name, plot, area) in enumerate(PICKUPS)})


def _codex(offset: int, predicate: str, area: str) -> LocationData:
    """A codex page in the area of its most accessible source (codex.py); always non-progression (regions.py)."""
    if area == "normandy":
        return LocationData(offset, Region.NORMANDY, predicate, category="codex")
    if area == "n7":
        return LocationData(offset, Region.UNCHARTED, predicate, category="codex")
    if area in _STORY_AREAS:
        region, needs = _STORY_AREAS[area]
        return LocationData(offset, region, predicate, needs, category="codex", prologue=area in ("lazarus", "freedom"))
    check = LOCATIONS[_CHECK_AREAS[area]]
    return LocationData(offset, check.region, predicate, check.needs, check.any_of, "codex", check.dlc, check.excluded)


LOCATIONS.update({name: _codex(_L + 0xC00 + i, predicate, area) for i, (name, predicate, area) in enumerate(CODEX)})

# Weapon pickups (D17 follow-up, pickups option): the Tre_Wpn_* treasure "found" bools of the missions. Each follows its
# mission like any pickup; the weapon's own unlock item never goes on it (regions.py), so receiving the item can't hide
# the pickup. Left out: the Collector Ship's Bonus/Super weapon choice (one of several) and the research Tre_Wpn rows.
# Order is the ID order (block 0xB00): append only.
WEAPON_PICKUPS: tuple[tuple[str, int, str, str | None], ...] = (  # (location, plot, area, weapon item or None)
    ("Lazarus Station: M-100 Grenade Launcher", 1191, "lazarus", "M-100 Grenade Launcher"),
    ("Horizon: Collector Particle Beam", 912, "horizon", None),
    ("Recruit Garrus: M-15 Vindicator", 898, "garrus_acq", "M-15 Vindicator"),
    ("Recruit Mordin: M-6 Carnifex", 1798, "mordin_acq", "M-6 Carnifex"),
    ("Recruit Tali: M-9 Tempest", 690, "tali_acq", "M-9 Tempest"),
    ("Recruit Tali: Geth Pulse Rifle", 5239, "tali_acq", "Geth Pulse Rifle"),
    ("Recruit Thane: M-97 Viper", 916, "thane_acq", "M-97 Viper"),
    ("Recruit Samara: M-27 Scimitar", 889, "samara_acq", "M-27 Scimitar"),
    ("Stealing Memory: M-12 Locust", 6710, "kasumi_l", "M-12 Locust"),
)
WEAPON_PICKUP_ITEM = {name: weapon for name, _, _, weapon in WEAPON_PICKUPS if weapon}
LOCATIONS.update({name: _pickup(_L + 0xB00 + i, plot, area) for i, (name, plot, area, _) in enumerate(WEAPON_PICKUPS)})

# Missed-checks salvage (D22, salvage option): every pickup area that can't be revisited (hubs excluded) gets one entry
# at the Normandy research terminal once the location naming its completion is true. The order is the index k that
# fixes the mod's plot ints and treasure rows (tools/le2mod/salvage.json): append only.
SALVAGE_MISSIONS: tuple[tuple[str, str, str], ...] = (  # (pickup area, terminal label, completion location)
    ("lazarus", "Lazarus Station", "Lazarus Station: Awakening"),
    ("freedom", "Freedom's Progress", "Freedom's Progress: Complete"),
    ("horizon", "Horizon", "Horizon: Complete"),
    ("collector_ship", "Collector Ship", "Collector Ship: Complete"),
    ("reaper", "Derelict Reaper", "Derelict Reaper: Acquire the IFF"),
    ("mordin_acq", "Mordin's Recruitment", _CHECK_AREAS["mordin_acq"]),
    ("garrus_acq", "Garrus's Recruitment", _CHECK_AREAS["garrus_acq"]),
    ("jack_acq", "Purgatory", _CHECK_AREAS["jack_acq"]),
    ("grunt_acq", "Korlus", _CHECK_AREAS["grunt_acq"]),
    ("thane_acq", "Dantius Towers", _CHECK_AREAS["thane_acq"]),
    ("samara_acq", "Samara's Recruitment", _CHECK_AREAS["samara_acq"]),
    ("tali_acq", "Haestrom", _CHECK_AREAS["tali_acq"]),
    ("miranda_l", "Miranda's Loyalty", _CHECK_AREAS["miranda_l"]),
    ("jacob_l", "Jacob's Loyalty", _CHECK_AREAS["jacob_l"]),
    ("mordin_l", "Mordin's Loyalty", _CHECK_AREAS["mordin_l"]),
    ("garrus_l", "Garrus's Loyalty", _CHECK_AREAS["garrus_l"]),
    ("jack_l", "Jack's Loyalty", _CHECK_AREAS["jack_l"]),
    ("grunt_l", "Grunt's Loyalty", _CHECK_AREAS["grunt_l"]),
    ("thane_l", "Thane's Loyalty", _CHECK_AREAS["thane_l"]),
    ("samara_l", "Samara's Loyalty", _CHECK_AREAS["samara_l"]),
    ("tali_l", "Tali's Loyalty", _CHECK_AREAS["tali_l"]),
    ("legion_l", "Legion's Loyalty", _CHECK_AREAS["legion_l"]),
    ("zaeed_l", "Zaeed's Loyalty", _CHECK_AREAS["zaeed_l"]),
    ("kasumi_l", "Kasumi's Loyalty", _CHECK_AREAS["kasumi_l"]),
    ("lotsb", "Lair of the Shadow Broker", _CHECK_AREAS["lotsb"]),
    ("arrival", "Arrival", _CHECK_AREAS["arrival"]),
    ("overlord", "Project Overlord", _CHECK_AREAS["overlord"]),
    ("firewalker", "Firewalker", _CHECK_AREAS["firewalker"]),
)
SALVAGE_PRICES = (0, 500, 1000, 2500, 5000)  # credits per check, by salvage_price option value
SALVAGE_PICKUPS: dict[str, tuple[str, ...]] = {
    area: tuple(name for name, _, a in PICKUPS if a == area) + tuple(name for name, _, a, _ in WEAPON_PICKUPS if a == area)
    for area, _, _ in SALVAGE_MISSIONS}

DLC_KEYS = ("Kasumi", "Zaeed", "Overlord", "Shadow Broker", "Arrival", "Firewalker", "Normandy Crash Site")

LOCATION_NAME_TO_ID = {name: ID_BASE + data.offset for name, data in LOCATIONS.items()}
LOCATION_NAME_GROUPS: dict[str, set[str]] = {
    region.value: {name for name, data in LOCATIONS.items() if data.region is region} for region in Region
}
for _category, _group in (("recruitment", "Recruitment"), ("loyalty", "Loyalty Missions"), ("n7", "N7 Assignments"),
                          ("hub", "Hub Assignments"), ("dlc", "DLC"), ("research", "Research"),
                          ("collectible", "Collectibles"), ("pickup", "Pickups")):
    LOCATION_NAME_GROUPS[_group] = {name for name, data in LOCATIONS.items() if data.category == _category}
LOCATION_NAME_GROUPS = {group: names for group, names in LOCATION_NAME_GROUPS.items() if names}


# ME1 history (the Genesis comic's six choices; tools/le2mod/research/genesis_choices.tsv). Each answer is the plot bools
# its Genesis transition sets; the other answers' bools are cleared. Option names follow the ME3 world's history keys.
ME1_HISTORY: dict[str, dict[str, dict[int, bool]]] = {
    "me1_virmire_survivor": {"ashley": {1541: True, 1540: False}, "kaidan": {1540: True, 1541: False}},
    "me1_romance": {answer: {bool_id: bool_id == chosen for bool_id in (1926, 1528, 1529, 1530)}
                    for answer, chosen in (("none", 1926), ("ashley", 1528), ("kaidan", 1529), ("liara", 1530))},
    "me1_rachni": {"saved": {7447: True, 3151: True}, "killed": {7447: True, 3151: False}},
    "me1_wrex": {"alive": {7448: True, 3752: False}, "dead": {7448: True, 3752: True}},
    "me1_council": {"saved": {1554: True, 1553: False}, "sacrificed": {1553: True, 1554: False}},
    "me1_human_councilor": {"anderson": {1556: True, 1555: False}, "udina": {1555: True, 1556: False}},
}
ME1_HISTORY_BOOLS = frozenset(b for answers in ME1_HISTORY.values() for bools in answers.values() for b in bools)
FEMALE_PLOT_BOOL = 66  # Female_Player, set by the main menu's gender pick


def me1_history_writes(choices: dict[str, str], female: bool) -> tuple[dict[int, bool], bool]:
    """The plot bools for these choices, and whether the romance fell back to none: an ME1 romance needs a partner who
    could romance this Shepard (Ashley: male; Kaidan: female) and, for Ashley or Kaidan, survived Virmire."""
    romance = choices["me1_romance"]
    if (romance == "ashley" and (female or choices["me1_virmire_survivor"] != "ashley")) or \
            (romance == "kaidan" and (not female or choices["me1_virmire_survivor"] != "kaidan")):
        choices = {**choices, "me1_romance": "none"}
    writes: dict[int, bool] = {}
    for key, answers in ME1_HISTORY.items():
        writes.update(answers[choices[key]])
    return writes, choices["me1_romance"] != romance
