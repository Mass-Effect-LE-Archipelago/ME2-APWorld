# le2mod

Builds the game-side LE2 mod (`DLC_MOD_ArchipelagoME2`) from the player's own game files with LegendaryExplorerCore.
It never writes under the game folder; it stages a ME3Tweaks Mod Manager mod (moddesc.ini + the DLC folder).

## openstart (test build)

```
le2mod openstart <LE2 BioGame dir> <staging dir> [transition,transition..] [--keep-prologue]
```

A new career skips the SR-1 prologue and goes from the character creator straight to the Normandy SR-2 at the galaxy
map (`BioP_Nor` / `start_galaxyMap`). `--keep-prologue` leaves the prologue in.

- Source package: the runtime winner of `BioP_Char.pcc`, `DLC_METR_Patch01` (mount priority 2000) over the base game.
- Edit: the creator's "Finished" output runs the plot transitions, then the vanilla black screen and loading movie,
  then the area transition, retargeted from `Biop_Procer` to `BioP_Nor` with `StartPoint=start_galaxyMap`.
- Default transitions: 48 Jacob in party, 46 Miranda in party, 2398 Lazarus journal done, 2210 talked to the Illusive
  Man, 2225 post-Illusive Man journal, 2401 Freedom's Progress journal done, 4813 StayingOnPlanet false, 2403 main quest
  journal. Not set: dossiers (AP items), 5672 Go_To_Citadel (AP logic), the mission XP bools 5794/5795 (AP checks).
- Prologue skip: overrides `EntryMenu.pcc` (runtime winner `DLC_METR_Patch01`). The main menu's `re_StartNewGame` event
  normally plays a loading movie and loads `BioP_ProNor`. It is pointed at the vanilla `re_StartCharCreation` route
  of the same package: loading movie, transitions 5356/5355/5342 (starter codices, the same ones ProNor's
  `Give_Starter_Codices` fires) with `IgnoreGrinderAchievements` (6022) set around them, then `Biop_Char`. Gender
  is picked in the main menu before either route (`RequestStartNewGame` sets `DefaultPlayer.bIsFemale`), and
  `BioP_Char` reads no plot state. Not fired: 5391 `ProNor_Complete` (achievement bool), 4311/4312 `SaveDataImport`
  (stays false; only ProNor/ProCer read it). Validated: exactly one output link changes.
- DLC: mount priority 4100, module 4100 (`DLC_4100_INT.tlk`, name strref 41000000). The build refuses if any vanilla
  DLC mounts at or above 4100.
- Fails closed: built in a temp folder, reopened and validated (destination and transition chain), then moved into place.

`research/prologue_transitions.tsv` is the trace the defaults come from: every transition fired by Kismet or
conversations in the ProNor, ProCer, ProFre and early Normandy packages, with its le2.json label and decoded effects
(from `Startup_INT.pcc` `PlotManagerAuto.StateTransitionMap`).

## Build

```
dotnet build tools/le2mod -c Release -p:LexCoreProject=<path to LegendaryExplorerCore.csproj>
```

Set `LE1PROBE_OODLE` to `oo2core_8_win64.dll` (from the game's `Binaries/Win64`) before running.

## Status

2026-10-16: 0.0.1 (creator to galaxy map) staged, reviewed (Codex, static) and installed. 0.0.2 adds the prologue skip;
staged and validated, in-game run pending.
