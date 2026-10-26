import re

from BaseClasses import CollectionState, LocationProgressType

from ..data import (DOSSIERS, EVENT_COLLECTOR_SHIP, EVENT_HORIZON, EVENT_IFF, IFF_INTEL, LOCATIONS, PHASE_1, PHASE_2,
                    Region, SHIP_UPGRADES, WEAPONS, loyalty_done, recruited)
from ..options import options_presets
from . import MassEffectLE2TestBase


class LE2Helpers(MassEffectLE2TestBase):
    # Logic tests use the vanilla opening: a random starting dossier would let state sweeps collect events early.
    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls.options = {"start_on_normandy": False, **cls.__dict__.get("options", {})}

    def collect_event(self, name: str) -> None:
        self.collect(self.multiworld.get_location(name, self.player).item)

    def location(self, name: str):
        return self.multiworld.get_location(name, self.player)

    def names(self) -> set[str]:
        return {loc.name for loc in self.multiworld.get_locations(self.player) if loc.address is not None}


class TestDefaults(LE2Helpers):
    options = {"start_on_normandy": False}  # the vanilla opening; TestStartOnNormandy covers the default skip

    def test_prologue_checks_are_open(self) -> None:
        self.assertTrue(self.can_reach_location("Lazarus Station: Awakening"))
        self.assertTrue(self.can_reach_location("Freedom's Progress: Complete"))

    def test_recruitment_needs_its_dossier(self) -> None:
        self.assertTrue(self.can_reach_region(Region.OMEGA.value))
        self.assertFalse(self.can_reach_location("Omega: Recruit Mordin"))
        self.collect_by_name(DOSSIERS["Mordin Solus"])
        self.assertTrue(self.can_reach_location("Omega: Recruit Mordin"))
        self.assertFalse(self.can_reach_region(Region.PURGATORY.value))
        self.collect_by_name(DOSSIERS["Jack"])
        self.assertTrue(self.can_reach_location("Purgatory: Recruit Jack"))

    def test_horizon_needs_the_first_wave(self) -> None:
        for name in PHASE_1[:-1]:
            self.collect_by_name(DOSSIERS[name])
        self.assertFalse(self.can_reach_region(Region.HORIZON.value))
        self.collect_by_name(DOSSIERS[PHASE_1[-1]])
        self.assertTrue(self.can_reach_region(Region.HORIZON.value))

    def test_second_wave_needs_horizon(self) -> None:
        self.collect_by_name([DOSSIERS[name] for name in PHASE_2])
        self.assertFalse(self.can_reach_location("Illium: Recruit Thane"))
        self.assertFalse(self.can_reach_location("Haestrom: Recruit Tali"))
        self.collect_event(EVENT_HORIZON)
        self.assertTrue(self.can_reach_location("Illium: Recruit Thane"))
        self.assertTrue(self.can_reach_location("Haestrom: Recruit Tali"))

    def test_derelict_reaper_needs_required_intel(self) -> None:
        self.collect_event(EVENT_COLLECTOR_SHIP)
        intel = self.get_items_by_name(IFF_INTEL)
        self.assertEqual(len(intel), 5)
        self.collect(intel[:2])
        self.assertFalse(self.can_reach_region(Region.DERELICT_REAPER.value))
        self.collect(intel[2:3])
        self.assertTrue(self.can_reach_region(Region.DERELICT_REAPER.value))

    def test_omega_4_needs_iff_and_all_ship_upgrades(self) -> None:
        self.collect_event(EVENT_IFF)
        self.collect_by_name(list(SHIP_UPGRADES[:-1]))
        self.assertFalse(self.can_reach_region(Region.COLLECTOR_BASE.value))
        self.collect_by_name(SHIP_UPGRADES[-1])
        self.assertTrue(self.can_reach_region(Region.COLLECTOR_BASE.value))

    def test_victory_needs_every_loyalty_mission(self) -> None:
        self.collect_event(EVENT_IFF)
        self.collect_by_name(list(SHIP_UPGRADES))
        self.assertFalse(self.can_reach_location("Victory"))

    def test_loyalty_needs_the_recruit(self) -> None:
        self.collect_event(EVENT_HORIZON)
        self.assertFalse(self.can_reach_location("Garrus: Eye for an Eye"))
        self.collect_event(recruited("Garrus Vakarian"))
        self.assertFalse(self.can_reach_location("Garrus: Eye for an Eye"))  # D26: needs every loyalty copy
        self.collect(self.get_items_by_name("Progressive Loyalty Mission"))
        self.assertTrue(self.can_reach_location("Garrus: Eye for an Eye"))
        self.assertTrue(self.can_reach_location("Miranda: The Prodigal"))

    def test_collector_base_holds_filler_only(self) -> None:
        for name, loc in LOCATIONS.items():
            if loc.region is Region.COLLECTOR_BASE:
                self.assertEqual(self.location(name).progress_type, LocationProgressType.EXCLUDED, name)

    def test_n7_on_by_default_hub_off(self) -> None:
        names = self.names()
        self.assertIn("N7: Abandoned Mine", names)
        self.assertNotIn("Illium: Medical Scans", names)

    def test_all_dlc_on_by_default(self) -> None:
        names = self.names()
        self.assertIn("Kasumi: Stealing Memory", names)
        self.assertIn("Lair of the Shadow Broker: Complete", names)
        self.assertEqual(len(self.get_items_by_name(DOSSIERS["Zaeed Massani"])), 1)

    def test_recruitment_never_reads_squad_state(self) -> None:
        # LE1 lesson: delivery may one day write in-party / selectable bools (21-44, 207-218), so dossier checks must not
        # read them. Zaeed and Kasumi (bools 44, 37) are the documented interim exception (D5).
        squad_state = set(range(21, 45)) | set(range(207, 219))
        for name in ("Omega: Recruit Mordin", "Omega: Recruit Garrus", "Purgatory: Recruit Jack", "Korlus: Recruit Grunt",
                     "Illium: Recruit Thane", "Illium: Recruit Samara", "Haestrom: Recruit Tali"):
            indices = {int(n) for n in re.findall(r"\d+", LOCATIONS[name].plot)}
            self.assertFalse(indices & squad_state, name)

    def test_codex_on_by_default_and_never_progression(self) -> None:
        codex = [name for name in self.names() if name.startswith("Codex: ")]
        self.assertGreater(len(codex), 60)  # 73 minus the prologue pages the open start skips
        progression = next(item for item in self.multiworld.itempool if item.advancement)
        for name in codex:  # excluded areas (e.g. Arrival) are filler-only through their progress type instead
            location = self.location(name)
            self.assertTrue(location.progress_type == LocationProgressType.EXCLUDED or not location.item_rule(progression), name)

    def test_weapon_pickup_never_holds_its_own_weapon(self) -> None:
        from ..data import WEAPON_PICKUP_ITEM
        for name, weapon in WEAPON_PICKUP_ITEM.items():
            if name not in self.names():
                continue
            own = self.get_item_by_name(weapon)
            self.assertFalse(self.location(name).item_rule(own), name)

    def test_dlc_access_items_gate_their_missions(self) -> None:
        from ..data import FIREWALKER_ITEM
        self.assertEqual(len(self.get_items_by_name(FIREWALKER_ITEM)), 5)
        for item in ("David's Math Test", "Shadow Broker Toenail", "Batarian Genocide"):
            self.assertEqual(len(self.get_items_by_name(item)), 1, item)
        self.collect_all_but(["David's Math Test", FIREWALKER_ITEM])
        self.assertFalse(self.can_reach_location("Project Overlord: Complete"))
        self.collect(self.get_items_by_name(FIREWALKER_ITEM)[:4])
        self.assertTrue(self.can_reach_location("Firewalker: Rosalie Lost"))
        self.assertFalse(self.can_reach_location("Firewalker: Volcano Station"))
    def test_beatable_with_everything(self) -> None:
        self.collect_all_but([])
        self.assertBeatable(True)

    def test_weapons_fill_free_room(self) -> None:
        weapons = [item.name for item in self.multiworld.itempool if item.name in WEAPONS]
        self.assertEqual(len(weapons), len(set(weapons)))
        self.assertGreater(len(weapons), 0)


