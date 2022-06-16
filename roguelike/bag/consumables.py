from typing import (
    cast,
    Any,
    Dict,
    Optional,
    TYPE_CHECKING
)

import moderngl as mgl # type: ignore

from roguelike.bag import item
from roguelike.engine import (
    assets,
    event_manager,
    sprite
)

if TYPE_CHECKING:
    from roguelike.engine.gamestate import GameState
    from roguelike.entities.entity import FightingEntity
    from roguelike.bag.inventory_state import UseTossScreen

potion: item.ConsumableItem

# Now unused
def healing_fn(amount):
    def _fn(map_state: 'GameState',
            ui_state: 'GameState',
            user: 'FightingEntity') -> None:
        ui_state = cast('UseTossScreen', ui_state)
        ui_state.display_message(f"You drank a potion! The aetherial energies swirl within you and rejuvinate your body. Blessed by its healing power, you regain {amount} HP...")
        user.hp += amount
        def _event(state, event):
            while state.locked():
                yield True
            user.pain_particle(map_state, f"+{amount}", (0, 1, 0, 1))
            yield False
        map_state.queue_event(event_manager.Event(_event))
    return _fn

class HealthRestorationItem(item.ConsumableItem):
    def __init__(self,
                 name: str,
                 description: str,
                 icon: sprite.Sprite,
                 message: str,
                 amount: float):
        super().__init__(name=name,
                         description=description,
                         icon=icon,
                         on_use=self.on_use)
        self.message = message
        self.amount = amount
    
    def on_use(self,
               map_state: 'GameState',
               ui_state: Optional['GameState'],
               user: 'FightingEntity') -> None:
        ui_state = cast('UseTossScreen', ui_state)
        ui_state.display_message(self.message.format(self.amount))
        user.hp += self.amount
        def _event(state, event):
            while state.locked():
                yield True
            user.pain_particle(map_state, f"+{self.amount}", (0, 1, 0, 1))
            yield False
        map_state.queue_event(event_manager.Event(_event))
    
    @staticmethod
    def create(name: str,
               description: str,
               icon: sprite.Sprite,
               params: Dict[str, Any]) -> 'HealthRestorationItem':
        amount = int(params['amount'])
        message = cast(str, params['message'])
        return HealthRestorationItem(name, description, icon, message, amount)

# Dict mapping "kind" values to functions to call to create the items
# by their JSON objects
_consumable_kinds = {
    'heal': HealthRestorationItem.create
}

# The global consumable items dict
items: Dict[str, item.ConsumableItem] = {}

def init_items() -> None:
    """Call me to initialize consumables"""
    item_specs = assets.residuals['consumables']
    for name, value in item_specs.items():
        description = cast(str, value['description'])
        icon_key = cast(str, value['icon'])
        icon = assets.Sprites.instance.sprites[icon_key]
        kind = cast(str, value['kind'])
        constructor = _consumable_kinds[kind]
        items[name] = constructor(name, description, icon, value)
    item.items.update(items)