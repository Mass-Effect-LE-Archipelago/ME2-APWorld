from BaseClasses import Tutorial
from worlds.AutoWorld import WebWorld

from .options import option_groups, options_presets


class MassEffectLE2WebWorld(WebWorld):
    theme = "dirt"
    game_info_languages = ["en"]
    options_presets = options_presets
    option_groups = option_groups
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up Mass Effect Legendary Edition 2 for Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["Jerrod"],
    )]