class TestShipUpgradesReadiness(LE2Helpers):
    options = {"endgame_readiness": "ship_upgrades"}

    def test_victory_needs_only_iff_and_upgrades(self) -> None:
        self.collect_event(EVENT_IFF)
        self.collect_by_name(list(SHIP_UPGRADES))
        self.assertTrue(self.can_reach_location("Victory"))


class TestAllLoyalCountsDLCSquad(LE2Helpers):
    def test_victory_waits_for_kasumi(self) -> None:
        # collect_all_but also collects event items, so build the state from the item pool and sweep the events
        state = CollectionState(self.multiworld)
        for item in self.multiworld.itempool:
            if item.player == self.player and item.name != DOSSIERS["Kasumi Goto"]:
                state.collect(item, True)
        state.sweep_for_advancements()
        self.assertTrue(state.has(loyalty_done("Garrus Vakarian"), self.player))
        self.assertFalse(state.has(loyalty_done("Kasumi Goto"), self.player))
        self.assertFalse(self.location("Victory").can_reach(state))


class TestNoDLC(LE2Helpers):
    options = {"enabled_dlc": []}

    def test_dlc_content_removed(self) -> None:
        names = self.names()
        for name in ("Omega: Recruit Zaeed", "Kasumi: Stealing Memory", "Arrival: Complete", "Firewalker: Prothean Site"):
            self.assertNotIn(name, names)
        self.assertEqual(self.get_items_by_name(DOSSIERS["Kasumi Goto"]), [])

    def test_victory_does_not_wait_for_dlc_squad(self) -> None:
        self.collect_all_but([])
        self.assertBeatable(True)


