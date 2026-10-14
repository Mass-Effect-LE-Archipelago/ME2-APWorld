"""Zip world/mass_effect_le2 into build/mass_effect_le2.apworld (tests and caches left out)."""
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORLD = ROOT / "world" / "mass_effect_le2"
OUT = ROOT / "build" / "mass_effect_le2.apworld"

OUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(WORLD.rglob("*")):
        relative = path.relative_to(WORLD)
        if path.is_dir() or "__pycache__" in relative.parts or relative.parts[0] == "test":
            continue
        archive.write(path, pathlib.Path("mass_effect_le2") / relative)
print(OUT)
