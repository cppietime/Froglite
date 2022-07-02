from typing import (
    Dict,
    TYPE_CHECKING
)

from roguelike.engine import assets

def save_game(world_type_name: str, player: 'PlayerEntity') -> None:
    current_save: Dict[str, Any] =\
        assets.persists['current'].setdefault(world_type_name, {})
    current_save['difficulty'] = assets.variables['difficulty']
    current_save['hp'] = player.hp
    current_save['mp'] = player.mp
    inv_dict: Dict['BaseItem', int] = {}
    for slot in player.inventory.items.values():
        inv_dict.update(slot)
    current_save['inventory'] = inv_dict
    current_save['coins'] = assets.variables['coins']
    assets.save_save()

def load_game(world_type_name: str, player: 'PlayerEntity') -> None:
    current_save: Dict[str, Any] =\
        assets.persists['current'].get(world_type_name, {})
    assets.variables['difficulty'] =\
        current_save.get('difficulty', 0)
    for itm, num in current_save.get('inventory', {}).items():
        player.inventory.give_item(itm, num)
    player.hp =\
        current_save.get('hp', player.hp)
    player.mp =\
        current_save.get('mp', player.mp)
    assets.variables['coins'] = current_save.get('coins', 0)

def die(world_type_name: str) -> None:
    assets.persists['current'].setdefault(world_type_name, {}).clear()
    assets.save_save()