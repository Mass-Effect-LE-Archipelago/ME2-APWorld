# Missed-checks salvage store (research 2026-10-25, read-only)

Austin's idea: for each finished mission that can't be replayed, an always-reachable store sells one entry (e.g.
"Korlus Salvage"). Buying it sends every pickup check of that mission still unchecked.

## How LE2 stores work (traced)

- **Purchase writes a bool the client can read.** `SFXPlotTreasure.AwardTreasure(nTreasureId)` (SFXGame) checks
  `CanAffordTreasure`, `QualifiesForTreasure` and `ChargeForTreasure`, calls `AwardTech(nmTech)`, then
  `SetBool(nTreasureId, TRUE)` for single-level entries. The treasure id is the plot bool.
- **Availability is a tech int, not a bool.** `QualifiesForTreasure` refuses an entry that is already bought (bool set,
  single level). It also refuses one whose `GetIntByName(nmRequiredTech) < RequiredTechLevel`. Names resolve to plot
  ints through the `PlotManagerGameData` 2DA.
- **Tables:** `SFXGame.pcc` `BIOG_2DA_PlotManager_X.Plot_Treasure_Treasure` (nmLevel, nmTreasure, nmTech, nmResource,
  nPrice, nmRequiredTech, nRequiredTechLevel, nDiscoverTechLevel, nNoAnimation, nMultiLevel), `Plot_Treasure_Tech`
  (strrefs srTitle/srName/srMessage/srDescription, UnlockId, images) and `PlotManagerGameData` (name -> plot int).
  **DLCs append rows** through `_part_N` tables in their `Startup_<dlc>_INT.pcc`. For example, DLC_HEN_VT has
  `BIOG_2DA_HEN_VT_PlotManager_X.Plot_Treasure_Treasure_part_100` (rows 6275-6277), `Plot_Treasure_Tech_part_100`
  (10001), `PlotManagerGameData_part_100` and `Plot_Treasure_Resources_part_100`. Our startup package can carry the
  same tables.
- **The store menu itself is Kismet, per hub.** For example BioD_TwrHub_302CarPort `Stores.Store_Choice_GUI_Logic*`:
  `BioSeqAct_AddChoiceGUIElement` lines (strref name, title, description; a `LineAdded/LineNotAdded` sub-sequence per
  item) -> `BioSeqAct_ShowChoiceGUI` -> per item `BioSeqAct_ShowMessage` (confirm) -> `BioSeqAct_AwardTreasure`
  -> `ItemPurchased` -> a plot transition. No store reads the treasure table by itself: each line is hand-wired.

## Feasibility

Feasible with the mechanisms 0.0.4-0.0.6 already use (an override package, our startup package, our TLK, client-set
bools), but it is more work than a gate: it needs a menu of new Kismet lines.

## Smallest design

1. **Data (world/client):** each non-replayable mission area key already groups its pickups (`pickups.py`,
   `data.PICKUP_AREAS`), and each mission has a done bool (its completion location rule). For each mission k with
   pickups, the client sets **bool 21300+k** ("salvage available") once the mission is done and at least one of its
   pickups is unchecked. It watches **bool 21400+k** ("salvage bought") and, when that is set, sends every unchecked
   pickup location of mission k. Both are in the AP bool range the bridge already allows (SETB 21000-21999).
2. **Menu (mod), free version:** one override of an always-usable Normandy object's package. Candidates are a CIC or
   cabin terminal; picking one is the open item, since it has to be reachable all game. Using it opens a choice menu
   with one line per mission. Each line is `PMCheckState(21300+k)` -> `AddChoiceGUIElement` (name and description
   strrefs in our DLC_4100_INT.tlk, e.g. "Korlus Salvage"). Picking a line confirms, then sets bool 21400+k. No 2DA
   rows are needed.
