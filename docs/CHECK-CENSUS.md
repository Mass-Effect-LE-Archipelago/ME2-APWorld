# Check and item census (2026-10-26)

Sources: the world's data.py (counts below), docs/CHECKS-CATALOG.md, the save editor's me2_plot_db / me2_raw_plot_db,
and the traces in tools/le2mod/research. "Readable" means the client can poll it through the bridge (plot bool or
int). Today the world has **418 locations max** (387 default).

## Checks

| Family | Count | Marker the client reads | Missable | In world (default) | Feasibility / notes |
|---|---|---|---|---|---|
| Story (Lazarus, Freedom's, Horizon, Collector Ship, IFF) | 5 | reward bools 5794-5797, 5816/1256 | no | yes (on) | done |
| Recruitment | 10 | 5812-5819, Zaeed 44, Kasumi 37 | no | yes (on) | done |
| Loyalty missions | 12 | reward bools 5802-5811 etc. | no (deaths aside) | yes (on) | done |
| Endgame milestones | 4 | 5798-5801 | no | yes (on) | done |
| N7 assignments (planet anomalies) | 19 | 5823-5843 | no | yes (`assignments`) | done; these are the scan anomalies |
| Hub assignments | 31 | 5847-5875 (XP codes) | some (time-limited) | yes (`assignments`) | done |
| DLC missions | 9 | Firewalker 5820-5822/5831/5842, Overlord 6512, LotSB 6815, Arrival 7451, crash site | no | yes (`enabled_dlc`) | done |
| Research projects | 44 | treasure bools (Plot_Treasure_Treasure ids) | no | yes (`research`) | done; ship-upgrade research grants nothing (D21) |
| Collectibles (cabin and armor) | 26 | cabin bools 3321-3338, 7200, 6206, armor bools | some store items | yes (`collectibles`) | done |
| Pickups (credits, resources, upgrade blueprints) | 258 | treasure "found" bools | **yes** (mission areas) | yes (`pickups` safe) | done; salvage (D22) recovers missed ones |
| Weapon pickups (Tre_Wpn_*) | 9 | treasure bools | yes | no | easy; left out so a weapon item can't hide its own pickup |
| Codex entries | up to 207 raw (fewer net of start-unlocked and Paragon/Renegade pairs) | codex bools (CodexMap) | mostly no | no | feasible; needs a pass to drop start-unlocked and paired entries |
| Store purchases (credit rows) | 24 rows (Illium 8, Citadel 6, Omega 5, Tuchanka 5) | treasure bool = row id | no (credits) | partly (cabin and armor overlap) | easy; dedupe against collectibles |
| Cabin extras (helmet, crash-site items) | 1-2 | 6157 helmet | no | partly | easy |
| Normandy Crash Site dog tags | ~20 (unverified) | not found in the editor DB | no | 1 location (site) | needs a trace for per-tag bools |
| Firewalker survey artifacts / per site | 5 (in world) | see DLC row | no | yes | done at mission level; per-artifact needs a trace |
| Overlord per site | 4 sites | site bools (not yet listed) | no | 1 location | needs a trace |
| Level-ups | ~29 (level 2-30) | player level is not a plot value | no | no | possible via a bridge read of the player pawn; medium |
| Paragon / Renegade milestones | e.g. 10 tiers each | plot ints 2 / 3 | no | no | easy (int thresholds); scale is opaque to players |
| Squad talent unlocks (loyalty powers) | 12 | loyalty bools, Tec_LoyaltyPower | no | no (covered by loyalty) | low value; duplicates loyalty |
| Skill points spent | n/a | not plot | no | no | not readable without bridge work; skip |
| Conversation / morality milestones | many | specific plot bools | some | no | case by case; low value |
| Achievements / trophies | ~50 | only a few have plot bools (e.g. 4253) | n/a | no | not feasible generally |

## Item ideas

| Item | What gates it today | Can our mod gate it? | Feasibility |
|---|---|---|---|
| **Progressive Loyalty Mission** (opens the next obtainable, not-done loyalty mission of a recruited squadmate) | Each loyalty mission needs: in squad && !done && "loyalty available" bool (393-404, set by a conversation after Horizon). The galaxy planets check it in conditionals (Zorya F195, Bekenstein F1571, Tali F192, Jacob F188, Miranda F187, ...). | Yes, the same pattern as 0.0.5: AND an AP bool into those planet conditionals (galaxy override). Hub-based loyalty missions (Citadel / Omega / Tuchanka starts) need hub gates like the recruits. The client picks which squadmate's bool to set, in a fixed or random order. | medium; the planet-based ones are easy, the hub ones need about 5 more traces |
| DLC access (Overlord, Arrival, LotSB, Firewalker, Kasumi, Zaeed) | Overlord planet land 1864, Arrival land 1924, LotSB via the Illium cab (Exp1Lvl1 route), Firewalker N7 planets, Kasumi/Zaeed recruits (now gated by dossier) | Yes: galaxy conditionals plus the Illium cab conditional | easy-medium |
| Hub access (Omega, Illium, Citadel, Tuchanka) | Omega none, Illium F491 (b312), Citadel F197 (TRUE), Tuchanka F196 | Yes: galaxy-map hub planets (3-4 conditionals) | easy; coarser than per-dossier |
| Weapon unlocks | in the world (17 items, plot ints) | n/a | done |
| Armor pieces | collectibles today (store bools) | could become items (set the armor bool) | easy; needs a bridge allowlist |
| Ship upgrades | items only (D21) | n/a | done (protocol 4, not installed) |
| Resource bundles, credits | in the world (filler) | n/a | done |

Notes: "Missable" pickups are why salvage exists. Codex, store and weapon pickups are the cheapest ways to add checks.
Progressive Loyalty is the most interesting new item, and our conditional mechanism already covers its planet half.
