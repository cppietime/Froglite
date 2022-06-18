from typing import (
    cast,
    Any,
    Dict
)

from roguelike.engine import assets
from roguelike.bag import item

items: Dict[str, item.WeaponItem] = {}

def init_items() -> None:
    weapons: Dict[str, Dict[str, Any]] = assets.residuals['weapons']
    for name, value in weapons.items():
        description = cast(str, value['description'])
        icon_key = cast(str, value['icon'])
        icon = assets.Sprites.instance.sprites[icon_key]
        attack = cast(float, value.get('attack', 1))
        items[name] = item.WeaponItem(name, icon, description, attack)
    item.items.update(items)