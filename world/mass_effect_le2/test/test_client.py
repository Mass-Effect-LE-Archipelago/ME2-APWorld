import unittest
from dataclasses import dataclass

from ..client import (CAREER_MARKER_PLOT_BOOL, DOSSIER_BOOL_BASE, GOAL_PLOT_BOOL, IDENTITY_PLOT_INTS, IdentityMismatchError, ME2Context, LOCATION_PREDICATES, RECEIVED_INDEX_PLOT_INT,
                      BridgeConnection, BridgeProtocolError, GameNotReadyError, evaluate_locations, item_op,
                      notice_lines, parse_plot_predicate, seed_identity, sync_received_items,
                      DOSSIER_JOURNAL_BOOLS, sync_dossier_journals, SALVAGE_AREA_IDS, SALVAGE_BOUGHT_INT_BASE,
                      SALVAGE_CAP_INT_BASE, SALVAGE_TIER_DISABLE_BASE, sync_salvage, SHIP_UPGRADE_BOOLS, sync_ship_upgrades)
from ..data import DOSSIERS, FEMALE_PLOT_BOOL, ITEM_NAME_TO_ID, ITEMS, LOCATION_NAME_TO_ID, ME1_HISTORY_BOOLS


@dataclass
class Received:
    item: int


class FakeBridge:
    """The bridge's TXN contract (tools/le2apbridge/PROTOCOL.md) over an in-memory plot table."""

    def __init__(self) -> None:
        self.bools: dict[int, bool] = {}
        self.ints: dict[int, int] = {}
        self.ops: list[str] = []
        self.fail_after_apply = False  # simulates a lost reply: applied in game, error on the client side

    def get_bools(self, indices):
        return {i: self.bools.get(i, False) for i in indices}

    def get_int(self, index):
        return self.ints.get(index, 0)

    def transaction(self, index, op):
        current = self.ints.get(RECEIVED_INDEX_PLOT_INT, 0)
        if index < current:
            return False
        if index > current:
            raise BridgeProtocolError(f"ERR gap {current}")
        self.ops.append(op)
        self.ints[RECEIVED_INDEX_PLOT_INT] = index + 1
        if self.fail_after_apply:
            self.fail_after_apply = False
            raise GameNotReadyError("ERR timeout")
        return True


