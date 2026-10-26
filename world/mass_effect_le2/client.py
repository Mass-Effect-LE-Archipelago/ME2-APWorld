"""Archipelago client for Mass Effect Legendary Edition 2.

The client talks to LE2APBridge.asi over its local named pipe (protocol: tools/le2apbridge/PROTOCOL.md). Pipe I/O is
kept behind :class:`BridgeConnection` so the game-facing behavior can be tested without either LE2 or a server.

Differences from the LE1 client, from the feasibility plan's "Runtime contract improvements":
- the save carries the seed/slot identity (two plot ints) and the client refuses to touch a save of another seed;
- every received item is delivered as one indexed transaction (TXN): the bridge grants it and advances the save's
  received index together on the game thread, and a retried TXN for an index already applied is a no-op.
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import contextlib
import logging
import re
import unicodedata
import zlib
from dataclasses import dataclass
from typing import BinaryIO, Callable, Protocol, Sequence

import colorama

import Utils
from CommonClient import ClientCommandProcessor, CommonContext, get_base_parser, gui_enabled, handle_url_arg, server_loop
from NetUtils import ClientStatus

from .data import (DLC_ACCESS_BOOLS, DLC_ACCESS_ITEMS, DOSSIERS, FEMALE_PLOT_BOOL, FIREWALKER_BOOL_BASE, FIREWALKER_ITEM,
                   FIREWALKER_MISSIONS, LOYALTY_BOOL_BASE, LOYALTY_LOCATION, PROGRESSIVE_LOYALTY, RECRUIT_LOCATION, IFF_INTEL, ITEM_NAME_TO_ID, ITEMS, LOCATION_NAME_TO_ID, LOCATIONS, SALVAGE_MISSIONS,
                   SALVAGE_PICKUPS, SALVAGE_PRICES, SHIP_UPGRADES,
                   WEAPONS, me1_history_writes)
from .world import MassEffectLE2World

logger = logging.getLogger("ME2Client")

PIPE_NAME = r"\\.\pipe\LE2APBridge"
PROTOCOL_VERSION = 4
# AP-owned plot IDs (docs/DECISIONS.md D2, pending the collision audit): bools 21000-21999, ints 2100-2199.
RECEIVED_INDEX_PLOT_INT = 2100  # read by the client; written only by the bridge inside TXN
IDENTITY_PLOT_INTS = (2101, 2102)  # seed and slot identity of the save (0, 0 = not yet bound)
DOSSIER_BOOL_BASE = 21000  # + dossier index: the mod's galaxy-map conditional for that recruitment mission
IFF_OPEN_PLOT_BOOL = 21100  # set by the client once enough Reaper IFF Intel arrived: opens the Derelict Reaper
CAREER_MARKER_PLOT_BOOL = 21999  # set by le2mod's character-creator chain (0.0.7): only such saves may be bound
BIND_MAX_TRUE_LOCATIONS = 5  # second guard: a fresh career has (almost) no locations done
GOAL_PLOT_BOOL = 1456  # "Game done" (me2_plot_db); candidate until the ending is observed (D11)
POLL_INTERVAL_SECONDS = 2.0
BATCH_READ_MAX = 64  # GETBS indices per request
NOTICE_LINE_CHARS = 40
NOTICES_PER_POLL = 3

# Ship upgrades (D21): the "applied" bool the suicide mission reads (me2_plot_db Normandy.Upgrades.*). Research never
# sets it (live read 2026-10-26: only treasure bool 1183 and tech int 114 change), so the item writes it and the client
# keeps it equal to "item received" each poll; the vanilla research stays a check and grants nothing.
SHIP_UPGRADE_BOOLS = {
    "Heavy Ship Armor": 237,
    "Multicore Shielding": 236,
    "Thanix Cannon": 238,
}
# Resource bundles: bridge RES type (SDK enum EInventoryResourceTypes, D12) and amount.
RESOURCES = {
    "Credits": (0, 5000),
    "Element Zero": (4, 500),
    "Iridium": (5, 2500),
    "Palladium": (6, 2500),
    "Platinum": (7, 2500),
}


class BridgeError(Exception):
    """Base class for bridge transport and protocol failures."""


class GameNotReadyError(BridgeError):
    """The bridge is running, but LE2 has no world, save or player loaded yet."""


class BridgeProtocolError(BridgeError):
    """The bridge rejected a request or returned a malformed reply."""


class IdentityMismatchError(BridgeError):
    """The loaded save belongs to another seed or slot."""


PipeOpener = Callable[[str, str, int], BinaryIO]
NOT_READY = {"ERR noworld", "ERR noplayer", "ERR notready"}


class BridgeConnection:
    """Small reconnecting request/reply client for LE2APBridge's named pipe."""

    def __init__(self, pipe_name: str = PIPE_NAME, opener: PipeOpener = open) -> None:
        self.pipe_name = pipe_name
        self._opener = opener
        self._pipe: BinaryIO | None = None

    def close(self) -> None:
        if self._pipe is not None:
            with contextlib.suppress(OSError):
                self._pipe.close()
            self._pipe = None

    def request(self, request: str) -> str:
        """Send one ASCII request, reconnecting once after a transport failure. Every request is safe to repeat: reads
        are pure, and TXN is idempotent per received index."""
        if not request.isascii():
            raise ValueError("bridge requests must be ASCII")
        last_error: OSError | None = None
        for _attempt in range(2):
            try:
                if self._pipe is None:
                    self._pipe = self._opener(self.pipe_name, "r+b", 0)
                self._pipe.write(request.encode("ascii"))
                reply = self._pipe.read(4096).decode("ascii")
                if not reply:
                    raise OSError("bridge closed the pipe without replying")
                return self._parse_reply(request, reply)
            except (OSError, UnicodeDecodeError) as error:
                last_error = error if isinstance(error, OSError) else OSError(str(error))
                self.close()
        raise BridgeError(f"bridge request failed after reconnect: {last_error}") from last_error

    @staticmethod
    def _parse_reply(request: str, reply: str) -> str:
        if reply in NOT_READY or reply == "ERR timeout":
            raise GameNotReadyError(f"{request.split()[0]}: {reply}")
        if reply.startswith("ERR "):
            raise BridgeProtocolError(f"{request!r}: {reply}")
        if reply == "OK":
            return ""
        if reply.startswith("OK "):
            return reply[3:]
        raise BridgeProtocolError(f"{request!r}: malformed reply {reply!r}")

    def hello(self) -> int:
        """Protocol handshake: the bridge's protocol version (it must equal PROTOCOL_VERSION)."""
        fields = self.request(f"HELLO {PROTOCOL_VERSION}").split()
        if len(fields) < 2 or fields[1] != "LE2" or not fields[0].isdigit():
            raise BridgeProtocolError(f"HELLO: unexpected reply {fields!r}")
        return int(fields[0])

    def get_bool(self, index: int) -> bool:
        value = self.request(f"GETB {index}")
        if value not in {"0", "1"}:
            raise BridgeProtocolError(f"GETB {index}: invalid bool {value!r}")
        return value == "1"

    def get_bools(self, indices: Sequence[int]) -> dict[int, bool]:
        """Many bools in few requests (GETBS answers one 0/1 character per index, in order)."""
        values: dict[int, bool] = {}
        for start in range(0, len(indices), BATCH_READ_MAX):
            chunk = indices[start:start + BATCH_READ_MAX]
            reply = self.request("GETBS " + " ".join(map(str, chunk)))
            if len(reply) != len(chunk) or set(reply) - {"0", "1"}:
                raise BridgeProtocolError(f"GETBS: invalid reply {reply!r}")
            values.update(zip(chunk, (char == "1" for char in reply)))
        return values

    def get_int(self, index: int) -> int:
        value = self.request(f"GETI {index}")
        try:
            return int(value)
        except ValueError as error:
            raise BridgeProtocolError(f"GETI {index}: invalid int {value!r}") from error

    def set_bool(self, index: int, value: bool) -> None:
        self.request(f"SETB {index} {int(value)}")

    def get_ints(self, indices: Sequence[int]) -> dict[int, int]:
        """Many ints in few requests (protocol 4 GETIS: space-separated values, in order)."""
        values: dict[int, int] = {}
        for start in range(0, len(indices), BATCH_READ_MAX):
            chunk = indices[start:start + BATCH_READ_MAX]
            fields = self.request("GETIS " + " ".join(map(str, chunk))).split()
            if len(fields) != len(chunk):
                raise BridgeProtocolError(f"GETIS: invalid reply {fields!r}")
            values.update(zip(chunk, map(int, fields)))
        return values

    def take_int(self, index: int) -> int:
        """Read a salvage purchase counter and zero it in the same game-thread step (protocol 4 TAKEI)."""
        return int(self.request(f"TAKEI {index}"))

    def set_int(self, index: int, value: int) -> None:
        self.request(f"SETI {index} {value}")

    def identity(self) -> tuple[int, int]:
        fields = self.request("ID").split()
        if len(fields) != 2:
            raise BridgeProtocolError(f"ID: invalid reply {fields!r}")
        return int(fields[0]), int(fields[1])

    def bind_identity(self, seed: int, slot: int) -> None:
        """Write the identity into a fresh save (the bridge refuses if one is already there)."""
        self.request(f"IDSET {seed} {slot}")

    def set_history_bool(self, index: int, value: bool) -> None:
        """Write one ME1-history plot bool (the bridge allows only those, and only on an unbound save)."""
        self.request(f"HIST {index} {int(value)}")

    def transaction(self, index: int, op: str) -> bool:
        """Apply item `index` with `op` once. True if this call applied it, False if the save already had it."""
        reply = self.request(f"TXN {index} {op}")
        if reply == "applied":
            return True
        if reply == "done":
            return False
        raise BridgeProtocolError(f"TXN {index} {op}: unexpected reply {reply!r}")

    def note(self, text: str) -> None:
        self.request(f"NOTE {notice_text(text)}")


