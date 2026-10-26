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
- 0.0.2's EntryMenu override did not take in game (2026-10-16: movies, SR-1 and Genesis still played); EntryMenu is most likely
  loaded before custom DLC mount (not proven). 0.0.3 also overrides `BioP_ProNor.pcc`, which loads after them. The runtime winner is
  `DLC_UPD_Patch03` (mount 1020; `DLC_DHME1` 375 and `DLC_UPD_Patch02` 1010 also ship one), so sources are now picked by
  mount priority, not a fixed folder. Its `BlackScreen_0` (after the first-run options screen) normally goes to the
  `SaveDataImport` check and then `RE_persistent_to_levelscript`, which starts BioD_ProNor's opening; Genesis (the
  `DHME1` subsequence of `ProNor_Cutscene_Sequence_2`) and the SR-1 destruction are only reachable from there. All three
  outputs are pointed at 5356/5355/5342 and `BioSeqAct_ActivateCharacterCreation` (BioP_Char). The ME1-save callback
  (`Ready No Data` bools) still runs before it. Gender: BioD_ProNor only reads plot bool 66, set by the main menu.
  Validated: nothing else leads into the `SaveDataImport` check.
- DLC: mount priority 4100, module 4100 (`DLC_4100_INT.tlk`, name strref 41000000). The build refuses if any vanilla
  DLC mounts at or above 4100.
- Fails closed: built in a temp folder, reopened and validated (destination and transition chain), then moved into place.

`research/genesis_choices.tsv`: the Genesis comic (`dlc_dhme1proto_dlg`, FemShep `dlc_dhme1proto_f_dlg`, same nodes and
transitions, in METR_Patch01's `BioD_ProNor_LOC_INT`) asks six questions, all major (the ME1 choices of the ME3 world),
and sets nothing else: no Kismet transitions in the `DHME1` sequence or the `BioD_DHME1_Chp*` packages. So there are no
minor Genesis defaults to fire; the majors stay unset until the bridge op. Effects decoded from every `BioStateEventMap`
in the Startup packages.

`research/prologue_transitions.tsv` is the trace the defaults come from: every transition fired by Kismet or
conversations in the ProNor, ProCer, ProFre and early Normandy packages, with its le2.json label and decoded effects
(from `Startup_INT.pcc` `PlotManagerAuto.StateTransitionMap`).

## Build

```
dotnet build tools/le2mod -c Release -p:LexCoreProject=<path to LegendaryExplorerCore.csproj>
```

Set `LE1PROBE_OODLE` to `oo2core_8_win64.dll` (from the game's `Binaries/Win64`) before running.

## Status

2026-10-16: 0.0.1 (creator to galaxy map) staged, reviewed (Codex, static) and installed. 0.0.2 adds the EntryMenu prologue skip
(failed in game). 2026-10-17: 0.0.3 adds the BioP_ProNor skip; it passed in game on 2026-10-20.

2026-10-24: 0.0.4 adds galaxy-map gating (skip it with `--no-gating`). `Startup_ArchipelagoME2_INT.pcc` is cloned from
DLC_CON_Pack01's startup package, with the packages renamed and `PlotManagerDLC_ArchipelagoME2.BioAutoConditionals`
recompiled to F21002 (Jack), F21003 (Grunt), F21006 (Tali) and F21100 (Reaper). Each is the vanilla body AND the AP
bool. The class is registered in BIOEngine.ini (StartupPackages) and BIOGame.ini (`BioWorldInfo.ConditionalClasses`).
`BioD_Nor_103aGalaxyMap.pcc` (winner DLC_METR_Patch01) gets those four planets' land/visible conditionals repointed.
0.0.4 also gates the six hub recruits per dossier (research/galaxy_gating.md section 6). Mordin, Garrus and Thane each
get a PMCheckState on 21000/21001/21004 in front of plot transition 399, which runs before the black screen and loading
movie of their mission departure. Samara's cab menu conditional C376 becomes F21005, and her RE_HailCab black screen
gets S21005. Zaeed's recruit conversation gets S21007 (0.0.5, 2026-10-25; 0.0.4 repointed his C1495 checks instead, but those only run after the conversation, so he could still be recruited). Kasumi's recruit conversation gets S21008. All of it is
staged and validated (reopened, links and conditionals checked) but not installed: it closes these missions on any
career whose dossier bools are unset.

0.0.6 (2026-10-25, staged only): galaxy-map recruit labels follow the locks. Planet labels (PlanetPlotLabelCondition) for Jack, Grunt, Tali and the Reaper use the gate conditionals. The hub FEATURE_LABELs 'Recruit The Professor/Archangel/Assassin/Justicar/Veteran/Master Thief' get F21200+i (vanilla body AND the dossier bool). 'Help X' loyalty labels and DLC labels (e.g. Overlord) are unchanged.

0.0.7 (2026-10-26, staged only): missed-checks salvage at the Normandy research terminal (D22, research/salvage_store.md). Needs tools/le2mod/salvage.json (tools/export_salvage.py), bridge protocol 4 and the matching client.