3. **Priced version (optional):** add `Plot_Treasure_Treasure_part_N` rows (ids 21400+k, so the purchase bool is the
   "bought" bool, nmResource Credits, price) and matching `Plot_Treasure_Tech_part_N` / `PlotManagerGameData_part_N`
   rows in Startup_ArchipelagoME2_INT. Each line's confirm then runs `BioSeqAct_AwardTreasure(21400+k)` instead of a
   SetBool, and the game charges the credits.
4. **Bridge:** no change for the free version. The priced version needs nothing more, because availability stays on
   the Kismet bool check rather than a tech int.

Zero-mod alternative: a YAML option "auto-salvage", where the client sends a mission's unchecked pickups as soon as
its done bool is set. Trivial, but there's no in-game choice or cost.

Open items before building: choose the Normandy object, list the non-replayable missions (exclude hubs and the
Normandy), and decide whether the entries are free or priced.

## Built design (le2mod 0.0.7, 2026-10-26; Austin: priced per missed check, on a Normandy terminal)

- **Where:** the Normandy research terminal (SFXSeqAct_ResearchChoiceGUI). Its list is config, not Kismet:
  `[SFXGame.SFXGameChoiceGUIData_Research] Research=(PlotName, TreasureId, UnlockId, RMode, DisableId, ChoiceEntry)`
  in BIOUI.ini. So the mod appends entries with `+Research=` in its own BIOUI.ini and needs no new Kismet. The
  terminal's Kismet (BioD_Nor_130TechLabs) opens the GUI on Used with no plot check, but in vanilla the tech lab is
  only reachable once Mordin is recruited. Salvage therefore needs Mordin. If that's a problem, the follow-up is to open
  the lab early.
- **Price per check, how:** a treasure row has one fixed price, so each mission k is one **multi-level** tech
  (Tec_APSalvage_k, nLevels 10, plot int 2110+k) whose treasure rows are multi-level. Each purchase raises the level by
  one and charges one check's price. The client **takes** the level each poll (bridge TAKEI reads it and sets it to 0
  in one game-thread step), sends that many of the mission's open pickups, lowest id first, and sets the cap int
  APSalvageCap_k (2150+k) to the open pickups left. The entry shows and qualifies only while level < cap, so you can
  never buy more than what's missing, and since the level returns to 0 the 10-level cap never binds. This was chosen
  over count tiers or a row per pickup: one row per mission per price, with no per-count rows and no per-pickup lines.
- **Price option:** the row price is fixed when the mod is built, so the YAML `salvage_price` picks one of five tiers
  (free, 500, 1000 default, 2500, 5000). Each mission has one treasure row per tier (ids 21500+5k+t). Every entry for
  tier t carries DisableId 21310+t, and the client sets the other tiers' disable bools, so only the chosen price shows.
  `salvage: false` (or pickups off) disables all tiers and keeps every cap at 0.
- **Rows** (Startup_ArchipelagoME2_INT, package BIOG_2DA_ArchipelagoME2_PlotManager_X, registered with
  `+Package=` in BIOEngine.ini, tables cloned from DLC_HEN_VT's _part_100): Plot_Treasure_Tech_part_4100 (28 techs,
  rows 41000+k), Plot_Treasure_Treasure_part_4100 (140 rows: nmLevel Biop_Nor, Credits, the tier price, nmRequiredTech
  APSalvageCap_k, multi-level), PlotManagerGameData_part_4100 (Tec_APSalvage_k -> 2110+k, APSalvageCap_k -> 2150+k,
  plus the vanilla sentinel row). Strings in DLC_4100_INT.tlk: "<mission> Salvage" (41000100+k), a description and a
  purchase message.
- **Missions:** `data.SALVAGE_MISSIONS`, the 28 non-hub pickup areas, each with its completion location; it is
  exported to tools/le2mod/salvage.json by tools/export_salvage.py, and a world test keeps the two in sync.
- **Untested in game:** the entries' placement (RMode 0 = top level), DLC config merge of `+Research=`, and
  multi-level research purchase flow for a modded tech. The tables and ini are validated statically.