def notice_text(text: str) -> str:
    """ASCII and single-line, so any slot or item name fits the bridge's NOTE request."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join("".join(char if char.isprintable() else " " for char in folded).split()) or "?"


def notice_lines(text: str, width: int = NOTICE_LINE_CHARS) -> list[str]:
    lines: list[str] = []
    for word in notice_text(text).split(" "):
        for start in range(0, len(word), width):
            chunk = word[start:start + width]
            if lines and len(lines[-1]) + 1 + len(chunk) <= width:
                lines[-1] += " " + chunk
            else:
                lines.append(chunk)
    return lines


# ---------------------------------------------------------------------------------------------------------- checks


@dataclass(frozen=True)
class PlotPredicate:
    kind: str
    indices: tuple[int, ...]
    threshold: int | None = None


_BOOL_PREDICATE = re.compile(r"^bool\s+(\d+(?:\s+or\s+\d+)*)$", re.IGNORECASE)
_INT_PREDICATE = re.compile(r"^int\s+(\d+)\s*>=\s*(-?\d+)$", re.IGNORECASE)


def parse_plot_predicate(description: str) -> PlotPredicate:
    if match := _BOOL_PREDICATE.fullmatch(description.strip()):
        return PlotPredicate("bool", tuple(int(v) for v in re.split(r"\s+or\s+", match.group(1), flags=re.IGNORECASE)))
    if match := _INT_PREDICATE.fullmatch(description.strip()):
        return PlotPredicate("int", (int(match.group(1)),), int(match.group(2)))
    raise ValueError(f"unsupported plot predicate {description!r}")


LOCATION_PREDICATES = {LOCATION_NAME_TO_ID[name]: parse_plot_predicate(loc.plot) for name, loc in LOCATIONS.items()}
PREDICATE_BOOLS = sorted({i for p in LOCATION_PREDICATES.values() if p.kind == "bool" for i in p.indices})


class PlotReader(Protocol):
    def get_bools(self, indices: Sequence[int]) -> dict[int, bool]: ...

    def get_int(self, index: int) -> int: ...


def evaluate_locations(bridge: PlotReader, locations: set[int] | None = None) -> set[int]:
    """Location IDs whose predicate holds now (only those in `locations` when given)."""
    wanted = {lid: p for lid, p in LOCATION_PREDICATES.items() if locations is None or lid in locations}
    bools = bridge.get_bools(sorted({i for p in wanted.values() if p.kind == "bool" for i in p.indices}))
    true: set[int] = set()
    for location_id, predicate in wanted.items():
        if predicate.kind == "bool":
            if any(bools[i] for i in predicate.indices):
                true.add(location_id)
        elif bridge.get_int(predicate.indices[0]) >= (predicate.threshold or 0):
            true.add(location_id)
    return true


# ------------------------------------------------------------------------------------------------------- delivery

DOSSIER_IDS = {ITEM_NAME_TO_ID[name]: i for i, name in enumerate(DOSSIERS.values())}
IFF_INTEL_ID = ITEM_NAME_TO_ID[IFF_INTEL]
DLC_ACCESS_FLAGS = {ITEM_NAME_TO_ID[item]: DLC_ACCESS_BOOLS[key] for key, item in DLC_ACCESS_ITEMS.items()}
FIREWALKER_ID = ITEM_NAME_TO_ID[FIREWALKER_ITEM]


def item_op(item_id: int, copies_before: int = 0) -> str:
    """The TXN operation that delivers one item (the bridge validates every target against its allowlist)."""
    if item_id in DOSSIER_IDS:
        return f"FLAG {DOSSIER_BOOL_BASE + DOSSIER_IDS[item_id]}"
    if item_id in DLC_ACCESS_FLAGS:
        return f"FLAG {DLC_ACCESS_FLAGS[item_id]}"
    if item_id == FIREWALKER_ID:  # progressive: the n-th copy opens the n-th Firewalker mission
        return f"FLAG {FIREWALKER_BOOL_BASE + min(copies_before, len(FIREWALKER_MISSIONS) - 1) + 1}"
    name = next((n for n, data_id in ITEM_NAME_TO_ID.items() if data_id == item_id), None)
    if name in SHIP_UPGRADES:
        return f"SHIP {SHIP_UPGRADE_BOOLS[name]}"
    if name in WEAPONS:
        return f"WEAPON {WEAPONS[name]}"
    if name in RESOURCES:
        kind, amount = RESOURCES[name]
        return f"RES {kind} {amount}"
    if name is not None and ITEMS[name].grant is None:
        return "NONE"  # counted by the client (Reaper IFF Intel)
    raise ValueError(f"no delivery for item {item_id}")


def seed_identity(seed_name: str, team: int, slot: int) -> tuple[int, int]:
    """Two positive 31-bit ints naming this seed and slot, stored in the save (never 0, which means unbound)."""
    return (zlib.crc32(seed_name.encode("utf-8")) & 0x7FFF_FFFF) or 1, ((team << 16) | slot) or 1


class ItemBridge(Protocol):
    def get_int(self, index: int) -> int: ...

    def transaction(self, index: int, op: str) -> bool: ...


class ReceivedItem(Protocol):
    item: int


def sync_received_items(bridge: ItemBridge, received: Sequence[ReceivedItem], log: logging.Logger = logger) -> list[int]:
    """Deliver every item after the save's received index, one transaction each; returns the item IDs applied now.

    A TXN whose reply was lost is simply sent again: the bridge answers "done" for an index the save already has."""
    start = bridge.get_int(RECEIVED_INDEX_PLOT_INT)
    if start < 0:
        raise BridgeProtocolError(f"save has a negative received index {start}")
    if start > len(received):
        log.warning("Save received index %s is ahead of the server's %s items; leaving it unchanged", start, len(received))
        return []
    applied: list[int] = []
    for index in range(start, len(received)):
        copies_before = sum(1 for earlier in received[:index] if earlier.item == received[index].item)
        if bridge.transaction(index, item_op(received[index].item, copies_before)):
            applied.append(received[index].item)
    return applied


# Vanilla "dossier received" state (me2_plot_db Journals.SquadMember_Acquisition.*, set by TIM's transitions 2371/2372),
# which the hub recruit starts and the journal read, and each recruitment's done bool (the location rule). The open
# start skips TIM's delivery, so the client sets the journal bool for every received dossier not yet recruited. The DLC
# recruits (Zaeed, Kasumi) have no such state: their DLC flag is already set.
DOSSIER_JOURNAL_BOOLS = {"Mordin Solus": (551, 5814), "Garrus Vakarian": (548, 5813), "Jack": (545, 5815),
                         "Grunt": (552, 5812), "Thane Krios": (549, 5818), "Samara": (553, 5819),
                         "Tali'Zorah vas Neema": (550, 5817)}
DOSSIER_ITEM_JOURNAL = {ITEM_NAME_TO_ID[DOSSIERS[member]]: pair for member, pair in DOSSIER_JOURNAL_BOOLS.items()}


def sync_dossier_journals(bridge: "BridgeConnection", received: Sequence[ReceivedItem], log: logging.Logger = logger) -> list[int]:
    """Set the vanilla journal bool of each received dossier whose recruitment is not done; returns the bools set."""
    pairs = {DOSSIER_ITEM_JOURNAL[item.item] for item in received if item.item in DOSSIER_ITEM_JOURNAL}
    if not pairs:
        return []
    state = bridge.get_bools(sorted({b for pair in pairs for b in pair}))
    written = [journal for journal, done in sorted(pairs) if not state[journal] and not state[done]]
    for journal in written:
        bridge.set_bool(journal, True)
        log.info("Dossier journal entry %s set", journal)
    return written


# Missed-checks salvage (D22): mission k's research entry (le2mod 0.0.7) is a multi-level tech whose level lives in plot
# int SALVAGE_BOUGHT_INT_BASE + k (each purchase adds 1) and whose cap is SALVAGE_CAP_INT_BASE + k (the entry shows
# and can be bought while level < cap). Per price tier t, every entry carries DisableId SALVAGE_TIER_DISABLE_BASE + t.
SALVAGE_BOUGHT_INT_BASE = 2110
SALVAGE_CAP_INT_BASE = 2150
SALVAGE_TIER_DISABLE_BASE = 21310
SALVAGE_AREA_IDS = {area: [LOCATION_NAME_TO_ID[name] for name in SALVAGE_PICKUPS[area]] for area, _, _ in SALVAGE_MISSIONS}


def sync_salvage(bridge: "BridgeConnection", enabled: bool, tier: int, open_locations: set[int],
                 log: logging.Logger = logger) -> list[int]:
    """Keep the salvage entries in step with the seed; returns the pickup locations bought since the last poll.

    open_locations: this slot's locations not yet checked. A mission offers salvage once its completion location is
    true, capped at its open pickups. A purchase is taken (read and zeroed at once, so none is lost or counted
    twice) and pays for that many open pickups, lowest id first."""
    disable = [SALVAGE_TIER_DISABLE_BASE + t for t in range(len(SALVAGE_PRICES))]
    current = bridge.get_bools(disable)
    for t, index in enumerate(disable):
        want = not enabled or t != tier
        if current[index] != want:
            bridge.set_bool(index, want)
    if not enabled:
        return []
    count = len(SALVAGE_MISSIONS)
    ints = bridge.get_ints([SALVAGE_BOUGHT_INT_BASE + k for k in range(count)] + [SALVAGE_CAP_INT_BASE + k for k in range(count)])
    done = evaluate_locations(bridge, {LOCATION_NAME_TO_ID[loc] for _, _, loc in SALVAGE_MISSIONS})
    bought_now: list[int] = []
    for k, (area, label, completion) in enumerate(SALVAGE_MISSIONS):
        open_pickups = sorted(i for i in SALVAGE_AREA_IDS[area] if i in open_locations)
        if ints[SALVAGE_BOUGHT_INT_BASE + k] > 0:
            paid = bridge.take_int(SALVAGE_BOUGHT_INT_BASE + k)
            bought_now += open_pickups[:paid]
            open_pickups = open_pickups[paid:]
            log.info("%s salvage: %s check(s) bought", label, paid)
        cap = len(open_pickups) if LOCATION_NAME_TO_ID[completion] in done else 0
        if ints[SALVAGE_CAP_INT_BASE + k] != cap:
            bridge.set_int(SALVAGE_CAP_INT_BASE + k, cap)
    return bought_now


def sync_ship_upgrades(bridge: "BridgeConnection", received: Sequence[ReceivedItem], log: logging.Logger = logger) -> list[int]:
    """Keep each upgrade's applied bool equal to whether its item arrived; returns the bools changed."""
    have = {ITEM_NAME_TO_ID[name] for name in SHIP_UPGRADE_BOOLS} & {item.item for item in received}
    current = bridge.get_bools(sorted(SHIP_UPGRADE_BOOLS.values()))
    changed = []
    for name, applied in SHIP_UPGRADE_BOOLS.items():
        want = ITEM_NAME_TO_ID[name] in have
        if current[applied] != want:
            bridge.set_bool(applied, want)
            changed.append(applied)
            log.info("%s %s", name, "installed" if want else "removed (no item yet; research grants nothing)")
    return changed


