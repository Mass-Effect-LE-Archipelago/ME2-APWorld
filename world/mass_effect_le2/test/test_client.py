import unittest
from dataclasses import dataclass

from ..client import (DOSSIER_BOOL_BASE, IDENTITY_PLOT_INTS, LOCATION_PREDICATES, RECEIVED_INDEX_PLOT_INT,
                      BridgeConnection, BridgeProtocolError, GameNotReadyError, evaluate_locations, item_op,
                      notice_lines, parse_plot_predicate, seed_identity, sync_received_items)
from ..data import DOSSIERS, ITEM_NAME_TO_ID, ITEMS, LOCATION_NAME_TO_ID


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
        self.assertEqual(item_op(ITEM_NAME_TO_ID["Thanix Cannon"]), "SHIP 238 5645")

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
        bridge, _ = self.bridge("ERR noworld", "ERR notallowed")
        with self.assertRaises(GameNotReadyError):
            bridge.get_int(1)
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
