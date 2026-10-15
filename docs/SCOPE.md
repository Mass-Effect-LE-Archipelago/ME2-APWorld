# Mass Effect 2 (LE2) for Archipelago: scope and plan

Stages follow `LE2-FEASIBILITY-AND-ROUGH-PLAN.md`. This file tracks what exists and what each next step must prove.

## Built (2026-10-14)

- **AP world** `world/mass_effect_le2` (0.1.0, AP 0.6.8): 387 locations by default (27 minimum, 40 with Story Focus,
  418 with every option): story, recruitment, loyalty, N7 and hub assignments, DLC, 44 research projects, 26
  collectibles, 258 pickups. Items: 9 dossiers, 3 ship upgrades, Reaper IFF Intel, 17 weapon unlocks, resource filler.
  Options: intel total/required, endgame readiness, assignments (off / n7 / all), research, collectibles, pickups (off /
  safe / any), enabled DLC, weapon unlocks; two presets.
- **Tests**: 89 tests (logic, client, 280-seed sweep); 1,000-seed sweeps on three option sets: 0 failures.
- **Client** `client.py`: identity binding, TXN delivery, batched predicate reads, IFF gate, goal. Fake-bridge tests cover
  lost replies, older-save replay and identity.
- **Bridge source** `tools/le2apbridge` (protocol v1): not yet compiled.

## Not built yet: the game-side mod (Stage 2)

Without it, dossiers and Reaper IFF Intel have no effect in game; checks, goal and resource/weapon/ship delivery work
through the bridge alone. The mod (a `DLC_MOD_ArchipelagoME2` built with LegendaryExplorerCore, like `tools/le1mod`) must:

1. Gate each recruitment mission's galaxy-map object (`SFXGalaxyMapObject.VisibleConditional/UsableConditional`) on
   AP bool 21000 + dossier index, ANDed with its vanilla conditional. Resolve the winning `BioD_Nor_103aGalaxyMap.pcc`
   among the DLC copies first (plan: "Direct LE2 findings").
2. Gate the Derelict Reaper the same way on bool 21100.
3. Decide what the vanilla ship-upgrade research does once the upgrades are items (hide it, or leave it additive).

## Stage 1 runtime spike (on the owner's PC)

Done 2026-10-15 with the branch bridge (ME3Tweaks bink proxy plus `ASI\LE2APBridge.asi`): HELLO, VER, MAP, reads, the write guard, AP bool/int writes, one indexed RES TXN with retry skipped, and save persistence. Left: steps 2 (ID/IDSET), 4 and 5 below, and the credit amount seen in game.

Needs an installed LE2 (only the backup was found) and ME3Tweaks Mod Manager's ASI loader.

1. Build `LE2APBridge-LE2` in the vendored LExASIs; fix SDK name mismatches.
2. Fresh career to the first SR-2 state: `HELLO`, `ID`/`IDSET`, read checks; save, reload, confirm identity and AP ints
   persist (D2 serialization).
3. One `TXN RES` (credits) and one `TXN SHIP`; kill the client mid-TXN and retry (expect `OK done`); load an older save
   (expect replay of the missing index only); connect with another slot (expect refusal).
4. Observe predicates: Lazarus/Freedom's Progress reward bools, one recruitment, the IFF and goal bools (D5, D11).
5. Verify the eInvResType order (D12) and the weapon int semantics (D8).

## Research list (blocks logic loosening, not the first campaign)

- R1 Horizon, Collector Ship and IFF triggers: trace the scheduler (int 23 and its consumers) to replace D7's conservative
  gates with the real ones.
- R2 Crew abduction: the plan's default is no crew penalty for waiting on remote items; trace and pick the smallest change.
- R3 Hub assignments: confirm the XP-code placements (D18) and the provisional Oracle / Sun / Daniel names; place
  Astrosmash.
- R8 More check families, not added yet: 207 codex entries (le2.json Codex_Text; Paragon/Renegade variants are mutually
  exclusive and many unlock at the start), the 9 weapon pickups (D17), and cabin items 3325/3327/3333/3335/3336 (likely
  pre-order). Mission_Landing_Open bools (27) can replace D7's N7 gates once observed.
- R4 Zaeed and Kasumi recruitment moments: find dedicated bools or transitions to replace the in-party interim (D5).
- R5 DLC availability: Overlord, Firewalker, Normandy Crash Site, Shadow Broker and Arrival unlock points.
- R6 HUD notices: LE2 `BioEventNotifier` call for `NOTE`.
- R7 Collision audit of D2's plot ranges (vanilla DLC packages, LE2 Community Patch and other popular mods).
