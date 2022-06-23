import logging
from typing import (
    cast,
    ClassVar,
    Dict,
    Sequence,
    TYPE_CHECKING
)

import pygame as pg

from roguelike.engine import (
    assets,
    event_manager,
    inputs,
    sprite,
    tween
)
from roguelike.entities import entity
from roguelike.bag import (
    inventory_state,
    item,
    spells
)
from roguelike.states import game_over

if TYPE_CHECKING:
    from roguelike.engine.renderer import Renderer

class PlayerEntity(entity.FightingEntity):
    """The player"""
    name = 'Player'

    sqr_sprite: ClassVar[sprite.Sprite]
    
    def __init__(self, *args, **kwargs):
        self.class_anim = assets.Animations.instance.player
        self.sqr_sprite = assets.Sprites.instance.highlight
        super().__init__(*args,
                         passable=False,
                         max_hp=100,
                         attack=10,
                         defense=1,
                         **kwargs)
        self.anim.speed = 0
        self.anim.direction = sprite.AnimDir.DOWN
        self.shaky_cam: List[int] = [0, 0]
        self.inventory = item.Inventory(owner=self)
        self.inv_state = inventory_state.InventoryBaseScreen(
            inventory=self.inventory)
        if 'coins' not in assets.variables:
            assets.variables['coins'] = 0
        
        for name, spell in spells.items.items():
            if assets.persists.get(name, False) and self.inventory[spell] == 0:
                self.inventory.give_item(spell, 1)
        
        # DEBUGGING
        # self.inventory.give_item(item.items['Fireball'], 1)
    
    walk_length: ClassVar[float] = .25
    
    def update_entity(self, delta_time, state, _):
        super().update_entity(delta_time, state, _)
        prop = None
        shift_pressed =\
            state.inputstate.keys[pg.K_LSHIFT][inputs.KeyState.PRESSED]\
            or state.inputstate.keys[pg.K_RSHIFT][inputs.KeyState.PRESSED]
        _n_dungeon_pos = self.dungeon_pos[:]
        if state.inputstate.keys[pg.K_UP][inputs.KeyState.PRESSED]\
                or state.inputstate.keys[pg.K_w][inputs.KeyState.PRESSED]:
            diff = -state.tile_size
            _n_dungeon_pos[1] -= 1
            self.anim.direction = sprite.AnimDir.UP
            prop = 'y'
        elif state.inputstate.keys[pg.K_DOWN][inputs.KeyState.PRESSED]\
                or state.inputstate.keys[pg.K_s][inputs.KeyState.PRESSED]:
            diff = state.tile_size
            _n_dungeon_pos[1] += 1
            self.anim.direction = sprite.AnimDir.DOWN
            prop = 'y'
        elif state.inputstate.keys[pg.K_LEFT][inputs.KeyState.PRESSED]\
                or state.inputstate.keys[pg.K_a][inputs.KeyState.PRESSED]:
            diff = -state.tile_size
            _n_dungeon_pos[0] -= 1
            self.anim.direction = sprite.AnimDir.LEFT
            prop = 'x'
        elif state.inputstate.keys[pg.K_RIGHT][inputs.KeyState.PRESSED]\
                or state.inputstate.keys[pg.K_d][inputs.KeyState.PRESSED]:
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
            return
        if state.inputstate.keys[pg.K_RETURN][inputs.KeyState.DOWN]:
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
                    return
                elif target_ent.interactable:
                    target_ent.interact(state, self)
                    return
        # Open inventory
        if state.inputstate.keys[pg.K_BACKSPACE][inputs.KeyState.DOWN]:
            def _menu(state, event):
                while state.locked():
                    yield True
                state.manager.push_state(self.inv_state)
                yield False
            state.queue_event(event_manager.Event(_menu))
            return
        if state.inputstate.keys[pg.K_LCTRL][inputs.KeyState.DOWN]\
                or state.inputstate.keys[pg.K_RCTRL][inputs.KeyState.DOWN]:
            # Use magic
            spell_item = self.inventory[item.EquipmentSlot.SPELL]
            if spell_item is not None:
                spell_item.on_use(state, self)
    
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
        logging.debug('Player is dead')
        assets.Sounds.instance.ah.play()
        state.cancel_events()
        def _event(_state, event):
            while _state.locked():
                yield True
            # _state.manager.pop_state()
            _state.manager.push_state(game_over.GameOverState())
            yield False
        anim = tween.Animation([
            (0., tween.Tween(state, 'blackout', 0, 1, 1.5))
        ])
        anim.attach(state)
        state.begin_animation(anim)
        state.queue_event(event_manager.Event(_event))
    
    attack_length: ClassVar[float] = .25
    
    def melee_attack(self, state, target) -> None:
        # TODO calculate actual damage
        damage = self._melee_attack_logic(state, target)
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
            assets.Sounds.instance.pow.play()
            target.get_hit(state, self, damage)
            while _state.locked():
                yield True
            _state.let_entities_move()
            yield False
        state.queue_event(event_manager.Event(_event))
        
    def effective_attack(self):
        weapon = self.inventory[item.EquipmentSlot.WEAPON]
        atk_mul = 1
        if weapon is not None:
            atk_mul = weapon.damage_mul
        attack_stat = super().effective_attack() * atk_mul
        return max(1, int(round(attack_stat)))
        
    def effective_defense(self):
        armor = self.inventory[item.EquipmentSlot.ARMOR]
        def_mul = 1
        if armor is not None:
            def_mul = armor.def_mul
        return max(1, int(round(super().effective_defense() * def_mul)))
        
    def effective_magic(self):
        charm = self.inventory[item.EquipmentSlot.CHARM]
        pow_mul = 1
        if charm is not None:
            pow_mul = charm.pow_mul
        return max(1, int(round(super().effective_magic() * pow_mul)))
    
    