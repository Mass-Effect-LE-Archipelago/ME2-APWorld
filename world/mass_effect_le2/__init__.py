from worlds.LauncherComponents import Component, Type, components, launch as launch_component

from .world import MassEffectLE2World as MassEffectLE2World


def launch_client(*args: str) -> None:
    from .client import launch
    launch_component(launch, name="ME2Client", args=args)


components.append(Component("Mass Effect LE2 Client", func=launch_client, component_type=Type.CLIENT,
                            game_name="Mass Effect Legendary Edition 2", supports_uri=True,
                            description="Connects Mass Effect Legendary Edition 2 (LE2APBridge) to a multiworld."))