LOYALTY_MEMBERS = tuple(LOYALTY_LOCATION)  # the order copies are handed out; mod bool LOYALTY_BOOL_BASE + index
PROGRESSIVE_LOYALTY_ID = ITEM_NAME_TO_ID[PROGRESSIVE_LOYALTY]


def sync_loyalty_tokens(bridge: "BridgeConnection", received: Sequence[ReceivedItem], members: Sequence[str],
                        log: logging.Logger = logger) -> list[str]:
    """Open one loyalty mission per Progressive Loyalty copy not yet spent (D26); returns the squadmates opened now.

    members: this seed's squadmates (DLC ones only if enabled). A copy goes to the first, in LOYALTY_MEMBERS order, who
    is recruited (starting squad always), not yet loyal and not already opened; spare copies wait for the next one."""
    copies = sum(1 for item in received if item.item == PROGRESSIVE_LOYALTY_ID)
    if not copies:
        return []
    flags = {m: LOYALTY_BOOL_BASE + LOYALTY_MEMBERS.index(m) for m in members}
    opened = {m for m, value in zip(flags, bridge.get_bools(list(flags.values())).values()) if value}
    spare = copies - len(opened)
    if spare <= 0:
        return []
    ids = {LOCATION_NAME_TO_ID[name] for m in members for name in
           ((RECRUIT_LOCATION[m],) if m in RECRUIT_LOCATION else ()) + (LOYALTY_LOCATION[m],)}
    true = evaluate_locations(bridge, ids)
    now = []
    for member in sorted(set(members) - opened, key=LOYALTY_MEMBERS.index):
        recruited = member not in RECRUIT_LOCATION or LOCATION_NAME_TO_ID[RECRUIT_LOCATION[member]] in true
        loyal = LOCATION_NAME_TO_ID[LOYALTY_LOCATION[member]] in true
        if recruited and not loyal and len(now) < spare:
            bridge.set_bool(flags[member], True)
            now.append(member)
            log.info("Loyalty mission opened: %s", member)
    return now