class TestDelivery(unittest.TestCase):
    def test_every_item_has_a_delivery(self) -> None:
        for name, item_id in ITEM_NAME_TO_ID.items():
            op = item_op(item_id)
            self.assertTrue(op, name)
            self.assertEqual(op == "NONE", ITEMS[name].grant is None, name)

    def test_dossier_sets_its_mod_flag(self) -> None:
        self.assertEqual(item_op(ITEM_NAME_TO_ID[DOSSIERS["Mordin Solus"]]), f"FLAG {DOSSIER_BOOL_BASE}")
        self.assertEqual(item_op(ITEM_NAME_TO_ID["Thanix Cannon"]), "SHIP 238")

    def test_dossier_journals_are_set_until_recruited(self) -> None:
        # Mordin and Garrus received (AustinME2, 2026-10-25): journals 551/548 set; Grunt's dossier is ignored once
        # recruited (bool 5812); Zaeed has no journal bool; a second poll writes nothing.
        class Bridge(FakeBridge):
            def set_bool(self, index, value):
                self.bools[index] = value

        bridge = Bridge()
        bridge.bools[5812] = True
        received = [Received(ITEM_NAME_TO_ID[DOSSIERS[m]]) for m in ("Mordin Solus", "Garrus Vakarian", "Grunt", "Zaeed Massani")]
        self.assertEqual(sync_dossier_journals(bridge, received), [548, 551])
        self.assertFalse(bridge.bools.get(552, False))
        self.assertEqual(sync_dossier_journals(bridge, received), [])

    def test_bridge_journal_allowlist_matches_client(self) -> None:
        import pathlib
        import re
        path = pathlib.Path(__file__).resolve().parents[3] / "tools" / "le2apbridge" / "LE2APBridge" / "Bridge.cpp"
        if not path.exists():
            self.skipTest("bridge source not beside this world (packaged .apworld)")
        listed = re.search(r"DossierJournalBools\[\] = \{([^}]*)\}", path.read_text()).group(1)
        self.assertEqual({int(n) for n in listed.split(",")}, {j for j, _ in DOSSIER_JOURNAL_BOOLS.values()})

    class SalvageBridge(FakeBridge):
        def set_bool(self, index, value):
            self.bools[index] = value

        def get_ints(self, indices):
            return {i: self.ints.get(i, 0) for i in indices}

        def take_int(self, index):
            value = self.ints.get(index, 0)
            self.ints[index] = 0
            return value

        def set_int(self, index, value):
            self.ints[index] = value

    def test_salvage_caps_follow_done_missions_and_open_pickups(self) -> None:
        from ..data import SALVAGE_MISSIONS
        bridge = self.SalvageBridge()
        korlus = next(k for k, (area, _, _) in enumerate(SALVAGE_MISSIONS) if area == "grunt_acq")
        ids = SALVAGE_AREA_IDS["grunt_acq"]
        open_locations = set(ids[6:])  # 4 of Korlus's pickups still open
        self.assertEqual(sync_salvage(bridge, True, 2, open_locations), [])
        self.assertEqual(bridge.ints.get(SALVAGE_CAP_INT_BASE + korlus, 0), 0)  # Korlus not done yet
        self.assertEqual([bridge.bools.get(SALVAGE_TIER_DISABLE_BASE + t, False) for t in range(5)], [True, True, False, True, True])
        bridge.bools[5812] = True  # Korlus: Recruit Grunt
        sync_salvage(bridge, True, 2, open_locations)
        self.assertEqual(bridge.ints[SALVAGE_CAP_INT_BASE + korlus], 4)
        bridge.ints[SALVAGE_BOUGHT_INT_BASE + korlus] = 2  # two purchases at the research terminal
        bought = sync_salvage(bridge, True, 2, open_locations)
        self.assertEqual(bought, sorted(open_locations)[:2])
        self.assertEqual(bridge.ints[SALVAGE_BOUGHT_INT_BASE + korlus], 0)
        self.assertEqual(bridge.ints[SALVAGE_CAP_INT_BASE + korlus], 2)

    def test_ship_upgrades_follow_items_not_research(self) -> None:
        # D21: research set Thanix's applied bool without the item -> cleared; the armor item arrived -> set
        bridge = self.SalvageBridge()
        bridge.bools[238] = True
        received = [Received(ITEM_NAME_TO_ID["Heavy Ship Armor"])]
        self.assertEqual(sorted(sync_ship_upgrades(bridge, received)), [237, 238])
        self.assertEqual((bridge.bools[237], bridge.bools[238], bridge.bools.get(236, False)), (True, False, False))
        self.assertEqual(sync_ship_upgrades(bridge, received), [])

    def test_bridge_ship_allowlist_matches_client(self) -> None:
        import pathlib
        import re
        path = pathlib.Path(__file__).resolve().parents[3] / "tools" / "le2apbridge" / "LE2APBridge" / "Bridge.cpp"
        if not path.exists():
            self.skipTest("bridge source not beside this world (packaged .apworld)")
        listed = re.search(r"ShipAppliedBools\[\] = \{([^}]*)\}", path.read_text()).group(1)
        self.assertEqual({int(n) for n in listed.split(",")}, set(SHIP_UPGRADE_BOOLS.values()))

    def test_salvage_off_disables_every_tier(self) -> None:
        bridge = self.SalvageBridge()
        self.assertEqual(sync_salvage(bridge, False, 2, set()), [])
        self.assertTrue(all(bridge.bools[SALVAGE_TIER_DISABLE_BASE + t] for t in range(5)))

    def test_salvage_json_matches_data(self) -> None:
        import pathlib
        import sys
        tools = pathlib.Path(__file__).resolve().parents[3] / "tools"
        if not (tools / "le2mod" / "salvage.json").exists():
            self.skipTest("tools not beside this world (packaged .apworld)")
        sys.path.insert(0, str(tools))
        try:
            from export_salvage import salvage_json
        finally:
            sys.path.remove(str(tools))
        self.assertEqual((tools / "le2mod" / "salvage.json").read_text(), salvage_json())

    def test_bridge_salvage_ranges_match_client(self) -> None:
        import pathlib
        import re
        from ..data import SALVAGE_MISSIONS
        path = pathlib.Path(__file__).resolve().parents[3] / "tools" / "le2apbridge" / "LE2APBridge" / "Bridge.cpp"
        if not path.exists():
            self.skipTest("bridge source not beside this world (packaged .apworld)")
        source = path.read_text()
        bought = re.search(r"SalvageBoughtMin = (\d+), SalvageBoughtMax = (\d+)", source).groups()
        cap = re.search(r"SalvageCapMin = (\d+), SalvageCapMax = (\d+)", source).groups()
        self.assertEqual(int(bought[0]), SALVAGE_BOUGHT_INT_BASE)
        self.assertGreaterEqual(int(bought[1]), SALVAGE_BOUGHT_INT_BASE + len(SALVAGE_MISSIONS) - 1)
        self.assertEqual(int(cap[0]), SALVAGE_CAP_INT_BASE)
        self.assertGreaterEqual(int(cap[1]), SALVAGE_CAP_INT_BASE + len(SALVAGE_MISSIONS) - 1)

    def test_dossier_flags_match_the_mod_gates(self) -> None:
        # le2mod 0.0.4 gates each recruitment on these bools (tools/le2mod/Program.cs Gates/HubGates)
        expected = {"Mordin Solus": 21000, "Garrus Vakarian": 21001, "Jack": 21002, "Grunt": 21003, "Thane Krios": 21004,
                    "Samara": 21005, "Tali'Zorah vas Neema": 21006, "Zaeed Massani": 21007, "Kasumi Goto": 21008}
        for member, flag in expected.items():
            self.assertEqual(item_op(ITEM_NAME_TO_ID[DOSSIERS[member]]), f"FLAG {flag}", member)

    def test_sync_applies_from_the_saved_index(self) -> None:
        bridge = FakeBridge()
        items = [Received(ITEM_NAME_TO_ID["Credits"]), Received(ITEM_NAME_TO_ID[DOSSIERS["Jack"]])]
        self.assertEqual(len(sync_received_items(bridge, items)), 2)
        self.assertEqual(bridge.get_int(RECEIVED_INDEX_PLOT_INT), 2)
        self.assertEqual(sync_received_items(bridge, items), [])
        self.assertEqual(len(bridge.ops), 2)

    def test_lost_reply_is_not_granted_twice(self) -> None:
        bridge = FakeBridge()
        items = [Received(ITEM_NAME_TO_ID["Credits"])] * 3
        bridge.fail_after_apply = True
        with self.assertRaises(GameNotReadyError):
            sync_received_items(bridge, items)
        sync_received_items(bridge, items)
        self.assertEqual(len(bridge.ops), 3)

    def test_older_save_replays_missing_items(self) -> None:
        bridge = FakeBridge()
        items = [Received(ITEM_NAME_TO_ID["Credits"])] * 4
        sync_received_items(bridge, items)
        bridge.ints[RECEIVED_INDEX_PLOT_INT] = 1  # load an older save
        sync_received_items(bridge, items)
        self.assertEqual(len(bridge.ops), 7)

    def test_identity_is_stable_and_nonzero(self) -> None:
        self.assertEqual(seed_identity("abc", 0, 1), seed_identity("abc", 0, 1))
        self.assertNotEqual(seed_identity("abc", 0, 1), seed_identity("abc", 0, 2))
        self.assertTrue(all(value > 0 for value in seed_identity("", 0, 0)))
        self.assertNotIn(RECEIVED_INDEX_PLOT_INT, IDENTITY_PLOT_INTS)


