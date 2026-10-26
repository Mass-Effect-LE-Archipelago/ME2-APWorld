<#
.SYNOPSIS
  Removes the Mass Effect LE2 Archipelago world, bridge and mod, restoring anything install.ps1 backed up.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File uninstall.ps1 -GameDir "D:\Games\Mass Effect Legendary Edition\Game\ME2"
#>
param(
    [string]$Archipelago = "C:\ProgramData\Archipelago",
    [string]$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\Mass Effect Legendary Edition\Game\ME2"
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$backup = Join-Path $here "backup"
if (Get-Process MassEffect2 -ErrorAction SilentlyContinue) { throw "Close Mass Effect 2 first." }

function Restore($installed, $name) {
    $saved = Join-Path $backup $name
    if (Test-Path $saved) { Copy-Item $saved $installed -Recurse -Force; Write-Host "restored $installed" }
    elseif (Test-Path $installed) { Remove-Item $installed -Recurse -Force; Write-Host "removed $installed" }
}

Restore (Join-Path $Archipelago "custom_worlds\mass_effect_le2.apworld") "mass_effect_le2.apworld"
Restore (Join-Path $GameDir "Binaries\Win64\ASI\LE2APBridge.asi") "LE2APBridge.asi"
$mod = Join-Path $GameDir "BioGame\DLC\DLC_MOD_ArchipelagoME2"
if (Test-Path $mod) { Remove-Item $mod -Recurse -Force; Write-Host "removed $mod" }
Restore $mod "DLC_MOD_ArchipelagoME2"
Write-Host "Done. Run AutoTOC from ME3Tweaks Mod Manager (or start the game once with the AutoTOC ASI) to refresh the file table."