def sync_open_gates(bridge: "BridgeConnection", progressive_loyalty: bool, dlc_access: bool, members: Sequence[str],
                    dlc: Sequence[str]) -> list[int]:
    """The mod gates loyalty and DLC missions on AP bools; when the seed has no such items (option off, or a seed from
    before them) the client opens those gates itself. Returns the bools set now."""
    want = []
    if not progressive_loyalty:
        want += [LOYALTY_BOOL_BASE + LOYALTY_MEMBERS.index(m) for m in members]
    if not dlc_access:
        want += [DLC_ACCESS_BOOLS[key] for key in DLC_ACCESS_BOOLS if key in dlc]
        if "Firewalker" in dlc:
            want += [FIREWALKER_BOOL_BASE + n for n in range(1, len(FIREWALKER_MISSIONS) + 1)]
    if not want:
        return []
    current = bridge.get_bools(want)
    missing = [index for index in want if not current[index]]
    for index in missing:
        bridge.set_bool(index, True)
    return missing


def intel_count(received: Sequence[ReceivedItem]) -> int:
    return sum(1 for item in received if item.item == IFF_INTEL_ID)


# --------------------------------------------------------------------------------------------------------- client


class ME2CommandProcessor(ClientCommandProcessor):
    ctx: ME2Context

    def _cmd_bridge(self) -> bool:
        """Show the bridge connection state."""
        self.output(f"LE2APBridge: {self.ctx.bridge_state}")
        return True