class TestChecks(unittest.TestCase):
    def test_every_location_predicate_parses(self) -> None:
        self.assertEqual(len(LOCATION_PREDICATES), len(LOCATION_NAME_TO_ID))
        self.assertEqual(parse_plot_predicate("int 23 >= 4").threshold, 4)

    def test_or_predicates_and_filtering(self) -> None:
        bridge = FakeBridge()
        bridge.bools[1256] = True  # IFF acquired (alternative of the Derelict Reaper check)
        iff = LOCATION_NAME_TO_ID["Derelict Reaper: Acquire the IFF"]
        self.assertIn(iff, evaluate_locations(bridge))
        self.assertEqual(evaluate_locations(bridge, {LOCATION_NAME_TO_ID["Horizon: Complete"]}), set())


class TestPipe(unittest.TestCase):
    class FakePipe:
        def __init__(self, replies):
            self.replies = list(replies)
            self.sent: list[bytes] = []

        def write(self, data):
            self.sent.append(data)

        def read(self, _size):
            return self.replies.pop(0).encode("ascii")

        def close(self):
            pass

    def bridge(self, *replies):
        pipe = self.FakePipe(replies)
        return BridgeConnection(opener=lambda *_: pipe), pipe

    def test_txn_replies(self) -> None:
        bridge, pipe = self.bridge("OK applied", "OK done")
        self.assertTrue(bridge.transaction(0, "NONE"))
        self.assertFalse(bridge.transaction(0, "NONE"))
        self.assertEqual(pipe.sent[0], b"TXN 0 NONE")

    def test_not_ready_and_errors(self) -> None:
        bridge, _ = self.bridge("ERR noworld", "ERR notready", "ERR notallowed")
        with self.assertRaises(GameNotReadyError):
            bridge.get_int(1)
        with self.assertRaises(GameNotReadyError):
            bridge.identity()
        with self.assertRaises(BridgeProtocolError):
            bridge.get_int(1)

    def test_batched_bools(self) -> None:
        bridge, pipe = self.bridge("OK 10")
        self.assertEqual(bridge.get_bools([5, 6]), {5: True, 6: False})
        self.assertEqual(pipe.sent[0], b"GETBS 5 6")

    def test_hello(self) -> None:
        bridge, _ = self.bridge("OK 1 LE2")
        self.assertEqual(bridge.hello(), 1)

    def test_notice_wrapping(self) -> None:
        self.assertTrue(all(len(line) <= 40 for line in notice_lines("Received Dossier: The Professor from Someone " * 3)))


