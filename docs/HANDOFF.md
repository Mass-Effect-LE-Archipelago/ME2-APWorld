# Handoff (read this first in a fresh session)

Updated 2026-10-20. Branch `claude/me2-ap-world` (draft PR #1). Owner: Austin (Unowa001). Keep sessions lean: read only
what the next step needs; details live in SCOPE.md, DECISIONS.md and CHECKS-CATALOG.md.

## Status
- AP world (AP 0.6.8): 387 checks by default (418 max). Options include pickups (off/safe/any) and Start on Normandy
  (default on: no Lazarus/Freedom's Progress checks, one random first-wave dossier precollected). 96 tests pass.
- Bridge (`tools/le2apbridge`, protocol v1): built and installed in LE2 on Austin's PC (ME3Tweaks bink proxy plus
  `ASI\LE2APBridge.asi`). First live run passed: reads, write guard, AP flag/int writes, indexed TXN with retry skipped,
  save persistence, +100 credits with the game's popup. HUD NOTE is still "unsupported".
- Start-state mod (`tools/le2mod`, builds `DLC_MOD_ArchipelagoME2`, mount 4100): overrides `BioP_Char` so the creator's
  Finished runs transitions 48, 46, 2398, 2210, 2225, 2401, 4813, 2403 and loads `BioP_Nor` at `start_galaxyMap`.
  0.0.2 (branch `claude/me2-skip-opening-pij7mi`) also skips the SR-1 prologue: an `EntryMenu.pcc` override points the
  main menu's `re_StartNewGame` at the vanilla `re_StartCharCreation` route (starter codex transitions 5356/5355/5342,
  then `BioP_Char`). Gender is picked in the main menu first; `BioP_Char` reads no plot state. `--keep-prologue` builds
  the old behavior. 0.0.2 FAILED in game (movies, SR-1, Genesis still played): EntryMenu most likely loads before
  custom DLC mount. 0.0.3 (2026-10-17) also overrides `BioP_ProNor` (runtime winner `DLC_UPD_Patch03`; sources are now
  picked by mount priority): its BlackScreen_0 goes straight to 5356/5355/5342 and ActivateCharacterCreation, so the
  opening, SR-1 and Genesis (`DHME1` in BioD_ProNor) are unreachable. Staged, validated and installed via Mod Manager
  (2026-10-17, AutoTOC run); in-game run pending. See tools/le2mod/README.md.
- Genesis traced (`tools/le2mod/research/genesis_choices.tsv`): six questions, all major (virmire_survivor, romance,
  rachni, wrex, council, human_councilor, as in the ME3 world), nothing else set, so no minor defaults exist.
- ME1 history (D20, approved): six YAML options; client writes them via bridge `HIST` (protocol 2, bridge ASI v2) before
  binding a fresh save. Impossible romance falls back to none. 100 tests pass.
- Quick-start research (not built): the creator handler `BioSFHandler_NewCharacter` has `StartGameWithIconicCharacter`
  (fills `PlayerInfoEx` from defaults: class, origin, notoriety, name), and `StartNewGame` calls native
  `SFXEngine.CreateCareer(FirstName, srClass, Origin, Notoriety)`. No Kismet action sets class or appearance; a
  creator-free start would mean the ASI bridge filling `SFXEngine.NewPlayer`/`DefaultPlayer` and calling those.

## Next
1. Done 2026-10-20 (Austin: "This worked"): New Career with 0.0.3 + bridge v2 skips the opening and Genesis and lands
   on the galaxy map; ME1 history writes on first connect.
2. Next: the real client against a local AP server on a fresh career (item delivery, checks), then merge this branch
   into claude/me2-ap-world (PR #1).

## Release 0.2.0 (2026-10-26, latest)
- Release folder: APWorldMaker\release\ME2LE-AP-0.2.0 (apworld, LE2APBridge.asi v4/protocol 4, mod 0.0.9 folder + zip,
  install.ps1 / uninstall.ps1, README, documented YAML). Installed on Austin's PC with install.ps1 (2026-10-26 00:12;
  backups in release\ME2LE-AP-0.2.0\backup plus APWorldMaker\backups). World 0.2.0: codex (D23), weapon pickups (D24),
  DLC access items (D25), Progressive Loyalty (D26), salvage (D22), ship upgrades as items (D21), career marker.
- Hosting: archipelago.gg (upload the AP_*.zip at archipelago.gg/uploads); the multidata embeds the data package, so
  no server-side world is needed (checked 2026-10-26 with a stock 0.6.8 Generate, ME2 + Hollow Knight stand-in).
- Pending: Austin's brother's YAML, then generate in C:\ProgramData\Archipelago\Players_ME2Test2 (AustinME2b.yaml is
  there; remove Brother_HK_standin.yaml first) and upload. First in-game run of 0.0.9/v4 on a New Career.
- Desktop .bat now starts only the ME2 client (no local server).

## Current state (2026-10-26, PC session; GitHub is down, so this local clone is the source of truth)
- Commit locally on claude/project-thread-5kre14 only, never push; after each commit run
  `git bundle create <APWorldMaker>\backups\ME2-LE-Archipelago-<date>.bundle --all`.
