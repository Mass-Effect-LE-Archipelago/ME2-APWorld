"""Write tools/le2mod/salvage.json from the world's salvage table, for the le2mod build (D22).

usage: python tools/export_salvage.py <Archipelago checkout with worlds/mass_effect_le2>
The world test test_salvage_json_matches_data keeps the committed file in step with data.py.
"""
import json
import pathlib
import sys


def salvage_json() -> str:
    from worlds.mass_effect_le2 import client, data
    return json.dumps({
        "bought_int_base": client.SALVAGE_BOUGHT_INT_BASE,
        "cap_int_base": client.SALVAGE_CAP_INT_BASE,
        "tier_disable_base": client.SALVAGE_TIER_DISABLE_BASE,
        "prices": list(data.SALVAGE_PRICES),
        "missions": [{"index": k, "area": area, "label": label, "pickups": len(data.SALVAGE_PICKUPS[area])}
                     for k, (area, label, _) in enumerate(data.SALVAGE_MISSIONS)],
    }, indent=1) + "\n"


if __name__ == "__main__":
    sys.path.insert(0, sys.argv[1])
    out = pathlib.Path(__file__).resolve().parent / "le2mod" / "salvage.json"
    out.write_text(salvage_json(), newline="\n")
    print(out)
