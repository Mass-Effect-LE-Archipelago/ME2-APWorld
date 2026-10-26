<#
.SYNOPSIS
  Installs the Mass Effect Legendary Edition 2 Archipelago world, game bridge and mod.

.DESCRIPTION
  1. Copies mass_effect_le2.apworld into Archipelago's custom_worlds folder.
  2. Copies LE2APBridge.asi into ME2's Binaries\Win64\ASI folder (needs ME3Tweaks Mod Manager's ASI loader).
  3. Installs the DLC_MOD_ArchipelagoME2 mod through ME3Tweaks Mod Manager (or tells you how to import it).
  Anything it replaces is copied to a backup folder next to this script first; uninstall.ps1 puts it back.
  Close Mass Effect 2 and the Archipelago client before running.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File install.ps1
  powershell -ExecutionPolicy Bypass -File install.ps1 -Archipelago "D:\Archipelago" -GameDir "D:\Games\Mass Effect Legendary Edition\Game\ME2" -ModManager "C:\Tools\ME3TweaksModManager.exe"
#>
param(
    [string]$Archipelago = "C:\ProgramData\Archipelago",
    [string]$GameDir = "",
    [string]$ModManager = ""
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$backup = Join-Path $here "backup"
New-Item -ItemType Directory -Force $backup | Out-Null

function Backup-File($path, $name) {
    if (Test-Path $path) { Copy-Item $path (Join-Path $backup $name) -Force; Write-Host "  backed up $path" }
}

if (Get-Process MassEffect2 -ErrorAction SilentlyContinue) { throw "Close Mass Effect 2 first." }

# 1. Archipelago world
if (-not (Test-Path (Join-Path $Archipelago "ArchipelagoLauncher.exe"))) {
    throw "Archipelago not found at $Archipelago (pass -Archipelago <folder>)."
}
$worlds = Join-Path $Archipelago "custom_worlds"
New-Item -ItemType Directory -Force $worlds | Out-Null
Backup-File (Join-Path $worlds "mass_effect_le2.apworld") "mass_effect_le2.apworld"
Copy-Item (Join-Path $here "mass_effect_le2.apworld") $worlds -Force
Write-Host "Installed the world into $worlds"

# 2. Game folder and bridge
if (-not $GameDir) {
    foreach ($steam in @("C:\Program Files (x86)\Steam", "C:\Steam", "D:\Steam", "D:\SteamLibrary", "E:\SteamLibrary")) {
        $candidate = Join-Path $steam "steamapps\common\Mass Effect Legendary Edition\Game\ME2"
        if (Test-Path $candidate) { $GameDir = $candidate; break }
    }
}
if (-not $GameDir -or -not (Test-Path (Join-Path $GameDir "Binaries\Win64\MassEffect2.exe"))) {
    throw "Mass Effect 2 LE not found (pass -GameDir <...\Mass Effect Legendary Edition\Game\ME2>)."
}
$win64 = Join-Path $GameDir "Binaries\Win64"
if (-not (Test-Path (Join-Path $win64 "bink2w64_original.dll"))) {
    throw "The ASI loader is missing. In ME3Tweaks Mod Manager pick the LE2 target and use Tools > ASI Mod Manager (any ASI install adds the loader), then run this again."
}
$asi = Join-Path $win64 "ASI"
New-Item -ItemType Directory -Force $asi | Out-Null
Backup-File (Join-Path $asi "LE2APBridge.asi") "LE2APBridge.asi"
Copy-Item (Join-Path $here "LE2APBridge.asi") $asi -Force
Write-Host "Installed the bridge into $asi"

# 3. Mod (ME3Tweaks Mod Manager installs it and refreshes the game's file table)
$installed = Join-Path $GameDir "BioGame\DLC\DLC_MOD_ArchipelagoME2"
if (Test-Path $installed) {
    $dest = Join-Path $backup "DLC_MOD_ArchipelagoME2"
    if (-not (Test-Path $dest)) { Copy-Item $installed $dest -Recurse; Write-Host "  backed up the installed mod" }
}
$moddesc = Join-Path $here "ArchipelagoME2\moddesc.ini"
if (-not $ModManager) {
    $ModManager = (Get-ChildItem "$env:LOCALAPPDATA", "$env:USERPROFILE\Documents", "$env:USERPROFILE\Downloads" -Recurse -Depth 3 `
        -Filter ME3TweaksModManager.exe -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
}
if ($ModManager -and (Test-Path $ModManager)) {
    Start-Process -FilePath $ModManager -ArgumentList "--installmod `"$moddesc`" --game LE2"
    Write-Host "Mod Manager is installing the mod; confirm any prompt it shows."
} else {
    Write-Host "Mod Manager not found: drag ArchipelagoME2-mod.zip onto ME3Tweaks Mod Manager (LE2 target) and install it."
}
Write-Host "Done. Start Archipelago's launcher and open 'Mass Effect LE2 Client' to play."