- **Test seed:** AustinME2 (C:\ProgramData\Archipelago\output\ME2Test\AP_52207553016037918111.zip), server
  localhost:38281, client from the installed AP 0.6.8 in C:\ProgramData\Archipelago (0.0.5-era .apworld in custom_worlds,
  protocol 3). Start both with `C:\Users\unowi\OneDrive\Desktop\Start ME2 AP Test.bat` (Austin can double-click it).
  From a Claude session, start that .bat detached through WMI (Win32_Process.Create); processes started as children of
  the session die when it parks.
- **Memory pressure:** the PC runs near its commit limit (about 1.5 GB of commit free; Firefox about 4.6 GB). The server once
  died with a MemoryError while loading the ~60 custom worlds; a retry worked. Suspect this first if processes vanish.
- **Installed in LE2:** bridge v3 (plot ops wait for a loaded save; SETB allows the 7 dossier journal bools;
  COND/CONDCLS diagnostics) and mod 0.0.5 (galaxy locks for Jack/Grunt/Tali/Reaper; hub recruit locks: Mordin/Garrus/
  Thane at transition 399, Samara cab C376->F21005 + RE_HailCab, Zaeed and Kasumi recruit conversations). Backups in
  APWorldMaker\backups: ASIs v2, v2b, v3; mod folders 0.0.3, 0.0.4. Install method: ME3TweaksModManager.exe
  --installmod <staging>\ArchipelagoME2\moddesc.ini --game LE2 (AutoTOC runs), only with LE2 closed.
- **Confirmed in game (AustinME2):** checks send and items arrive; saves keep plot ints 2100-2102; galaxy locks hide
  Korlus/Purgatory/Haestrom/Reaper (so our conditional class resolves); the Kasumi lock holds; the client sets the
  vanilla dossier journal bools (548/551) and EDI's dossier lines play; Mordin's and Garrus's missions open with their
  dossiers. AustinME2 holds dossiers Mordin and Garrus; Grunt and Zaeed are recruited (Zaeed before the 0.0.5 fix).
- **Built, not installed:**
  - mod 0.0.6 (a163c15, staging-0.0.6): galaxy-map recruit labels hidden until their dossier arrives.
  - Salvage D22 (c29567d): mod 0.0.7 (staging-0.0.7, on top of 0.0.6) + bridge v4 (protocol 4: GETIS/TAKEI/SETI; built at
    APWorldMaker\tools\le2apbridge\build\repo\Build\Release) + client/world with salvage/salvage_price options
    (build\mass_effect_le2.apworld). These three go in together, and salvage needs a new seed. Untested points:
    tools/le2mod/research/salvage_store.md. Needs Mordin (research terminal).
- **Pending:**
  - D21 resolved (galaxy_gating.md section 7) and built into the protocol-4 bridge/client (not installed): the SHIP item
    writes applied bool 236/237/238 and the client enforces it to the items each poll; research grants nothing.
  - The Zaeed lock fix (0.0.5) is untested in game, since he was already recruited on AustinME2.
  - DLC missions (Overlord, etc.) are not gated; they have no AP items.
  - Roadmap steps 3-5 below.
- **Tests and builds on the PC:** world tests: `ME2 LE Randomizer\Archipelago-main` (0.6.9 source,
  worlds\mass_effect_le2 junctioned to this repo's world) with
  `vendor\Archipelago\.venv\Scripts\python.exe -m pytest -q worlds/mass_effect_le2/test` (110 pass). Mod: le2mod openstart
  <BioGame> <staging> with LE1PROBE_OODLE set and -p:LexCoreProject=APWorldMaker\vendor\LegendaryExplorer\...\
  LegendaryExplorerCore.csproj. Bridge: cmake --build APWorldMaker\tools\le2apbridge\build\repo\Build --config Release
  --target LE2APBridge-LE2. salvage.json: python tools/export_salvage.py <Archipelago checkout>.

## Roadmap to playable (proposed 2026-10-20, awaiting Austin's pick)
1. End-to-end run: real client + local AP 0.6.8 server, fresh career; confirm item delivery, check sends, reconnect.
2. Game-side gating (SCOPE Stage 2): the le2mod gates recruitment galaxy-map objects on dossier bools (21000+i) and
   the Derelict Reaper on 21100, ANDed with vanilla conditionals; decide ship-upgrade research vs upgrade items.
   Without this the logic's gates are honor-system only.
3. Logic research that changes gating: R1 (Horizon / Collector Ship / IFF triggers), R5 (DLC unlock points),
   R4 (Zaeed/Kasumi recruit bools), R2 (crew abduction penalty).
4. More checks (R8): codex entries (up to 207, minus start-unlocked and Paragon/Renegade pairs), 9 weapon pickups,
   cabin items, Mission_Landing_Open bools; pickups "any" already exists. Today: 387 default / 418 max.
5. Polish: HUD notices (R6), goal bool 1456 seen at a real ending, plot-range collision audit (R7), release build.
Recommended order: 1, 2, 3, 4, 5.

## Open questions
- Miranda and Jacob start in the squad (default; Austin hasn't objected).
- Goal bool 1456 must be observed at a real ending.

## Working setup
- Cloud: AP 0.6.8 checkout at /home/claude/ap with the world symlinked; tests:
  `cd /home/claude/ap && ../apvenv/bin/python -m pytest -q worlds/mass_effect_le2/test < /dev/null`.
- Austin's PC session hears only Austin's own messages in the ME2 thread; give him a line to paste when it needs a brief.
- Never seed from Austin's bridge test save (AP flag 21000 and counter 1 already set).
