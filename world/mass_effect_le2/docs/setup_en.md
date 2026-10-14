# Mass Effect Legendary Edition 2 setup guide

## Requirements

- Mass Effect Legendary Edition (PC), with Mass Effect 2 installed.
- [ME3Tweaks Mod Manager](https://me3tweaks.com/modmanager/), used to install the ASI loader for LE2.
- Archipelago 0.6.8 or newer.
- `mass_effect_le2.apworld` and `LE2LE2APBridge.asi` from a release.

## Installing

1. Put `mass_effect_le2.apworld` in your Archipelago `custom_worlds` folder.
2. In ME3Tweaks Mod Manager, select the LE2 target and install the ASI loader (Tools > ASI Mod Manager).
3. Copy `LE2LE2APBridge.asi` into `Game/ME2/Binaries/Win64/ASI/`.

## Playing

1. Generate a seed with your options YAML and host or join the room.
2. Start "Mass Effect LE2 Client" from the Archipelago Launcher and connect to the room.
3. Start a new career (or load the save you started this seed with). The client binds a new save to your slot on first
   contact and refuses saves from other seeds, so keep one career per seed.
4. Play. Checks are sent while the client runs; anything done offline is sent the next time the client sees the save.