class TestBinding(unittest.TestCase):
    class Bridge(FakeBridge):
        def __init__(self) -> None:
            super().__init__()
            self.bools[CAREER_MARKER_PLOT_BOOL] = True  # a career started with the mod

        def get_bool(self, index):
            return self.bools.get(index, False)

        def identity(self):
            return tuple(self.ints.get(i, 0) for i in IDENTITY_PLOT_INTS)

        def bind_identity(self, seed, slot):
            self.ints.update(zip(IDENTITY_PLOT_INTS, (seed, slot)))

    def context(self, bridge):
        context = ME2Context.__new__(ME2Context)  # only the attributes _check_identity reads
        context.bridge, context.identity, context._mismatch_reported, context.notices_enabled = bridge, (7, 9), False, False
        return context

    def test_fresh_save_binds(self) -> None:
        bridge = self.Bridge()
        self.context(bridge)._check_identity()
        self.assertEqual(bridge.identity(), (7, 9))

    def test_menu_world_is_not_bound(self) -> None:
        # the bridge answers "ERR notready" until a save is loaded (no player pawn on the main menu)
        class MenuBridge(self.Bridge):
            def identity(self):
                raise GameNotReadyError("ID: ERR notready")

        bridge = MenuBridge()
        with self.assertRaises(GameNotReadyError):
            self.context(bridge)._check_identity()
        self.assertEqual(bridge.ints, {})

    def test_vanilla_save_is_not_bound(self) -> None:
        bridge = self.Bridge()
        bridge.bools[CAREER_MARKER_PLOT_BOOL] = False  # e.g. Vector's career, loaded by mistake (2026-10-26)
        with self.assertRaises(IdentityMismatchError):
            self.context(bridge)._check_identity()
        self.assertEqual(bridge.identity(), (0, 0))

    def test_save_with_progress_is_not_bound(self) -> None:
        bridge = self.Bridge()
        for plot in (5812, 5813, 5814, 5815, 5817, 5818):  # six recruitments done
            bridge.bools[plot] = True
        with self.assertRaises(IdentityMismatchError):
            self.context(bridge)._check_identity()
        self.assertEqual(bridge.identity(), (0, 0))

    def test_post_game_save_is_refused(self) -> None:
        bridge = self.Bridge()
        bridge.bools[GOAL_PLOT_BOOL] = True
        with self.assertRaises(IdentityMismatchError):
            self.context(bridge)._check_identity()
        self.assertEqual(bridge.identity(), (0, 0))