class TestAssignmentsAll(LE2Helpers):
    options = {"assignments": "all", "start_on_normandy": False}  # no starting dossier to sweep events from

    def test_hub_assignments_follow_their_hub(self) -> None:
        self.assertTrue(self.can_reach_location("Omega: Packages for Ish"))
        self.assertFalse(self.can_reach_location("Illium: Medical Scans"))
        self.assertFalse(self.can_reach_location("Tuchanka: Combustion Manifold"))
        self.collect_event(EVENT_HORIZON)
        self.assertTrue(self.can_reach_location("Illium: Medical Scans"))
        self.assertFalse(self.can_reach_location("Tuchanka: Combustion Manifold"))
        self.collect_event(recruited("Grunt"))
        self.assertTrue(self.can_reach_location("Tuchanka: Combustion Manifold"))
        # the missing scout is found inside Mordin's loyalty mission
        self.assertFalse(self.can_reach_location("Tuchanka: Missing Scout"))
        self.collect_event(recruited("Mordin Solus"))
        self.assertTrue(self.can_reach_location("Tuchanka: Missing Scout"))


class TestMinimal(LE2Helpers):
    options = {"assignments": "off", "enabled_dlc": [], "research": False, "collectibles": False,
               "start_on_normandy": False,
               "intel_total": 10, "intel_required": 10}

    def test_intel_clamped_to_room(self) -> None:
        # 27 locations - 4 excluded - 7 dossiers - 3 upgrades - 4 reserved filler slots = 9
        self.assertEqual(len(self.get_items_by_name(IFF_INTEL)), 9)
        self.assertEqual(self.world.intel_required, 9)
        self.assertEqual(self.world.fill_slot_data()["intel_required"], 9)


class TestPresetStoryFocus(MassEffectLE2TestBase):
    options = options_presets["Story Focus"]


class TestPresetCompletionist(MassEffectLE2TestBase):
    options = options_presets["Completionist"]


class TestLateGame(LE2Helpers):
    def test_research_waits_for_collector_ship_and_loyalty(self) -> None:
        name = "Research: Assault Rifle Damage"
        self.assertIn(name, self.names())
        self.collect_event(EVENT_COLLECTOR_SHIP)
        self.assertFalse(self.can_reach_location(name))
        self.collect_all_but([])
        self.assertTrue(self.can_reach_location(name))

    def test_ship_upgrades_are_never_research_checks(self) -> None:
        # their delivery sets the research "unlocked" bools 5642/5648/5645, which would fake a check
        for loc in LOCATIONS.values():
            self.assertFalse({5642, 5648, 5645} & {int(n) for n in re.findall(r"\d+", loc.plot)})

    def test_squadmate_research_needs_the_squadmate(self) -> None:
        self.assertIn(recruited("Legion"), LOCATIONS["Research: Legion's Sniper Rifle"].needs)


