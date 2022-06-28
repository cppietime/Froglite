from enum import Enum
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
    from roguelike.entities.player import PlayerEntity
    from roguelike.bag.inventory_state import UseTossScreen

class RestorationTarget(Enum):
    HP = 0
    MP = 1

class HealthRestorationItem(item.ConsumableItem):
    def __init__(self,
                 name: str,
                 description: str,
                 display: str,
                 icon: sprite.Sprite,
                 message: str,
                 amount: float,
                 target: RestorationTarget):
        super().__init__(name=name,
                         description=description,
                         display=display,
                         icon=icon,
                         on_use=self.on_use)
        self.message = message
        self.amount = amount
        self.target = target
    
    def on_use(self,
               map_state: 'GameState',
               ui_state: Optional['GameState'],
               user: 'FightingEntity') -> None:
        if ui_state is not None:
            ui_state = cast('UseTossScreen', ui_state)
            ui_state.display_message(self.message.format(self.amount))
        healed = self.amount
        if self.target == RestorationTarget.HP:
            # Do I want to limit healed HP to the max HP?
            user.hp += self.amount
            color = (0, 1, 0, 1)
        elif self.target == RestorationTarget.MP:
            assert hasattr(user, 'mp')
            player = cast('PlayerEntity', user)
            healed = min(player.max_mp - player.mp, self.amount)
            player.mp += healed
            color = (0, 1, 1, 1)
        def _event(state, event):
            while state.locked():
                yield True
            user.pain_particle(map_state, f"+{healed}", color)
            yield False
        map_state.queue_event(event_manager.Event(_event))
    
    @staticmethod
    def create(name: str,
               description: str,
               display_name: str,
               icon: sprite.Sprite,
               params: Dict[str, Any]) -> 'HealthRestorationItem':
        amount = int(params['amount'])
        message = cast(str, params['message'])
        target = RestorationTarget[params.get('type', 'HP').upper()]
        return HealthRestorationItem(
            name, description, display_name, icon, message, amount, target)

# Dict mapping "kind" values to functions to call to create the items
# by their JSON objects
_consumable_kinds = {
    'heal': HealthRestorationItem.create
}

# The global consumable items dict
items: Dict[str, item.ConsumableItem] = {}

def init_items() -> None:
    """Call me to initialize consumables"""
    item_specs = assets.residuals.pop('consumables')
    for name, value in item_specs.items():
        description = cast(str, value['description'])
        icon_key = cast(str, value['icon'])
        icon = assets.Sprites.instance.sprites[icon_key]
        kind = cast(str, value['kind'])
        display = value.get('display', name.title())
        constructor = _consumable_kinds[kind]
        items[name] = constructor(name, description, display, icon, value)
    item.items.update(items)