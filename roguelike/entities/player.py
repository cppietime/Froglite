from typing import (
    cast,
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
from roguelike.bag import (
    inventory_state,
    item
)

if TYPE_CHECKING:
    from roguelike.engine.renderer import Renderer

class PlayerEntity(entity.FightingEntity):
    """The player"""
    name = 'Player'

    sqr_sprite: ClassVar[sprite.Sprite]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, passable=False, max_hp=100, **kwargs)
        self.anim.speed = 0
        self.anim.direction = sprite.AnimDir.DOWN
        self.shaky_cam: List[int] = [0, 0]
        self.inventory = item.Inventory()
        self.inv_state = inventory_state.InventoryBaseScreen(
            inventory=self.inventory)
    
    walk_length: ClassVar[float] = .25
    
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
            self.anim.speed = 1
            n_pos_x = self.rect.x + (diff if prop == 'x' else 0)
            n_pos_y = self.rect.y + (diff if prop == 'y' else 0)
            self.animate_stepping_to(state,
                                     (n_pos_x, n_pos_y),
                                     self.walk_length,
                                     sprite.AnimState.IDLE,
                                     0,
                                     None,
                                     True)
            def _event(state, event):
                while state.locked():
                    yield True
                state.let_entities_move()
                yield False
            state.start_event(event_manager.Event(_event))
        if state.inputstate.keys[pg.K_LCTRL][inputs.KeyState.DOWN]:
            # Attempt to attack
            t_x, t_y = self.dungeon_pos
            if self.anim.direction == sprite.AnimDir.UP:
                t_y -= 1
            if self.anim.direction == sprite.AnimDir.DOWN:
                t_y += 1
            if self.anim.direction == sprite.AnimDir.LEFT:
                t_x -= 1
            if self.anim.direction == sprite.AnimDir.RIGHT:
                t_x += 1
            target_ent = state.dungeon_map.entities.get((t_x, t_y), None)
            if target_ent is not None:
                if target_ent.attackable:
                    target_ent = cast(entity.EnemyEntity, target_ent)
                    self.melee_attack(state, target_ent)
                elif target_ent.interactable:
                    # TODO NPC interaction
                    pass
        if state.inputstate.keys[pg.K_RETURN][inputs.KeyState.DOWN]:
            def _menu(state, event):
                while state.locked():
                    yield True
                state.manager.push_state(self.inv_state)
                yield False
            state.queue_event(event_manager.Event(_menu))
    
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
            renderer.render_sprite(self.sqr_sprite,
                (self.rect.x + base_offset[0] + x_off * self.rect.w,
                 self.rect.y + base_offset[1] + y_off * self.rect.h),
                (self.rect.w, self.rect.h))
    
    hit_bounces: ClassVar[float] = 2.
    hit_length: ClassVar[float] = .25
    hit_size: ClassVar[float] = .1
    
    def get_hit(self, state, attacker, damage):
        # Process damage and queue a shaking animation
        self.pain_particle(state, f'-{damage}')
        self.anim.state = sprite.AnimState.HURT
        self.anim.speed = 1
        self.anim.time = 0
        self.shaky_cam[0] = 0
        anim = tween.Animation([
            (0, tween.Tween(self.shaky_cam,
                            0,
                            0,
                            self.rect.w * self.hit_size,
                            self.hit_length,
                            is_list=True,
                            interpolation=tween.shake(self.hit_bounces))),
            (self.hit_length, tween.Tween(self.anim,
                              'state',
                              0,
                              sprite.AnimState.IDLE,
                              0,
                              step=True)),
            (0, tween.Tween(self.anim,
                              'speed',
                              0,
                              0,
                              0,
                              step=True)),
            (0, tween.Tween(self.anim,
                              'time',
                              0,
                              0,
                              0,
                              step=True)),
        ])
        anim.attach(state)
        state.begin_animation(anim)
        
        self.hp -= damage
        if self.hp <= 0:
            self.entity_die(state)
            return False
        return True
        
    def entity_die(self, state):
        pass
    
    attack_length: ClassVar[float] = .25
    
    def melee_attack(self, state, target) -> None:
        # TODO calculate actual damage
        damage = self._melee_attack_logic(state, target) * 0 + 1
        my_anim = cast(sprite.AnimationState, self.anim)
        my_anim.state = sprite.AnimState.ATTACK
        other_x = target.dungeon_pos[0] * state.tile_size
        other_y = target.dungeon_pos[1] * state.tile_size
        anim = tween.Animation([
            (0, tween.Tween(self.shaky_cam,
                            0,
                            0,
                            other_x - self.rect.x,
                            self.attack_length,
                            is_list=True,
                            interpolation=tween.bounce(1))),
            (0, tween.Tween(self.shaky_cam,
                            1,
                            0,
                            other_y - self.rect.y,
                            self.attack_length,
                            is_list=True,
                            interpolation=tween.bounce(1))),
            (self.attack_length, tween.Tween(self.anim,
                              'state',
                              0,
                              sprite.AnimState.IDLE,
                              0,
                              step=True)),
            (0, tween.Tween(self.anim,
                              'speed',
                              0,
                              0,
                              0,
                              step=True)),
        ])
        def _event(_state, event):
            anim.attach(_state)
            _state.begin_animation(anim)
            target.get_hit(state, self, damage)
            while _state.locked():
                yield True
            _state.let_entities_move()
            yield False
        state.queue_event(event_manager.Event(_event))
    
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
                sprite.AnimDir.DOWN: down,
                sprite.AnimDir.UP: up,
                sprite.AnimDir.LEFT: left,
                sprite.AnimDir.RIGHT: right,
                sprite.AnimDir.DEFAULT: down
            }
        cls.class_anim = sprite.Animation({
            sprite.AnimState.DEFAULT: standing,
            sprite.AnimState.IDLE: standing,
            sprite.AnimState.WALK: walking,
        }, 12)
        
        cls.sqr_sprite = sprite.Sprite(
            renderer.load_texture('effects.png'),
            (0, 0), (64, 64))
    