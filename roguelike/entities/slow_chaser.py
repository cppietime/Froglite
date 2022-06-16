import math
from typing import (
    cast,
    Tuple,
    TYPE_CHECKING
)

from roguelike.engine import (
    assets,
    event_manager,
    sprite,
    tween
)

from roguelike.entities import (
    entity,
    npc
)

if TYPE_CHECKING:
    from roguelike.engine.renderer import Renderer
    from roguelike.engine.gamestate import GameState
    from roguelike.world.dungeon import DungeonMapState

class PursuantEnemy(entity.EnemyEntity):
    """Slowly chases after the player"""
    # name = 'Slow Chaser'
    # detection_radius = 5
    
    def __init__(self, *args, **kwargs):
        # self.class_anim = assets.Animations.instance.slow_chaser
        self.class_anim = kwargs.pop('anim', None)
        self.name = kwargs.pop('name', 'Pursuant')
        self.detection_radius = kwargs.pop('detection_radius', 5)
        action_cost = kwargs.pop('action_cost', 1)
        max_hp = kwargs.pop('max_hp', 16)
        super().__init__(*args,
                         passable=False,
                         action_cost=action_cost,
                         max_hp=max_hp,
                         **kwargs)
        self.anim.speed = 0
    
    def attack(self,
               state: 'DungeonMapState',
               target: entity.Entity) -> None:
        print(f'{self.name} attacks {target.name}!')
        my_anim = cast(sprite.AnimationState, self.anim)
        my_anim.state = sprite.AnimState.ATTACK
        tpos = target.dungeon_pos
        dprop = 'x' if tpos[0] != self.dungeon_pos[0] else 'y'
        dprop_i = 1 if dprop == 'y' else 0
        current_self = getattr(self.rect, dprop)
        other_x = target.dungeon_pos[0] * state.tile_size
        other_y = target.dungeon_pos[1] * state.tile_size
        def _script(_state, event):
            while _state.locked():
                yield True
            self.animate_stepping_to(state,
                                     (other_x, other_y),
                                     0.25,
                                     sprite.AnimState.IDLE,
                                     0,
                                     interpolation=tween.bounce(1))
            target.get_hit(_state, self, 0)
            yield not _state.locked()
        state.queue_event(event_manager.Event(_script))
    
    def take_action(self,
                      state: 'GameState',
                      player_pos: Tuple[int, int]) -> None:
        super().chase_player(state, player_pos, -1)

class NiceSlowChaser(npc.NPCEntity):
    attackable=False
    actionable=False
    def __init__(self, *args, **kwargs):
        # initial_prompt = npc.ChatPrompt('PeepeePoopoo', ('Fard', 'Shid', 'Cum', 'Quat', 'Dicke', 'Balls'))
        initial_prompt = npc.chats['test_chat']
        self.class_anim = assets.Animations.instance.player
        super().__init__(*args, chat=initial_prompt, **kwargs)