class TestME1History(unittest.TestCase):
    CHOICES = {"me1_virmire_survivor": "ashley", "me1_romance": "none", "me1_rachni": "saved", "me1_wrex": "alive",
               "me1_council": "saved", "me1_human_councilor": "anderson"}

    class Bridge(TestBinding.Bridge):
        def set_history_bool(self, index, value):
            # the bridge's guard (PROTOCOL.md HIST): allowlist, unbound save only
            from ..data import ME1_HISTORY_BOOLS
            assert index in ME1_HISTORY_BOOLS and self.identity() == (0, 0)
            self.bools[index] = value

    def bind(self, choices, female=False):
        bridge = self.Bridge()
        bridge.bools[FEMALE_PLOT_BOOL] = female
        context = TestBinding.context(self, bridge)
        context.me1_history = choices
        context._check_identity()
        self.assertEqual(bridge.identity(), (7, 9))
        return bridge.bools

    def test_defaults_written_before_binding(self) -> None:
        bools = self.bind(self.CHOICES)
        self.assertEqual({b: bools[b] for b in (1541, 1540, 1926, 7447, 3151, 7448, 3752, 1554, 1553, 1556, 1555)},
                         {1541: True, 1540: False, 1926: True, 7447: True, 3151: True, 7448: True, 3752: False,
                          1554: True, 1553: False, 1556: True, 1555: False})

    def test_impossible_romance_falls_back_to_none(self) -> None:
        bools = self.bind({**self.CHOICES, "me1_romance": "kaidan"})  # male Shepard, Ashley survived
        self.assertTrue(bools[1926])
        self.assertFalse(bools[1529])
        bools = self.bind({**self.CHOICES, "me1_virmire_survivor": "kaidan", "me1_romance": "kaidan"}, female=True)
        self.assertTrue(bools[1529])
        self.assertFalse(bools[1926])

    def test_old_seed_writes_nothing(self) -> None:
        bools = self.bind(None)
        self.assertFalse(any(b in ME1_HISTORY_BOOLS for b in bools))

    def test_bridge_allowlist_matches_data(self) -> None:
        import pathlib
        import re
        path = pathlib.Path(__file__).resolve().parents[3] / "tools" / "le2apbridge" / "LE2APBridge" / "Bridge.cpp"
        if not path.exists():
            self.skipTest("bridge source not beside this world (packaged .apworld)")
        source = path.read_text()
        listed = re.search(r"HistoryBools\[\] = \{([^}]*)\}", source).group(1)
        self.assertEqual({int(n) for n in listed.split(",")}, ME1_HISTORY_BOOLS)
