# Handoff (read this first in a fresh session)

Updated 2026-10-16. Branch `claude/me2-ap-world` (draft PR #1). Owner: Austin (Unowa001). Keep sessions lean: read only
what the next step needs; details live in SCOPE.md, DECISIONS.md and CHECKS-CATALOG.md.

## Status
- AP world (AP 0.6.8): 387 checks by default (418 max). Options include pickups (off/safe/any) and Start on Normandy
  (default on: no Lazarus/Freedom's Progress checks, one random first-wave dossier precollected). 96 tests pass.
- Bridge (`tools/le2apbridge`, protocol v1): built and installed in LE2 on Austin's PC (ME3Tweaks bink proxy plus
  `ASI\LE2APBridge.asi`). First live run passed: reads, write guard, AP flag/int writes, indexed TXN with retry skipped,
  save persistence, +100 credits with the game's popup. HUD NOTE is still "unsupported".
- Start-state mod (`tools/le2mod`, builds `DLC_MOD_ArchipelagoME2`, mount 4100): overrides `BioP_Char` so the creator's
  Finished runs transitions 48, 46, 2398, 2210, 2225, 2401, 4813, 2403 and loads `BioP_Nor` at `start_galaxyMap`. The SR-1
  intro is kept (Austin's choice). Being installed via Mod Manager now; the builder is being pushed to this repo.

## Next
1. New Career test: where Shepard lands, weapons on arrival, the Normandy first-arrival scene, the galaxy map.
2. Then the real client against a local AP server on a fresh career (seed binding ID/IDSET, item delivery, checks).

## Open questions
- Miranda and Jacob start in the squad (default; Austin hasn't objected).
- Goal bool 1456 must be observed at a real ending.

## Working setup
- Cloud: AP 0.6.8 checkout at /home/claude/ap with the world symlinked; tests:
  `cd /home/claude/ap && ../apvenv/bin/python -m pytest -q worlds/mass_effect_le2/test < /dev/null`.
- Austin's PC session hears only Austin's own messages in the ME2 thread; give him a line to paste when it needs a brief.
- Never seed from Austin's bridge test save (AP flag 21000 and counter 1 already set).
