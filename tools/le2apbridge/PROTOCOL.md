# LE2APBridge protocol (version 4)

Named pipe `\\.\pipe\LE2APBridge`, message mode. One ASCII request per message, one reply per request.
Replies are `OK`, `OK <value>` or `ERR <reason>`. The pipe thread validates; everything touching game state runs on the
game thread inside the `UObject::ProcessEvent` hook. A request that waits more than 5 s answers `ERR timeout` (it may
still complete later; see TXN for why that is safe).

| Request | Reply | Notes |
|---|---|---|
| `PING` | `OK pong` | |
| `HELLO <client protocol>` | `OK <bridge protocol> LE2` | The client refuses to continue on a different protocol. |
| `VER` | `OK <asi version>` | |
| `GETB <n>` | `OK 0` / `OK 1` | Any plot bool. |
| `GETI <n>` | `OK <value>` | Any plot int. |
| `GETBS <n1> <n2> ...` | `OK <0/1 per index>` | Up to 64 indices, in order. |
| `SETB <n> <0/1>` | `OK` | AP block bools 21000-21999 (derived state the client recomputes, e.g. 21100), and (protocol 3) set-only the dossier journal bools 551, 548, 545, 552, 549, 553, 550 that TIM's transitions 2371/2372 set. |
| `GETIS <n1> <n2> ...` | `OK <v1> <v2> ...` | Protocol 4. Up to 64 plot ints, in order. |
| `TAKEI <n>` | `OK <value>` | Protocol 4. Salvage purchase counters 2110-2149 only: returns the value and sets it to 0 in the same game-thread step. |
| `SETI <n> <v>` | `OK` | Protocol 4. Salvage caps 2150-2199 only, 0-1000. |
| `COND <id>` | `OK 0/1` | Protocol 3, diagnostic: `BioWorldInfo.CheckConditional(id, 0)`. |
| `CONDCLS` | `OK <class> ...` | Protocol 3, diagnostic: `BioWorldInfo.ConditionalClasses` (the registered conditional classes). |
| `ID` | `OK <seed> <slot>` | Save identity, plot ints 2101/2102. `0 0` = not bound. |
| `IDSET <seed> <slot>` | `OK` / `ERR bound` | Only when the save is unbound and its received index is 0. |
| `HIST <n> <0/1>` | `OK` / `ERR bound` | Protocol 2. ME1-history bools only (the Genesis choices: 1528-1530, 1926, 1540, 1541, 1553-1556, 3151, 3752, 7447, 7448), only on an unbound save with received index 0; the client sends them just before `IDSET`. |
| `TXN <index> <op> [args]` | `OK applied` / `OK done` / `ERR gap <current>` | See below. |
| `NOTE <text>` | `ERR unsupported` (v1) | HUD notice; logged only until LE2's notifier call is verified. |
| `MAP` | `OK <package>` | Persistent map package of the current world. |

Not-ready replies: `ERR noworld` (no world loaded), `ERR notready` (a world but no player pawn, e.g. the main menu
or a loading screen: every plot read and write, `ID`, `IDSET`, `HIST` and `TXN` wait for a loaded save),
`ERR noplayer` (no player pawn, for `RES`).

## TXN

`TXN <index> <op> [args]` delivers received item `<index>` (0-based position in the server's received list). On the game
thread, in one step: if the save's received index (plot int 2100) is greater than `<index>`, reply `OK done` and do
nothing; if it is smaller, reply `ERR gap <current>`; if equal, apply the operation, then set int 2100 to `<index> + 1`
and reply `OK applied`. A failed operation leaves the index unchanged. Because comparison, grant and index update are one
game-thread step, a lost reply followed by a retry never grants twice, and no save can contain the grant without the
index (or the reverse).

| Op | Args | Effect | Allowed targets |
|---|---|---|---|
| `NONE` | | nothing (counter-only items: Reaper IFF Intel) | |
| `FLAG` | `<bool>` | set an AP bool | 21000-21999 |
| `SHIP` | `<applied> <unlocked>` | set a ship upgrade's applied and research-unlocked bools | 237/5642, 236/5648, 238/5645 |
| `WEAPON` | `<int>` | raise a weapon unlock int to at least 1 | the 17 weapon ints in `data.WEAPONS` |
| `RES` | `<type> <amount>` | `ASFXInventoryManager.AdjustResource` | type 0 credits, 1 medi-gel, 4 eezo, 5 iridium, 6 palladium, 7 platinum, 8 probes (SDK EInventoryResourceTypes); amount 1-1000000 |

Anything else is `ERR notallowed` / `ERR badrequest`: an unsupported item is never silently consumed.

## Plot IDs owned by Archipelago (pending the collision audit, docs/DECISIONS.md D2)

| ID | Meaning |
|---|---|
| int 2100 | received index (written only by TXN) |
| ints 2101, 2102 | seed and slot identity |
| bools 21000-21008 | dossier received (data.DOSSIERS order); read by the mod's galaxy-map conditionals |
| bool 21100 | Reaper IFF Intel requirement met; read by the mod's Derelict Reaper conditional |
