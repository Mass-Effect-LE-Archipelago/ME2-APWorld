<div align="center">

# Mass Effect 2 Legendary Edition &middot; Archipelago

**Recruit the team, earn their loyalty and stop the Collectors, with your progress scattered across an
[Archipelago](https://archipelago.gg) multiworld.**

[![Latest release](https://img.shields.io/github/v/release/Mass-Effect-LE-Archipelago/ME2-APWorld?label=release)](https://github.com/Mass-Effect-LE-Archipelago/ME2-APWorld/releases/latest)
[![Launcher](https://img.shields.io/github/v/release/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher?label=launcher)](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher/releases/latest)
![Archipelago](https://img.shields.io/badge/Archipelago-0.6.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20(PC)-lightgrey)

</div>

> [!NOTE]
> This is a **public test build**. It is an unofficial fan project, not affiliated with or endorsed by BioWare or
> Electronic Arts, and it contains no game assets. You need your own PC copy of Mass Effect Legendary Edition.

## Contents

- [Overview](#overview)
- [Setup guide](#setup-guide)
- [Options](#options)
- [Repository layout](#repository-layout)
- [Development](#development)
- [Part of the trilogy](#part-of-the-trilogy)
- [AI Disclosure](#ai-disclosure)

## Overview

### What gets randomized

Recruitment dossiers, the Normandy's three suicide-mission upgrades (Heavy Ship Armor, Multicore Shielding and the
Thanix Cannon), Reaper IFF Intel, DLC mission keys, loyalty mission unlocks, weapon unlocks and resource bundles are
shuffled into the multiworld. A recruitment mission opens on the galaxy map only once its dossier arrives, and the
Derelict Reaper opens once you hold enough Reaper IFF Intel.

### What counts as a check

| Family | Examples | Default |
| --- | --- | --- |
| Story and recruitment | Each recruitment, Horizon, the Collector Ship, the Reaper IFF | Always on |
| Loyalty missions | Every squadmate's loyalty mission | Always on |
| Assignments | N7 assignments from planet scans; optionally hub and Normandy assignments | N7 only |
| Pickups | Credit caches, resource nodes and upgrade blueprints in missions and hubs | On (safe) |
| Research | Tech lab projects on the Normandy | On |
| Collectibles | Captain's cabin purchases (models, fish, the space hamster) and armor pieces | On |
| Codex | Codex entries unlocked after the start | On |
| DLC | Kasumi, Zaeed, Overlord, Lair of the Shadow Broker, Arrival, Firewalker, Normandy Crash Site | All enabled |

Collector Base checks sit past the point of no return and only ever hold filler.

### Goal

Collect the required Reaper IFF Intel, take the Normandy through the Omega 4 Relay, and finish the suicide mission with
Shepard alive. By default, logic expects every loyalty mission and all three ship upgrades before the relay, so a
successful run is always possible. Choosing the right specialists is still up to you.

### How it plays

- **No prologue, no Genesis comic.** A new career skips Lazarus Station and Freedom's Progress and starts aboard the
  SR-2 at the galaxy map, with Miranda and Jacob in the squad. Your ME1 choices are seed options, written into the
  career by the client the first time it connects. No ME1 save is needed.
- **Your normal saves are safe.** The client only connects to careers started with the mod, and it binds each career
  to one seed.
- **Missed something?** Once you finish a mission that can't be replayed, the Normandy's research terminal sells
  "&lt;mission&gt; Salvage". Each purchase sends one pickup check you left behind.

## Setup guide

The [**Mass Effect Archipelago Launcher**](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher/releases/latest)
is the recommended way to install, update and play. It downloads this project's newest release, verifies it, installs
it with backups, writes your player options and starts the game with its client.

### Requirements

- Mass Effect Legendary Edition (PC), with Mass Effect 2 installed.
- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
- Nothing else. ME3Tweaks Mod Manager is **not** required for ME2: the launcher adds its own ASI loader when no other
  loader is present.

### 1. Install with the launcher

1. Close Mass Effect 2 and any open Archipelago client.
2. Download `Mass-Effect-Archipelago-Launcher.exe` from the
   [launcher's latest release](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher/releases/latest)
   and run it. It is self-contained, so there is nothing else to install.
3. Pick **Mass Effect 2** in the campaign list on the left.
4. Open **Folders** and check that your Legendary Edition and Archipelago folders were detected. Browse to correct
   them if needed.
5. Open **Deploy** and click **Deploy**. The launcher downloads the newest ME2 release, checks it against its SHA-256,
   and installs:
   - `mass_effect_le2.apworld` into Archipelago's `custom_worlds` folder,
   - the game bridge `LE2APBridge.asi` into `Game\ME2\Binaries\Win64\ASI`,
   - the `DLC_MOD_ArchipelagoME2` game mod, and
   - the AP ASI Loader (`bink2w64.dll`), only if no other loader is installed.

   Anything replaced is backed up. **Uninstall** puts every file back. When a newer release is published, the button
   reads **Update**.

### 2. Create your player options

1. Open **Options** in the launcher.
2. Pick a preset (**Story Focus**, **Completionist** or **Everything**) or set each option yourself. Hover any option
   to read what it does.
3. Enter your slot name and click **Save to Players**. This writes your YAML into Archipelago's `Players` folder.

Prefer editing by hand? The template `Mass Effect Legendary Edition 2.yaml` ships with the world and explains every
option.

### 3. Generate and host the seed

Whoever hosts the multiworld collects everyone's YAMLs and runs Archipelago's **Generate** with this world in
`custom_worlds`. To host online, upload the resulting `AP_*.zip` at [archipelago.gg/uploads](https://archipelago.gg/uploads)
and create a room. Everyone then connects to the address the room shows (for example `archipelago.gg:12345`).

### 4. Play

1. In the launcher, click **Launch** with the client box ticked. This starts Mass Effect 2 and the
   **Mass Effect LE2 Client**. (You can also open the client from Archipelago's own launcher.)
2. In the client, connect to the room with your slot name.
3. In Mass Effect 2, choose **New Career** and create your Shepard. The mod skips the opening and drops you on the
   Normandy at the galaxy map. The client writes your ME1 history on first contact and binds the career to your slot.
4. Play. Checks are sent while the client is running, and anything you do offline is sent the next time the client sees
   the save. Keep one career per seed.

### Troubleshooting

- **The client won't connect to my save.** It only accepts careers started with the mod, and it refuses a career bound
  to a different seed. Start a new career for each seed.
- **I use ME3Tweaks Mod Manager for other mods.** That's fine. Mod Manager may replace the AP ASI Loader with its own
  on its next install; its loader also loads the bridge.
- **Logs.** The loader writes `APAsiLoader.log` next to `MassEffect2.exe`. The launcher keeps downloads in
  `%LOCALAPPDATA%\MassEffectAPSetup\downloads` and install records and backups in
  `%LOCALAPPDATA%\MassEffectAPSetup\ME2`.

<details>
<summary><b>Installing without the launcher</b></summary>

Each [release](https://github.com/Mass-Effect-LE-Archipelago/ME2-APWorld/releases/latest) also has a standalone zip
with `ME2 AP Setup.exe` (an installer and options editor), an `install.ps1` script, and every file listed above. See
the README inside the zip for the manual steps.

</details>

## Options

| Option | What it does | Default |
| --- | --- | --- |
| `intel_total` | Reaper IFF Intel items in the pool (1-10) | 5 |
| `intel_required` | Reaper IFF Intel needed to open the Derelict Reaper (1-10) | 3 |
| `endgame_readiness` | What logic expects before the Omega 4 Relay: `all_loyal` or `ship_upgrades` | `all_loyal` |
| `start_on_normandy` | Skip Lazarus Station and Freedom's Progress and start on the SR-2 | On |
| `assignments` | Which assignments are checks: `off`, `n7` or `all` | `n7` |
| `pickups` | Mission pickups as checks: `off`, `safe` (never progression) or `any` | `safe` |
| `research` | Tech lab research projects are checks | On |
| `collectibles` | Captain's cabin purchases and armor pieces are checks | On |
| `codex` | Codex entries are checks (never progression) | On |
| `dlc_access` | DLC missions need a key item to open | On |
| `progressive_loyalty` | Loyalty missions open through "Progressive Loyalty Mission" items | On |
| `weapon_unlocks` | Weapon unlocks are shuffled into the pool | On |
| `salvage` / `salvage_price` | Buy back missed pickups at the research terminal, and their price per check | On / 1000 |
| `enabled_dlc` | Which DLC adds checks | All |
| `me1_*` | ME1 history: Virmire survivor, romance, Rachni Queen, Wrex, the Council, the human councilor | See YAML |

## Repository layout

| Path | Contents |
| --- | --- |
| [`world/mass_effect_le2`](world/mass_effect_le2) | The Archipelago world (items, locations, logic, options) and the Mass Effect LE2 Client |
| [`tools/le2apbridge`](tools/le2apbridge) | Game bridge (ASI plugin) that the client talks to over a named pipe ([protocol](tools/le2apbridge/PROTOCOL.md)) |
| [`tools/le2mod`](tools/le2mod) | Builder for the `DLC_MOD_ArchipelagoME2` game mod (opening skip, mission gates) |
| [`tools/asiloader`](tools/asiloader) | The AP ASI Loader (`bink2w64.dll` proxy) |
| [`tools/setup`](tools/setup) | The standalone `ME2 AP Setup.exe` |
| [`docs`](docs) | [Scope](docs/SCOPE.md), [decisions](docs/DECISIONS.md), [checks catalog](docs/CHECKS-CATALOG.md) |

## Development

Tests run inside an Archipelago 0.6.8 checkout with the world linked in:

```sh
git clone --branch 0.6.8 https://github.com/ArchipelagoMW/Archipelago.git
ln -s "$PWD/world/mass_effect_le2" Archipelago/worlds/mass_effect_le2   # or copy it on Windows
cd Archipelago && python -m pytest worlds/mass_effect_le2/test
```

Build the `.apworld` with `python tools/build_apworld.py` (writes `build/mass_effect_le2.apworld`).

Bug reports and feedback are welcome in [Issues](https://github.com/Mass-Effect-LE-Archipelago/ME2-APWorld/issues).

## Part of the trilogy

| Game | Project |
| --- | --- |
| Mass Effect 1 | [ME1-APWorld](https://github.com/Mass-Effect-LE-Archipelago/ME1-APWorld) |
| Mass Effect 2 | **ME2-APWorld** (this project) |
| Mass Effect 3 | [ME3-AP-World](https://github.com/Mass-Effect-LE-Archipelago/ME3-AP-World) |
| Launcher | [ME-Archipelago-Launcher](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher) |

## AI Disclosure
AI was used to aid in the research and development of this multiworld.
