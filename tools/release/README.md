# Mass Effect Legendary Edition 2 for Archipelago

Recruit the team, earn their loyalty and stop the Collectors, with dossiers, ship upgrades, Reaper IFF intel, DLC keys
and loyalty missions scattered across the multiworld.

## What you need

- Mass Effect Legendary Edition (PC) with ME2.
- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
- [ME3Tweaks Mod Manager](https://me3tweaks.com/modmanager/), with the LE2 target set and its ASI loader installed
  (Tools > ASI Mod Manager; installing any ASI from there adds the loader).

## Install

Close Mass Effect 2 and the Archipelago client, then in this folder run:

    powershell -ExecutionPolicy Bypass -File install.ps1

It copies `mass_effect_le2.apworld` into Archipelago's `custom_worlds`, `LE2APBridge.asi` into ME2's
`Binaries\Win64\ASI`, and has Mod Manager install the `ArchipelagoME2` mod. Pass `-Archipelago`, `-GameDir` or
`-ModManager` if yours aren't in the default places. Anything replaced is backed up in `backup\`, and `uninstall.ps1`
restores it. Without the script: double-click the .apworld (or copy it to custom_worlds), copy the .asi to the ASI
folder, and drag `ArchipelagoME2-mod.zip` onto Mod Manager.

## Play

1. Edit `Mass Effect Legendary Edition 2.yaml` (every option is explained in it; you can also use the launcher's
   Options Creator) and give it to whoever generates the seed.
2. Start Mass Effect 2 and pick **New Career**. The mod skips the prologue and Genesis and starts you on the Normandy.
   The client only connects to careers started with the mod, so it will never touch your normal saves.
3. In Archipelago's launcher open **Mass Effect LE2 Client** and connect to the room (e.g. `archipelago.gg:12345`)
   with your slot name.

Items arrive while you play. Recruitment and loyalty missions, DLC missions and the Derelict Reaper open as their
items come in. Missed mission pickups can be bought back at the Normandy's research terminal ("Salvage").

## Hosting on archipelago.gg

Generate the seed with Archipelago's Generate (this world's .apworld in custom_worlds). Upload the resulting
`AP_*.zip` at https://archipelago.gg/uploads and create a room. Players then connect with the address it shows.
