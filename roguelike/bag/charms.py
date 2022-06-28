from typing import Dict

from roguelike.engine import assets
from roguelike.bag import item

items: Dict[str, item.CharmItem] = {}

def init_items() -> None:
    for name, value in assets.residuals.pop('charms').items():
        display = value.get('display', name.title())
        description = value.get('description')
        icon = assets.Sprites.instance.sprites[value['icon']]
        power = value.get('power', 1.0)
        mp = value.get('mp', 1.0)
        charm_item = item.CharmItem(name=name,
                                    display=display,
                                    description=description,
                                    icon=icon,
                                    pow_mul=power,
                                    mpr_mul=mp)
        items[name] = charm_item
    item.items.update(items)