from typing import (
    cast,
    Any,
    Dict,
    TYPE_CHECKING
)

from roguelike.engine import assets
from roguelike.bag import item

items = {}

def init_items() -> None:
    key_specs: Dict[str, Dict[str, Any]] = assets.residuals.pop('keys')
    for name, value in key_specs.items():
        description = cast(str, value['description'])
        icon_key = cast(str, value['icon'])
        display = value.get('display', name.title())
        icon = assets.Sprites.instance.sprites[icon_key]
        items[name] = item.KeyItem(name, icon, description, display)
    item.items.update(items)