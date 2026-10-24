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

## 2026-10-24 (PC session; GitHub is down, so this local clone is the source of truth)
- Commit locally on claude/project-thread-5kre14 only, never push; after each commit run
  `git bundle create <APWorldMaker>\backups\ME2-LE-Archipelago-<date>.bundle --all`.
- E2E run on the AustinME2 seed (C:\ProgramData\Archipelago\output\ME2Test, server localhost:38281): checks send,
  items come back, saves keep plot ints 2100-2102. Main-menu early bind fixed in the bridge (aa0dad5; ASI built at
  APWorldMaker\tools\le2apbridge\build\repo\Build\Release, NOT installed yet; install only with LE2 closed).
- D21 (ship upgrades are items only): research trace in tools/le2mod/research/galaxy_gating.md section 4. Blocked on
  a before/after bridge read on a throwaway non-AP save (never AustinME2). Client bug: SHIP items set the research
  UnlockId bool.
- le2mod 0.0.4 (747f0a4) stages galaxy gating for Jack/Grunt/Tali/Reaper (APWorldMaker\tools\le2mod\staging-0.0.4).
  Not installed: it closes those planets on careers without the dossier bools.
- Hub recruits (Mordin, Garrus, Zaeed, Thane, Samara, Kasumi): gates traced (galaxy_gating.md section 6). Austin is
  choosing between per-mission gates and hub-access items.
- World tests on the PC: `ME2 LE Randomizer\Archipelago-main` (0.6.9 source, worlds\mass_effect_le2 is a junction to
  this repo's world) with `vendor\Archipelago\.venv\Scripts\python.exe -m pytest -q worlds/mass_effect_le2/test`.

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
