import math
from typing import (
    cast,
    Tuple,
    TYPE_CHECKING
)

from roguelike.engine import (
    event_manager,
    sprite,
    tween
)

from roguelike.entities import entity

if TYPE_CHECKING:
    from roguelike.engine.renderer import Renderer
    from roguelike.engine.gamestate import GameState
    from roguelike.states.dungeon import DungeonMapState

class SlowChaserEntity(entity.EnemyEntity):
    """Slowly chases after the player"""
    name = 'Slow Chaser'
    detection_radius = 5
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         passable=False,
                         action_cost=2,
                         max_hp=16,
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
    
    @classmethod
    def init_sprites(cls, renderer: 'Renderer') -> None:
        texture = renderer.load_texture('monsters/slow_chaser.png')
        seq = sprite.Animation.from_atlas(texture, (64, 64), ((0, 0),
                                                              (0, 0),
                                                              (0, 0),
                                                              (0, 0)))
        for i, spr in enumerate(seq):
            spr.angle = -i * math.pi / 2
        cls.class_anim = sprite.Animation({
            sprite.AnimState.DEFAULT: {
                sprite.AnimDir.DEFAULT: seq
            },
            sprite.AnimState.WALK: {
                sprite.AnimDir.DEFAULT: seq
            },
            sprite.AnimState.ATTACK: {
                sprite.AnimDir.DEFAULT: seq
            }
        }, 6)