# Galaxy-map gating and ship-upgrade research (traced 2026-10-24)

Read-only trace of Austin's LE2 install with LegendaryExplorerCore (scratch probe, not in the repo). Every package
listed is the runtime winner by mount priority, as `Program.cs` Winner() picks it. Plot ids are le2.json indices.

## 1. Where the galaxy map lives

- One package holds the whole galaxy: `BioD_Nor_103aGalaxyMap.pcc`. The runtime winner is `DLC_METR_Patch01`
  (mount 2000). It overrides the copies in EXP_Part02 (400), EXP_Part01 (300), UNC_Pack01, HEN_MT, UNC_Hammer01,
  HEN_VT, UNC_Moment01 and DLC_00_Shared. It holds `BIOG_GalaxyMap_DLC00.GalaxyMap`: 29 `SFXCluster`, 72 `SFXSystem`,
  312 `BioPlanet` and 4074 `SFXPlanetFeature`, DLC destinations included.
- `BioPlanet`, `SFXSystem` and `SFXCluster` each carry `VisibleConditional`/`VisibleParameter` and
  `UsableConditional`/`UsableParameter` (conditional ids). Planets also carry `PlanetLandCondition`, the
  conditional that makes a planet landable, plus `MapName`. The `*ConditionalRegion/Plot/Name` fields are None
  everywhere (editor-only).

### Destinations

| Destination | Object (in `GalaxyMap`) | MapName | Planet V / land | System / cluster V |
|---|---|---|---|---|
| Jack, Purgatory | SFXCluster_19.SFXSystem_14.BioPlanet_25 | BioP_PrsCvA | V177 / land 177 | none / none |
| Grunt, Korlus | SFXCluster_16.SFXSystem_12.BioPlanet_23 | BioP_JnkKgA | none / land 182 | none / none |
| Tali, Haestrom | SFXCluster_9.SFXSystem_7.BioPlanet_18 | BioP_SunTlA | none / land 181 | none / 1304 |
| Derelict Reaper | SFXCluster_10.SFXSystem_8.BioPlanet_1 | BioP_RprGtA | V178 / land 178 | 1305 / 1701 |
| Omega (Mordin, Garrus, Zaeed) | SFXCluster_1.SFXSystem_2.BioPlanet_2 | BioP_OmgHub | none / none | none / none |
| Illium (Thane, Samara) | SFXCluster_5.SFXSystem_6.BioPlanet_17 | BioP_TwrHub | V491 U491 / none | 491 / 491 |
| Citadel (Kasumi) | SFXCluster_0.SFXSystem_0.BioPlanet_0 | BioP_CitHub | V197 U197 / none | - |

Six of the nine recruitments (Mordin, Garrus and Zaeed on Omega, Thane and Samara on Illium, Kasumi on the Citadel)
**are not galaxy-map objects**: they start inside a hub. The galaxy map can only gate Jack, Grunt, Tali and the
Reaper. Gating the hub recruits needs the hub packages' recruitment triggers. That is not traced yet.

The other mission planets on the map are loyalty missions (Zorya `BioP_ZyaVTL` F195, Bekenstein `BioP_BchLmL` F1571,
`BioP_QuaTlL` F192, `BioP_JunCvL` F187, `BioP_BlbGtL` F188, `biop_ptymtl` F189, with F943/F944/F947/F948 on their
systems). The endgame is `BioP_EndGm1` (land 1580).

## 2. What the conditionals test, and where they live

Base conditionals are `BioAutoConditionals.F<id>` functions in `CookedPCConsole\PlotManager.pcc`: 1356 functions,
ids 1..2050. Each DLC adds its own class `PlotManagerDLC_<dlc>.BioAutoConditionals` inside its
`Startup_<dlc>_INT.pcc`. It is registered in the DLC's BIOEngine.ini `[Engine.StartupPackages]`
(`+DLCStartupPackage=Startup_<dlc>`, `+Package=PlotManagerDLC_<dlc>`, `+Package=PlotManagerAutoDLC_<dlc>`). The 343
DLC conditional ids (1198..2039) never repeat a base id, so lookup is by unique id across all registered classes.

| Conditional | Body (decompiled) | Reading |
|---|---|---|
| F177 (Jack land, visible) | `!bool35 && !bool197` | Jack not in squad, mission not done |
| F182 (Grunt land) | `!bool618` | Korlus mission not done |
| F181 (Tali land) | `bool312 && !bool40 && !bool202` | after Horizon gate 312, Tali not in squad, not done |
| F178 (Reaper visible, land) | `bool313 && !bool1256` | IFF mission open, not done |
| F491 (Illium) | `bool312` | |
| F197 (Citadel) | `TRUE` | |

Vanilla has no dossier bool on these planets. Jack's and Grunt's planets open as soon as Freedom's Progress is done
(the open start sets that), and Tali's after bool 312.

Can one DLC_MOD package override them? Yes, on the galaxy-map side. `BioD_Nor_103aGalaxyMap.pcc` is a level package
picked by mount priority, the same route `BioP_Char`, `BioP_ProNor` and `EntryMenu` already use. Overriding
`PlotManager.pcc` itself is not recommended: it is a base startup package, and a DLC copy is not shown to win.

