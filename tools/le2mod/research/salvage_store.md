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
