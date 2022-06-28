from typing import (
    TYPE_CHECKING
)

from roguelike.engine import assets
from roguelike.entities import entity
from roguelike.bag import item

if TYPE_CHECKING:
    from roguelike.entities.player import PlayerEntity
    from roguelike.engine.gamestate import GameState

class ItemEntity(entity.Entity):
    interactable = True
    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop('name', 'Pursuant')
        self.item = item.items[kwargs.pop('item')]
        self.class_anim = self.item.icon
        self.count = kwargs.pop('count', 1)
        super().__init__(*args, passable=False, **kwargs)
        if self.anim is not None:
            self.anim.speed = 0
    
    def interact(self,
                 current_state: 'GameState',
                 player: 'PlayerEntity') -> None:
        self.pain_particle(current_state,
            f'Got {self.item.display} x{self.count}!', (1, 1, 1, 1))
        player.inventory.give_item(self.item, self.count)
        assets.Sounds.instance.budu.play()
        self.entity_die(current_state, None)

class KeyEntity(ItemEntity):
    def __init__(self, *args, **kwargs):
        self.needed = kwargs.pop('needed')
        super().__init__(*args, **kwargs)
    
    def interact(self,
                 current_state: 'GameState',
                 player: 'PlayerEntity') -> None:
        player.inventory.give_item(self.item, self.count)
        has = player.inventory[self.item]
        self.pain_particle(current_state,
            f'{self.item.display} {has}/{self.needed}', (1, 1, 0, 1))
        assets.Sounds.instance.budu.play()
        self.entity_die(current_state, None)

entity.entities['ItemEntity'] = ItemEntity
entity.entities['KeyEntity'] = KeyEntity