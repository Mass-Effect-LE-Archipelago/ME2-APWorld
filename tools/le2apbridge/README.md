# LE2APBridge

ASI plugin that connects Mass Effect 2 Legendary Edition to the Archipelago client (`world/mass_effect_le2/client.py`)
over a named pipe. Ported from LE1APBridge v11; the contract is [PROTOCOL.md](PROTOCOL.md).

## Build (Windows, Visual Studio 2022 or 2026 with C++)

The bridge builds inside an [LExASIs](https://github.com/ME3Tweaks/LExASIs) checkout, which provides LExSDKv2 (with the
LE2 target), the `Common` library and the `asi_target` CMake function.

1. Copy (or symlink) `LE2APBridge/` into the LExASIs root, next to `Common/`.
2. Add `add_subdirectory ("LE2APBridge")` to the LExASIs root `CMakeLists.txt`.
3. Set `LEASI_CMAKE_PRESET` as LExASIs requires, and optionally `LEASI_GAME2_WIN64` to your LE2 `Game/ME2/Binaries/Win64`
   folder so the build copies the ASI into its `ASI/` folder.
4. Configure and build the `LE2APBridge-LE2` target. The output is `LE2LE2APBridge.asi`.

## Install

ME3Tweaks Mod Manager installs the ASI loader for LE2. Put `LE2LE2APBridge.asi` in `Game/ME2/Binaries/Win64/ASI/`.
The log is written next to the other LExASIs logs.

## Status

Compiles against LExSDKv2's LE2 target (Visual Studio 2026 Build Tools, 2026-10-14) with no SDK name changes; resource
types follow the SDK enum `EInventoryResourceTypes` (PROTOCOL.md). Not yet run in game: the first runtime spike
(docs/SCOPE.md, Stage 1) exercises every request.
