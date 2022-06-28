from typing import (
    Dict
)

from roguelike.engine import (
    assets
)
from roguelike.bag import item

items: Dict[str, item.ArmorItem] = {}

def init_items() -> None:
    for name, value in assets.residuals.pop('armor').items():
        display = value.get('display', name.title())
        description = value.get('description')
        icon = assets.Sprites.instance.sprites[value['icon']]
        defense = value.get('defense', 1.0)
        armor_item = item.ArmorItem(name=name,
                                    display=display,
                                    description=description,
                                    icon=icon,
                                    def_mul=defense)
        items[name] = armor_item
    item.items.update(items)