# Mass Effect 2 Legendary Edition for Archipelago

An [Archipelago](https://archipelago.gg) multiworld integration for Mass Effect 2 Legendary Edition (PC), following the
architecture of the completed LE1 integration.

| Part | Path | State |
|---|---|---|
| AP world (items, locations, logic, options) | `world/mass_effect_le2` | Generates; 64 tests, 3,000-seed sweeps clean |
| Client (Archipelago <-> game) | `world/mass_effect_le2/client.py` | Written and unit-tested against a fake bridge |
| Game bridge (ASI, named pipe) | `tools/le2apbridge` | Source written; not yet compiled or run |
| Game-side DLC mod (mission gates) | not started | Next stage |

Docs: [scope and plan](docs/SCOPE.md), [decisions](docs/DECISIONS.md), [checks catalog](docs/CHECKS-CATALOG.md),
[bridge protocol](tools/le2apbridge/PROTOCOL.md).

## Development

Tests run inside an Archipelago 0.6.8 checkout with the world linked in:

```sh
git clone --branch 0.6.8 https://github.com/ArchipelagoMW/Archipelago.git
ln -s "$PWD/world/mass_effect_le2" Archipelago/worlds/mass_effect_le2   # or copy on Windows
cd Archipelago && python -m pytest worlds/mass_effect_le2/test
```

Build the `.apworld` with `python tools/build_apworld.py` (writes `build/mass_effect_le2.apworld`).