class TestNoResearchOrCollectibles(LE2Helpers):
    options = {"research": False, "collectibles": False}

    def test_removed(self) -> None:
        self.assertFalse(any(n.startswith(("Research: ", "Cabin: ", "Armor: ")) for n in self.names()))


class TestPickups(LE2Helpers):
    def test_safe_pickups_hold_no_progression(self) -> None:
        pickups = [loc for loc in self.multiworld.get_locations(self.player) if LOCATIONS.get(loc.name)
                   and LOCATIONS[loc.name].category == "pickup" and not LOCATIONS[loc.name].excluded]
        self.assertGreater(len(pickups), 200)
        for loc in pickups:
            self.assertFalse(loc.item_rule(self.world.create_item(DOSSIERS["Jack"])), loc.name)
            self.assertTrue(loc.item_rule(self.world.create_item("Credits")), loc.name)

    def test_loyalty_pickups_follow_their_mission(self) -> None:
        name = "Subject Zero: Lobby Credits"
        self.assertEqual(LOCATIONS[name].needs, LOCATIONS["Jack: Subject Zero"].needs)
        self.collect_event(EVENT_HORIZON)
        self.assertFalse(self.can_reach_location(name))
        self.collect_event(recruited("Jack"))
        self.collect(self.get_items_by_name("Progressive Loyalty Mission"))
        self.assertTrue(self.can_reach_location(name))

    def test_arrival_pickups_are_excluded(self) -> None:
        self.assertEqual(self.location("Arrival: Credits 1").progress_type, LocationProgressType.EXCLUDED)

    def test_every_plot_predicate_is_unique(self) -> None:
        seen: dict[int, str] = {}
        for name, loc in LOCATIONS.items():
            for plot in map(int, re.findall(r"\d+", loc.plot)):
                self.assertNotIn(plot, seen, f"{name} and {seen.get(plot)} read the same plot bool")
                seen[plot] = name


class TestCodexOff(LE2Helpers):
    options = {"codex": False}

    def test_no_codex_checks(self) -> None:
        self.assertFalse([name for name in self.names() if name.startswith("Codex: ")])


class TestPickupsOff(LE2Helpers):
    options = {"pickups": "off"}

    def test_removed(self) -> None:
        self.assertFalse(any(LOCATIONS[n].category == "pickup" for n in self.names()))


class TestPickupsAny(LE2Helpers):
    options = {"pickups": "any"}

    def test_pickups_can_hold_progression(self) -> None:
        self.assertTrue(self.location("Horizon: Credits 1").item_rule(self.world.create_item(DOSSIERS["Jack"])))


class TestStartOnNormandy(LE2Helpers):
    options = {"start_on_normandy": True, "assignments": "off", "enabled_dlc": [], "research": False, "collectibles": False,
               "intel_total": 10, "intel_required": 10}

    def test_prologue_removed_and_one_dossier_given(self) -> None:
        names = self.names()
        self.assertFalse({"Lazarus Station: Awakening", "Freedom's Progress: Complete"} & names)
        self.assertFalse(any(n.startswith(("Lazarus Station: ", "Freedom's Progress: ")) for n in names))
        start = self.world.starting_dossier
        self.assertIn(start, {DOSSIERS[name] for name in PHASE_1})
        self.assertIn(start, {item.name for item in self.multiworld.precollected_items[self.player]})
        self.assertEqual(self.get_items_by_name(start), [])
        self.assertEqual(self.world.fill_slot_data()["starting_dossier"], start)

    def test_intel_clamped_to_room(self) -> None:
        # 25 locations - 4 excluded - 6 pooled dossiers - 3 upgrades - 4 reserved filler slots = 8
        self.assertEqual(len(self.get_items_by_name(IFF_INTEL)), 8)
