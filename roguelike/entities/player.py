from typing import (
    ClassVar,
    Dict,
    Sequence,
    TYPE_CHECKING
)

import pygame as pg

from roguelike.engine import (
    event_manager,
    inputs,
    sprite,
    tween
)
from roguelike.entities import entity

if TYPE_CHECKING:
    from roguelike.engine.renderer import Renderer

class PlayerEntity(entity.Entity):
    """The player"""
    name = 'Player'

    sqr_sprite: ClassVar[sprite.Sprite]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, passable=False, **kwargs)
    
    def update_entity(self, delta_time, state, _):
        super().update_entity(delta_time, state, _)
        prop = None
        shift_pressed =\
            state.inputstate.keys[pg.K_LSHIFT][inputs.KeyState.PRESSED]\
            or state.inputstate.keys[pg.K_RSHIFT][inputs.KeyState.PRESSED]
        _n_dungeon_pos = self.dungeon_pos[:]
        if state.inputstate.keys[pg.K_UP][inputs.KeyState.DOWN]:
            diff = -state.tile_size
            _n_dungeon_pos[1] -= 1
            self.anim.direction = sprite.AnimDir.UP
            prop = 'y'
        if state.inputstate.keys[pg.K_DOWN][inputs.KeyState.DOWN]:
            diff = state.tile_size
            _n_dungeon_pos[1] += 1
            self.anim.direction = sprite.AnimDir.DOWN
            prop = 'y'
        if state.inputstate.keys[pg.K_LEFT][inputs.KeyState.DOWN]:
            diff = -state.tile_size
            _n_dungeon_pos[0] -= 1
            self.anim.direction = sprite.AnimDir.LEFT
            prop = 'x'
        if state.inputstate.keys[pg.K_RIGHT][inputs.KeyState.DOWN]:
            diff = state.tile_size
            _n_dungeon_pos[0] += 1
            self.anim.direction = sprite.AnimDir.RIGHT
            prop = 'x'
        if prop is not None\
                and state.dungeon_map.is_free(tuple(_n_dungeon_pos))\
                and not shift_pressed:
            self.dungeon_pos = _n_dungeon_pos
            rect = self.rect
            self.anim.state = sprite.AnimState.WALK
            self.anim.time = 0
            tw = tween.Tween(rect,
                             prop,
                             getattr(rect, prop),
                             getattr(rect, prop) + diff,
                             0.25)
            twp = tween.Tween(self.anim,
                              'state',
                              sprite.AnimState.WALK,
                              sprite.AnimState.IDLE,
                              0,
                              step=True)
            anim = tween.Animation([(0, tw), (0.25, twp)])
            anim.attach(state)
            state.begin_animation(anim)
            def _event(state, event):
                while state.locked():
                    yield True
                state.let_entities_move()
                yield False
            state.start_event(event_manager.Event(_event))
    
    def render_entity(self, delta_time, renderer, base_offset):
        super().render_entity(delta_time, renderer, base_offset)
        if self.anim.state == sprite.AnimState.IDLE:
            x_off, y_off = 0, 0
            if self.anim.direction == sprite.AnimDir.DOWN\
                    or self.anim.direction == sprite.AnimDir.DEFAULT:
                y_off = 1
            elif self.anim.direction == sprite.AnimDir.UP:
                y_off = -1
            elif self.anim.direction == sprite.AnimDir.LEFT:
                x_off = -1
            elif self.anim.direction == sprite.AnimDir.RIGHT:
                x_off = 1
            renderer.render_sprite(PlayerEntity.sqr_sprite,
                (self.rect.x + base_offset[0] + x_off * self.rect.w,
                 self.rect.y + base_offset[1] + y_off * self.rect.h),
                (self.rect.w, self.rect.h))
    
    @classmethod
    def init_sprites(cls, renderer: 'Renderer') -> None:
        texture = renderer.load_texture('player_debug.png')
        down = sprite.Animation.from_atlas(texture, (64, 64), (
            (0, 0), (64, 0), (128, 0), (192, 0)
        ))
        up = sprite.Animation.from_atlas(texture, (64, 64), (
            (0, 64), (64, 64), (128, 64), (192, 64)
        ))
        left = sprite.Animation.from_atlas(texture, (64, 64), (
            (0, 128), (64, 128), (128, 128), (192, 128)
        ))
        right = sprite.Animation.from_atlas(texture, (-64, 64), (
            (63, 128), (127, 128), (191, 128), (255, 128)
        ))
        walking: Dict[sprite.AnimDir, Sequence[sprite.Sprite]] = {
                sprite.AnimDir.DOWN: down,
                sprite.AnimDir.UP: up,
                sprite.AnimDir.LEFT: left,
                sprite.AnimDir.RIGHT: right,
                sprite.AnimDir.DEFAULT: down
            }
        standing: Dict[sprite.AnimDir, Sequence[sprite.Sprite]] = {
                sprite.AnimDir.DOWN: down[:1],
                sprite.AnimDir.UP: up[:1],
                sprite.AnimDir.LEFT: left[:1],
                sprite.AnimDir.RIGHT: right[:1],
                sprite.AnimDir.DEFAULT: down[:1]
            }
        cls.class_anim = sprite.Animation({
            sprite.AnimState.DEFAULT: standing,
            sprite.AnimState.IDLE: standing,
            sprite.AnimState.WALK: walking,
        }, 12)
        
        cls.sqr_sprite = sprite.Sprite(
            renderer.load_texture('effects.png'),
            (0, 0), (64, 64))
    