## 3. Smallest override (proposed, not built)

1. **New conditionals in our own DLC.** Add `Startup_ArchipelagoME2_INT.pcc`, holding a class
   `PlotManagerDLC_ArchipelagoME2.BioAutoConditionals`, modeled on any vanilla DLC's (e.g. HEN_VT's 27 functions). Use
   free ids 21000+i, which match the AP bools and are far above the vanilla 1..2050:
   - F21002 Jack = `F177 body && bool21002`; F21003 Grunt = `F182 body && bool21003`;
     F21006 Tali = `F181 body && bool21006` (dossier order Mordin 0, Garrus 1, Jack 2, Grunt 3, Thane 4, Samara 5,
     Tali 6, Zaeed 7, Kasumi 8);
   - F21100 Reaper = `F178 body && bool21100`.
   Register it in the mod's BIOEngine.ini `[Engine.StartupPackages]` the way the vanilla DLCs do.
2. **Galaxy-map override.** Ship `BioD_Nor_103aGalaxyMap.pcc` in `DLC_MOD_ArchipelagoME2` (mount 4100 beats
   METR_Patch01's 2000). It is a copy of the METR_Patch01 winner (10.5 MB) with only these int properties repointed:
   PrsCvA `PlanetLandCondition` and `VisibleConditional` 177→21002; JnkKgA land 182→21003; SunTlA land 181→21006;
   RprGtA `VisibleConditional` and land 178→21100. Keeping the vanilla body inside each new conditional is the AND.
3. **Hub recruits** (Mordin, Garrus, Zaeed, Thane, Samara, Kasumi): separate work in the hub packages
   (BioD_OmgHub_*, BioD_TwrHub_*, BioD_CitHub_*), not the galaxy map.

Open risks to check in game: conditional ids above 2050 resolve (the engine looks functions up by name `F<id>`), and
the planet shows "cannot land" correctly when the AP bool is unset.

## 4. Ship upgrades: research and grant

- Research table: `SFXGame.pcc` `BIOG_2DA_PlotManager_X.Plot_Treasure_Treasure`, rows in Biop_Nor:
  1183 `Tre_Tec_ShipArmor_LmS` (Tec_ShipArmor, Palladium 15000), 1182 `Tre_Tec_ShipGun_GrS` (Tec_ShipGun, Platinum
  15000), 1192 `Tre_Tec_ShipShield_TlS` (Tec_ShipShield, Palladium 15000). Each needs `Dep_Tec_Ship*` level 1.
- Tech table `Plot_Treasure_Tech`: Tec_ShipArmor UnlockId 5642, Tec_ShipGun 5645, Tec_ShipShield 5648 (the
  research "available" bools, as the client's SHIP_UPGRADE_BOOLS has them).
- `SFXPlotTreasure.AwardTech(nmTech)` (SFXGame) sets the plot int named by the tech
  (`PlotManagerGameData`: Tec_ShipArmor int 114, Tec_ShipGun 117, Tec_ShipShield 110; Dep_* 573/575/578). It shows
  the notification, awards the tech bonus and re-locks the tech. It does not set bool 236/237/238.
- The "applied" bools the suicide mission reads (F125/F126/F127, F1260/F1261, F1063..1065, F1087) are set only by
  plot transitions in `Startup_INT.pcc` `PlotManagerAuto.StateTransitionMap`: 280 (236), 281 (237), 282 (238), and
  268/272/274 (237/238/236 plus 5318/220, 5317/224, 5325/226). The only Kismet callers found for 268/272/274 are the
  debug `Set_Spec_Missions_True` sequences in BioD_Nor and BioD_Nor_130TechLabs.
- No normal-play setter for 236/237/238 is in the cooked content. I checked every package (base and DLC, `_LOC_INT`
  conversations included): no conversation entry or reply fires 268/272/274/280/281/282, and the only Kismet callers
  are the debug sequences above plus `SEQ_DEBUG_SetDefaultVariables` in BioP_EndGm1/EndGm2. No
  `BioSeqVar_StoryManagerBool` anywhere points at 236/237/238. No conditional reads the tech ints 110/114/117 or
  bools 5642/5645/5648. `SFXSeqAct_SystemsHandleResearch` and `SFXSeqAct_HandleResearchNotifications` (SFXGameContent
  in BioD_Nor / BioD_Nor_130TechLabs) don't touch them either.
- What research does write (SFXGame script): `AwardTreasure` sets bool <treasure id> (1182/1183/1192 for these rows)
  and charges the cost. `AwardTech` sets plot int `Tec_Ship*` (110/114/117). `ReLockTech` clears the UnlockId bool
  (5642/5645/5648). `HandleResearchNotifications.CheckForUpdates` sets the UnlockId bool TRUE when a project
  qualifies, which offers the project.
- So either native code maps the tech int to 236/237/238, or the suicide mission's reads go through something not
  found here. **Next step, cheap and decisive:** on a throwaway save, read through the bridge bools 236/237/238,
  1182/1183/1192, 5642/5645/5648 and ints 110/114/117 before and after researching one upgrade.
- Note for D21: the client's `SHIP_UPGRADE_BOOLS` sets the UnlockId bool (5642/5645/5648) along with the applied bool.
  UnlockId is the "research available" flag, so setting it offers the research project rather than granting
  anything. With D21 (items only), the item should set only the applied bool (and maybe the tech int).
- Making research grant nothing (D21), options to pick from after the experiment: (a) if 236/237/238 turn out to
  follow the tech int natively, the mod points the three `Plot_Treasure_Treasure` rows' `nmTech` at a dummy tech.
  That table is in SFXGame.pcc; DLCs append `_part_N` tables, but whether a part row can replace a base row is
  unproven. (b) Keep research as is and have the client hold 236/237/238 to the AP item state: write FALSE while
  the item is missing. Simple, but a race: the bool is true until the next poll. (c) Treat the research check as the
  treasure bool (1182/1183/1192) and leave the grant path alone if the experiment shows research never sets
  236/237/238.

## 5. Austin's live run, for the record (2026-10-24)

After a game restart the client logs "ME1 history written" and "Save bound" about 14 s before "game loaded". A fresh
save and reload showed the cause. Plot ints 2100-2102 do persist in the save. But the bridge (`CurrentBioWorld()`)
answers as soon as any world exists, including the main-menu/loading world with a blank plot table, so the client
binds that throwaway table. Then the first RES TXN gets `ERR noplayer` and the real save loads over it, with no
rebind, no mismatch and no re-delivery. Fix (not done): the bridge answers `ERR notready` for ID/IDSET/HIST/GET* while
there is no player pawn, or the client checks readiness before `_check_identity`.

## 6. Hub recruits: where each one starts (traced 2026-10-24, report only)

Runtime winners by mount priority. "S" is a `BioSeqAct_PMCheckState` (plot bool), "C" a `BioSeqAct_PMCheckConditional`.

| Recruit | Package (winner) | Start | Checks on that path | Smallest gate |
|---|---|---|---|---|
| Mordin | BioD_OmgHub_110ProfessorAcq (base) | `BioSeqAct_AreaTransition_1` -> BioP_OmgPrA | S1450, S2697, S1449 | insert S21000 before the transition |
| Garrus | BioD_OmgHub_100Dock (METR_Patch01) | `Garrus_Acquisition_Blue_Suns_Driver.BioSeqAct_AreaTransition_1` -> BioP_OmgGrA | S1458, S2616 | insert S21001 before the transition |
| Thane | BioD_TwrHub_301CarPortHall (base) | `Assassin_Acquisition.BioSeqAct_AreaTransition_1` -> Biop_Twrasa | S107, S1134, S5085 | insert S21004 before the transition |
| Samara | BioD_TwrHub_302CarPort (EXP_Part01) | `Cab_Console.BioSeqAct_AreaTransition_1` -> BioP_TwrMwA | C376 = b1542 && !b43 && !b205 | repoint C376 to F21005 = F376 body && b21005 (same pattern as the galaxy gates) |
| Zaeed | BioD_OmgHub_DLC_Veteran (METR_Patch01) | `Initialization`: two C1495 gate his spawn and recruit conversation | C1495 = b2289 && !b44 && !b206 | repoint both C1495 to F21007 = F1495 body && b21007 |
| Kasumi | BioD_CitHub_DLC_500Thief (HEN_MT) | recruit conversation after S37 (Kasumi in squad), transitions 1356/457/492/95 | S37 | insert S21008 before the recruit conversation; the exact node needs one more pass |

- Each gate is a one-package override in DLC_MOD_ArchipelagoME2, the same mechanism as 0.0.3/0.0.4. Samara and Zaeed
  reuse the new-conditional route (Startup_ArchipelagoME2_INT); the others need one inserted PMCheckState each.
- Gating a transition gives no in-game feedback: the door or driver just does nothing. A friendlier variant routes the
  False link to the vanilla "not now" branch where one exists.
- The alternative is hub-access items. Omega has no galaxy-map conditional; Illium is F491 (b312), the Citadel F197
  (TRUE). That would gate the hub planets in the galaxy override instead: three planets, coarser, simpler.

## 7. D21 resolved (2026-10-26)

Live read on a non-AP save (Vector's career, client closed): researching Heavy Ship Armor set treasure bool 1183 and
tech int 114 only. Applied bool 237 stayed 0 after research, a galaxy-map jump, an elevator trip and a save/reload. The
suicide mission reads only the applied bools: 237 armor (BioD_EndGm1_120Bridge intro), 236 shields (220Cutscenes
Sheilds_Upgrade_Consiquence), 238 cannon (240Cutscenes Weapon_Upgrade_Consiquence). No normal-play setter was found
(transitions 268/272/274/280-282 have only debug callers; no conversation, StoryManagerBool, AwardTechBonus case or
config entry). So the SHIP item writes the applied bool, and the client keeps 236-238 equal to "item received" each
poll (bridge SETB allowlist), so the vanilla research stays a check and grants nothing.
