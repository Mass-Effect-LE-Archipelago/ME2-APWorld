# Handoff (read this first in a fresh session)

Updated 2026-10-17. Branch `claude/me2-ap-world` (draft PR #1). Owner: Austin (Unowa001). Keep sessions lean: read only
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
  opening, SR-1 and Genesis (`DHME1` in BioD_ProNor) are unreachable. Staged and validated; install queued in Mod
  Manager (Austin clicks Install), in-game run pending. See tools/le2mod/README.md.
- Genesis traced (`tools/le2mod/research/genesis_choices.tsv`): six questions, all major (virmire_survivor, romance,
  rachni, wrex, council, human_councilor, as in the ME3 world), nothing else set, so no minor defaults exist. With 0.0.3
  the ME1 majors are unset until the bridge op.
- Quick-start research (not built): the creator handler `BioSFHandler_NewCharacter` has `StartGameWithIconicCharacter`
  (fills `PlayerInfoEx` from defaults: class, origin, notoriety, name), and `StartNewGame` calls native
  `SFXEngine.CreateCareer(FirstName, srClass, Origin, Notoriety)`. No Kismet action sets class or appearance; a
  creator-free start would mean the ASI bridge filling `SFXEngine.NewPlayer`/`DefaultPlayer` and calling those.

## Next
1. Austin: install 0.0.3 (Mod Manager panel) and test New Career: gender pick -> creator -> galaxy map.
2. Austin reviews the major list (genesis_choices.tsv). Then: guarded bridge op (allowlist of those transitions, fresh
   career only), YAML options with ME3 names/defaults, client step. Not started.
3. Then the real client against a local AP server.

## Open questions
- Major defaults until Austin decides: ME3 world's (ashley, wrex alive, rachni saved, council saved, anderson, no
  romance)? Romance needs a matching survivor/gender (Ashley: male + Ashley survived; Kaidan: female + Kaidan).
- Miranda and Jacob start in the squad (default; Austin hasn't objected).
- Goal bool 1456 must be observed at a real ending.

## Working setup
- Cloud: AP 0.6.8 checkout at /home/claude/ap with the world symlinked; tests:
  `cd /home/claude/ap && ../apvenv/bin/python -m pytest -q worlds/mass_effect_le2/test < /dev/null`.
- Austin's PC session hears only Austin's own messages in the ME2 thread; give him a line to paste when it needs a brief.
- Never seed from Austin's bridge test save (AP flag 21000 and counter 1 already set).
