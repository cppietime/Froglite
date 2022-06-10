import math
from typing import (
    cast,
    Tuple,
    TYPE_CHECKING
)

from roguelike.engine import (
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
        current_other = target.dungeon_pos[dprop_i] * state.tile_size
        anim = tween.Animation([
            (0, tween.Tween(self.rect,
                            dprop,
                            current_self,
                            current_other,
                            0.1)),
            (0.1, tween.Tween(self.rect,
                              dprop,
                              current_other,
                              current_self,
                              0.15)),
            (0.15, tween.Tween(my_anim,
                               'state',
                               0,
                               sprite.AnimState.IDLE,
                               0,
                               step=True))
        ])
        anim.attach(state)
        state.begin_animation(anim)
    
    def take_action(self,
                      state: 'GameState',
                      player_pos: Tuple[int, int]) -> None:
        state = cast('DungeonMapState', state)
        my_anim = cast(sprite.AnimationState, self.anim)
        path = state.dungeon_map.a_star(tuple(self.dungeon_pos), player_pos)
        if path is None:
            # Player cannot be reached, just sit still
            return
        if len(path) < 3:
            # Player is within one square
            self.attack(state, state.dungeon_map.player)
            return
        next_step = path[1]
        # Animations and motion
        my_anim.state = sprite.AnimState.WALK
        prop = None
        if next_step[0] < self.dungeon_pos[0]:
            my_anim.direction = sprite.AnimDir.LEFT
            prop = 'x'
        elif next_step[0] > self.dungeon_pos[0]:
            my_anim.direction = sprite.AnimDir.RIGHT
            prop = 'x'
        elif next_step[1] < self.dungeon_pos[1]:
            my_anim.direction = sprite.AnimDir.UP
            prop = 'y'
        elif next_step[1] > self.dungeon_pos[1]:
            my_anim.direction = sprite.AnimDir.DOWN
            prop = 'y'
        if prop is not None\
                and state.dungeon_map.move_entity(tuple(self.dungeon_pos),
                                                  next_step):
            anim = tween.Animation([
                (0, tween.Tween(self.rect,
                                prop,
                                getattr(self.rect, prop),
                                self.dungeon_pos[0 if prop == 'x' else 1]\
                                    * state.tile_size,
                                0.25)),
                (0.25, tween.Tween(my_anim,
                                'state',
                                0,
                                sprite.AnimState.IDLE,
                                0,
                                step=True))
            ])
            anim.attach(state)
            state.begin_animation(anim)
        # if state.dungeon_map.move_entity(tuple(self.dungeon_pos), next_step):
            # self.rect.x = self.dungeon_pos[0] * state.tile_size
            # self.rect.y = self.dungeon_pos[1] * state.tile_size
    
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
                sprite.AnimDir.DEFAULT: seq[:1]
            },
            sprite.AnimState.WALK: {
                sprite.AnimDir.DEFAULT: seq
            },
            sprite.AnimState.ATTACK: {
                sprite.AnimDir.DEFAULT: seq
            }
        }, 6)