class ME2Context(CommonContext):
    game = MassEffectLE2World.game
    command_processor = ME2CommandProcessor
    items_handling = 0b111

    def __init__(self, server_address: str | None, password: str | None, bridge: BridgeConnection | None = None) -> None:
        self.bridge = bridge or BridgeConnection()
        self.bridge_state = "not connected"
        self.intel_required: int | None = None
        self.identity: tuple[int, int] | None = None
        self.notices: collections.deque[str] = collections.deque()
        self.notices_enabled = True
        self._handshake_done = False
        self._mismatch_reported = False
        super().__init__(server_address, password)

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "Connected":
            slot_data = args.get("slot_data", {})
            self.intel_required = slot_data.get("intel_required")
            self.me1_history = slot_data.get("me1_history")
            # seeds generated before the salvage options have no salvage entries
            self.salvage = bool(slot_data.get("salvage", 0)) and slot_data.get("pickups", 0) != 0
            self.salvage_tier = int(slot_data.get("salvage_price", 2))
            dlc = set(slot_data.get("enabled_dlc", ()))
            self.enabled_dlc = tuple(dlc)
            self.progressive_loyalty = bool(slot_data.get("progressive_loyalty", 0))
            self.dlc_access = bool(slot_data.get("dlc_access", 0))
            self.loyalty_members = tuple(m for m in LOYALTY_LOCATION
                                         if m not in ("Zaeed Massani", "Kasumi Goto") or m.split()[0] in dlc)
            self.identity = seed_identity(self.seed_name or "", self.team or 0, self.slot or 0)
            self._mismatch_reported = False

    def on_print_json(self, args: dict) -> None:
        super().on_print_json(args)
        if args.get("type") == "ItemSend" and self.slot_concerns_self(args["receiving"]):
            item = args["item"]
            name = self.item_names.lookup_in_slot(item.item, args["receiving"])
            if self.slot_concerns_self(item.player):
                self.notify(f"Found {name}")
            else:
                self.notify(f"Received {name} from {self.player_names[item.player]}")

    def notify(self, text: str) -> None:
        self.notices.extend(notice_lines(text))

    def _server_ready(self) -> bool:
        return self.slot is not None and self.server is not None and not self.server.socket.closed

    def _check_identity(self) -> None:
        """Bind a fresh save to this seed, or refuse a save that belongs to another one."""
        assert self.identity is not None
        saved = self.bridge.identity()
        if saved == self.identity:
            return
        if saved == (0, 0) and self.bridge.get_int(RECEIVED_INDEX_PLOT_INT) == 0:
            if self.bridge.get_bool(GOAL_PLOT_BOOL):
                # a post-game save would send the goal at once (seen live on 2026-10-15)
                if not self._mismatch_reported:
                    self._mismatch_reported = True
                    logger.error("This save is past the ending, so it cannot start an Archipelago seed. "
                                 "Load an earlier save, or start a new career.")
                raise IdentityMismatchError("save is past the ending")
            # Only a career started with the mod (marker set in the character creator), and only one with almost no
            # progress: a vanilla save loaded by mistake was bound and sent 260 checks (2026-10-26).
            if not self.bridge.get_bool(CAREER_MARKER_PLOT_BOOL):
                self._refuse_bind("This save is not an Archipelago career. Start a New Career with the Archipelago mod "
                                  "installed, or load the save for this slot.", "not an Archipelago career")
            already = len(evaluate_locations(self.bridge))
            if already > BIND_MAX_TRUE_LOCATIONS:
                self._refuse_bind(f"This save already has {already} Archipelago locations done, so it is not a fresh "
                                  "career. Start a New Career, or load the save for this slot.", "save has progress")
            self._write_me1_history()
            self.bridge.bind_identity(*self.identity)
            logger.info("Save bound to this seed and slot")
            return
        if not self._mismatch_reported:
            self._mismatch_reported = True
            logger.error("This save belongs to another Archipelago seed or slot (save %s, connected %s). "
                         "Load the save for this slot, or start a new career.", saved, self.identity)
            with contextlib.suppress(BridgeError):
                if self.notices_enabled:
                    self.bridge.note("Archipelago: this save is from another seed")
        raise IdentityMismatchError(f"save identity {saved} != {self.identity}")

    def _refuse_bind(self, message: str, reason: str) -> None:
        if not self._mismatch_reported:
            self._mismatch_reported = True
            logger.error(message)
        raise IdentityMismatchError(reason)

    def _write_me1_history(self) -> None:
        """Before binding a fresh save, write the slot's ME1 choices (the Genesis comic is skipped by the mod)."""
        choices = getattr(self, "me1_history", None)
        if not choices:
            return  # a seed generated before these options: the game keeps whatever the career has
        writes, fell_back = me1_history_writes(choices, self.bridge.get_bool(FEMALE_PLOT_BOOL))
        for index, value in writes.items():
            self.bridge.set_history_bool(index, value)
        if fell_back:
            logger.info("ME1 romance %s is not possible for this Shepard; set to none", choices["me1_romance"])
        logger.info("ME1 history written")

    def _read_game_state(self, server_ready: bool) -> tuple[set[int], bool]:
        if not self._handshake_done:
            version = self.bridge.hello()
            if version != PROTOCOL_VERSION:
                raise BridgeProtocolError(f"bridge speaks protocol {version}, this client {PROTOCOL_VERSION}")
            self._handshake_done = True
        if not server_ready:
            return set(), False  # without a slot, nothing in the save can be trusted to be ours
        self._check_identity()
        received = tuple(self.items_received)
        sync_received_items(self.bridge, received)
        sync_dossier_journals(self.bridge, received)
        sync_ship_upgrades(self.bridge, received)
        sync_loyalty_tokens(self.bridge, received, getattr(self, "loyalty_members", ()))
        sync_open_gates(self.bridge, getattr(self, "progressive_loyalty", False), getattr(self, "dlc_access", False),
                        getattr(self, "loyalty_members", ()), getattr(self, "enabled_dlc", ()))
        open_locations = set(self.missing_locations) - set(self.locations_checked)
        salvaged = sync_salvage(self.bridge, getattr(self, "salvage", False), getattr(self, "salvage_tier", 2),
                                open_locations)
        if self.intel_required is not None and intel_count(received) >= self.intel_required:
            if not self.bridge.get_bool(IFF_OPEN_PLOT_BOOL):
                self.bridge.set_bool(IFF_OPEN_PLOT_BOOL, True)
                logger.info("Reaper IFF Intel complete: the Derelict Reaper is open")
                self.notify("The Derelict Reaper is open")
        missing = set(self.missing_locations) - set(self.locations_checked)
        true_locations = evaluate_locations(self.bridge, missing) | set(salvaged)
        goal = self.bridge.get_bool(GOAL_PLOT_BOOL)
        self._deliver_notices()
        return true_locations, goal

    def _deliver_notices(self) -> None:
        """HUD notices are an aid: a bridge that cannot show them turns them off instead of stopping the client."""
        if not self.notices_enabled:
            self.notices.clear()
            return
        try:
            for _ in range(min(NOTICES_PER_POLL, len(self.notices))):
                self.bridge.note(self.notices[0])
                self.notices.popleft()
        except BridgeProtocolError as error:
            logger.warning("In-game notices are off: %s", error)
            self.notices_enabled = False
            self.notices.clear()

    async def poll_game(self) -> None:
        server_ready = self._server_ready()
        true_locations, goal = await asyncio.to_thread(self._read_game_state, server_ready)
        if not server_ready:
            return
        new_locations = true_locations - self.checked_locations - self.locations_checked
        if self.server_locations:
            new_locations &= self.server_locations
        if new_locations:
            self.locations_checked.update(new_locations)
            await self.send_msgs([{"cmd": "LocationChecks", "locations": sorted(new_locations)}])
            logger.info("Sent %s new location check(s)", len(new_locations))
        if goal and not self.finished_game:
            self.finished_game = True
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            logger.info("Goal complete")

    def _set_state(self, state: str, level: int = logging.INFO) -> None:
        if state != self.bridge_state:
            logger.log(level, "LE2APBridge: %s", state)
            self.bridge_state = state

    async def bridge_loop(self) -> None:
        try:
            while not self.exit_event.is_set():
                try:
                    await self.poll_game()
                    self._set_state("connected, game loaded")
                except GameNotReadyError:
                    self._set_state("connected, waiting for a loaded save")
                except IdentityMismatchError:
                    self._set_state("connected, save belongs to another seed (nothing sent or received)", logging.WARNING)
                except BridgeError as error:
                    self._handshake_done = False
                    self._set_state(f"unavailable ({error})", logging.WARNING)
                except OSError as error:
                    self.bridge.close()
                    self._handshake_done = False
                    self._set_state(f"pipe unavailable ({error})", logging.WARNING)
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        finally:
            self.bridge.close()


async def _main(args: argparse.Namespace) -> None:
    ctx = ME2Context(args.connect, args.password)
    ctx.auth = args.name
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    bridge_task = asyncio.create_task(ctx.bridge_loop(), name="ME2 bridge loop")
    if gui_enabled and not getattr(args, "nogui", False):
        ctx.run_gui()
    ctx.run_cli()
    try:
        await ctx.exit_event.wait()
    finally:
        bridge_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await bridge_task
        await ctx.shutdown()


def launch(*launch_args: str) -> None:
    parser = get_base_parser(description="Mass Effect Legendary Edition 2 Archipelago Client")
    parser.add_argument("--name", default=None, help="Slot name to connect as.")
    parser.add_argument("url", nargs="?", help="archipelago:// connection URL")
    args = handle_url_arg(parser.parse_args(launch_args or None), parser)
    Utils.init_logging("ME2Client", exception_logger="Client")
    colorama.just_fix_windows_console()
    try:
        asyncio.run(_main(args))
    finally:
        colorama.deinit()


if __name__ == "__main__":
    launch()
