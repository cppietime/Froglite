from dataclasses import (
    dataclass,
    field
)
from enum import Enum
from typing import (
    cast,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    TYPE_CHECKING
)

import pygame as pg

from roguelike.engine import (
    assets,
    awaiting,
    event_manager,
    gamestate,
    sprite,
    text,
    tween
)
from roguelike.entities import (
    spawn
)

if TYPE_CHECKING:
    from roguelike.engine.renderer import Renderer
    from roguelike.world.dungeon import DungeonMapState

entities: Dict[str, Type['Entity']] = {}
Pos = Tuple[int, int]

@dataclass
class Entity:
    """Anything on the screen with state
    Subclasses have some class variables to control behavior
    
    ClassVars:
    class_anim: default animation for rendering instances
    actionable: True if these entities take actions after the player
    attackable: Can the player  attack it?
    interactable: Can the player speak to/interact with it?
    base_size: Size in pixels of an entity
    name: For debuggin at least for now
    pain_particle_y: Height above the entity for damage indicator
    pain_particle_h: Size of the damage indicator
    pain_particle_v: How far up the damage indicator moves before
        disappearing
    
    The player moves/takes actions in the update_entity function when
    the state is unlocked. If the player takes an action, it queues an
    event that lets other actionable entities take their actions as well
    """
    passable: bool
    dungeon_pos: List[int] = field(default_factory=lambda: [0, 0])
    rect: tween.AnimatableMixin =\
        field(init=False, default_factory=tween.AnimatableMixin)
    callbacks_on_update: List[Callable[['Entity',
                                        float,
                                        gamestate.GameState,
                                        Pos],
                                       None]] = field(default_factory=list)
    anim: Optional[sprite.AnimationState] = None
    lock: awaiting.AwaiterMixin = field(default_factory=awaiting.AwaiterMixin)
    
    class_anim: ClassVar[Union[sprite.Animation, sprite.Sprite, None]] = None
    actionable: ClassVar[bool] = False
    attackable: ClassVar[bool] = False
    interactable: ClassVar[bool] = False
    base_size: ClassVar[int] = 1
    name: ClassVar[str] = 'Entity'
    particle_backdrop: ClassVar[Optional[sprite.Animation]] = None
    death_sound: ClassVar[Optional[pg.mixer.Sound]] = None
    
    def __post_init__(self):
        if isinstance(self.class_anim, sprite.Animation):
            self.anim = sprite.AnimationState(self.class_anim)
            self.anim.state = sprite.AnimState.IDLE
            self.anim.direction = sprite.AnimDir.DOWN
        self.rect.w = self.rect.h = self.base_size
        self.rect.x = self.dungeon_pos[0] * self.base_size
        self.rect.y = self.dungeon_pos[1] * self.base_size
    
    def be_at(self, dpos: Pos) -> None:
        self.dungeon_pos = list(dpos)
        self.rect.w = self.rect.h = self.base_size
        self.rect.x = self.dungeon_pos[0] * self.base_size
        self.rect.y = self.dungeon_pos[1] * self.base_size
    
    def render_entity(self,
                      delta_time: float,
                      renderer: 'Renderer',
                      base_offset: Tuple[float, float]) -> None:
        """Default entity rendering technique"""
        pos = (self.rect.x + base_offset[0], self.rect.y + base_offset[1])
        size = (self.rect.w, self.rect.h)
        if self.anim is not None:
            self.anim.render(renderer,
                             pos,
                             (self.rect.w, self.rect.h),
                             angle=self.rect.rotation)
            self.anim.increment(delta_time)
        elif isinstance(self.class_anim, sprite.Sprite):
            renderer.render_sprite(self.class_anim, pos, size)
    
    def render_entity_post(self,
                      delta_time: float,
                      renderer: 'Renderer',
                      base_offset: Tuple[float, float]) -> None:
        """For UI/effects that need to not be obscured by other entities"""
        pass
    
    def update_entity(self,
                      delta_time: float,
                      state: gamestate.GameState,
                      player_pos: Pos) -> None:
        for callback in self.callbacks_on_update:
            callback(self, delta_time, state, player_pos)
    
    def animate_then(self,
                     state: gamestate.GameState,
                     tweens: List[Tuple[float, tween.Tween]],
                     duration: float,
                     state_at_end: Optional[sprite.AnimState] = None,
                     speed_at_end: Optional[float] = None,
                     reset_time_to: Optional[float] = None,
                     blocking: bool = True) -> None:
        """Helper function to start an animation and reset state afterwards"""
        if self.anim is not None:
            if state_at_end is not None:
                tweens.append((duration, tween.Tween(self.anim,
                                                     'state',
                                                     0,
                                                     state_at_end,
                                                     0,
                                                     step=True)))
                duration = 0
            if speed_at_end is not None:
                tweens.append((duration, tween.Tween(self.anim,
                                                     'speed',
                                                     0,
                                                     speed_at_end,
                                                     0,
                                                     step=True)))
                duration = 0
            if reset_time_to is not None:
                tweens.append((duration, tween.Tween(self.anim,
                                                     'time',
                                                     0,
                                                     reset_time_to,
                                                     0,
                                                     step=True)))
                duration = 0
        anim = tween.Animation(tweens)
        if blocking:
            anim.attach(state)
        state.begin_animation(anim)
        
    
    def animate_stepping_to(self,
                            state: gamestate.GameState,
                            new_pos: Tuple[float, float],
                            duration: float,
                            state_at_end: Optional[sprite.AnimState] = None,
                            speed_at_end: Optional[float] = None,
                            reset_time_to: Optional[float] = None,
                            blocking: bool = True,
                            interpolation: Callable[[float], float]=\
                                tween.smoothstep) -> None:
        """Starts an animation on an entity to move to another point with
        some interpolation function
        """
        tweens = [
            (0., tween.Tween(self.rect,
                            'x',
                            self.rect.x,
                            new_pos[0],
                            duration,
                            interpolation=interpolation)),
            (0., tween.Tween(self.rect,
                            'y',
                            self.rect.y,
                            new_pos[1],
                            duration,
                            interpolation=interpolation))
        ]
        self.animate_then(state,
                          tweens,
                          duration,
                          state_at_end,
                          speed_at_end,
                          reset_time_to,
                          blocking)
    
    pain_particle_y: ClassVar[float] = 1 / 4
    pain_particle_w: ClassVar[float] = 18
    pain_particle_h: ClassVar[float] = 1 / 2
    pain_particle_v: ClassVar[float] = 75
        
    def pain_particle(self,
                      state: gamestate.GameState,
                      msg: str,
                      color: Tuple[float, float, float, float]\
                          =(1, 0, 0, 1)):
        state = cast('DungeonMapState', state)
        width = (2 + len(msg)) * self.pain_particle_w
        p_rect = tween.AnimatableMixin(self.rect.x + (self.rect.h - width) / 2,
                                       self.rect.y - self.rect.h\
                                           * self.pain_particle_y,
                                       width,
                                       self.rect.h * self.pain_particle_h)
        state.spawn_particle(
            p_rect,
            tween.Animation([
                (0, tween.Tween(
                    p_rect, 'y', p_rect.y, p_rect.y - self.pain_particle_v, 1))
            ]),
            msg,
            color,
            self.particle_backdrop)
    
    def entity_die(self,
                   state: gamestate.GameState,
                   killer: Optional['FightingEntity']=None) -> None:
        """Calls when something needs to die or be removed"""
        if self.death_sound is not None:
            self.death_sound.play()
        state = cast('DungeonMapState', state)
        state.dungeon_map.remove_entity(self)

class FightingEntity(Entity):
    """Entities that can take and deal damage and die
    
    Arguments:
    max_hp: Default starting HP
    
    ClassVars:
    attack_length: Duration of the attack melee animation
    """
    melee_sound: ClassVar[Optional[pg.mixer.Sound]] = None
    def __init__(self, *args, **kwargs):
        self.max_hp: int = kwargs.pop('max_hp')
        self.hp = self.max_hp
        self.attack_stat: float = kwargs.pop('attack', 1.)
        self.defense_stat: float = kwargs.pop('defense', 1.)
        super().__init__(*args, **kwargs)
        
        # DEBUG
        self.death_sound = assets.Sounds.instance.ah
    
    def get_hit(self,
                state: gamestate.GameState,
                attacker: Optional['FightingEntity'],
                damage: int) -> bool:
        """Returns whether self is still alive after taking the hit"""
        self.hp -= damage
        if self.hp <= 0:
            self.entity_die(state, attacker)
            return False
        return True
    
    def _melee_attack_logic(self,
                      state: gamestate.GameState,
                      target: 'FightingEntity') -> int:
        """Internal helper function for melee attacks that does not handle
        animations
        """
        atk = self.effective_attack()
        dfn = target.effective_defense()
        return max(1, int(round(atk / dfn)))
    
    def _spell_attack_logic(self,
                            magic: float,
                            state: gamestate.GameState,
                            target: 'FightingEntity') -> int:
        atk = magic * self.effective_magic()
        dfn = target.effective_defense()
        return max(1, int(round(atk / dfn)))
    
    attack_length: ClassVar[float] = .25
    
    def melee_attack(self,
                      state: gamestate.GameState,
                      target: 'FightingEntity') -> None:
        """Base case function to attack directly via melee"""
        damage = self._melee_attack_logic(state, target)
        state = cast('DungeonMapState', state)
        self._melee_attack_logic(state, target)
        my_anim = self.anim
        if my_anim is not None:
            my_anim.state = sprite.AnimState.ATTACK
        other_x = target.dungeon_pos[0] * state.tile_size
        other_y = target.dungeon_pos[1] * state.tile_size
        def _script(_state, event):
            while _state.locked():
                yield True
            self.animate_stepping_to(state,
                                     (other_x, other_y),
                                     self.attack_length,
                                     sprite.AnimState.IDLE,
                                     0,
                                     interpolation=tween.bounce(1))
            if self.melee_sound is not None:
                self.melee_sound.play()
            while state.locked():
                yield True
            target.get_hit(_state, self, damage)
            yield not _state.locked()
        state.queue_event(event_manager.Event(_script))
    
    def effective_attack(self) -> float:
        return self.attack_stat
    
    def effective_defense(self) -> float:
        return self.defense_stat
    
    def effective_magic(self) -> float:
        return 1
    
class ActingEntity(FightingEntity):
    """Entities that take actions between turns
    
    Arguments:
    action_cost: How much energy it takes to perform one action
    
    ClassVars:
    detection_radius: How far can it be from the player and still act
    hit_bounces: How many times to shiver when struck
    hit_size: How far to shiver
    hit_length: For how long to shiver
    """
    actionable = True
    name = 'Actor'
    
    detection_radius: ClassVar[int] = -1
    
    def __init__(self, *args, **kwargs):
        self.action_cost: float = kwargs.pop('action_cost')
        self.energy = 0.
        super().__init__(*args, **kwargs)
    
    def expend_energy(self,
                      state: gamestate.GameState,
                      player_pos: Pos) -> None:
        while self.energy >= self.action_cost:
            self.energy -= self.action_cost
            self.take_action(state, player_pos)
    
    def give_energy(self, energy: float) -> None:
        self.energy += energy
    
    def waste_energy(self) -> None:
        self.energy %= self.action_cost
    
    def take_action(self,
                    state: gamestate.GameState,
                    player_pos: Pos) -> None:
        pass
    
    hit_bounces: ClassVar[float] = 2.
    hit_length: ClassVar[float] = .25
    hit_size: ClassVar[float] = .1
    
    def get_hit(self,
                state: gamestate.GameState,
                attacker: Optional['FightingEntity'],
                damage: int) -> bool:
        state = cast('DungeonMapState', state)
        self.pain_particle(state, f'-{damage}')
        if super().get_hit(state, attacker, damage):
            offset = self.rect.w * self.hit_size
            move_to = (self.rect.x + offset, self.rect.y)
            self.animate_stepping_to(state,
                                     move_to,
                                     self.hit_length,
                                     state_at_end=sprite.AnimState.IDLE,
                                     speed_at_end=0,
                                     interpolation=\
                                        tween.shake(self.hit_bounces))
            return True
        return False

class EnemyEntity(ActingEntity):
    """Base class for enemies
    
    ClassVars:
    hp_font: Font to render HP indicators
    hp_bar_y: Height of HP indicator above entity
    hp_bar_h: Size of HP indicator (height)
    hp_bar_color: Color of HP indicator text
    """
    attackable = True
    
    hp_font: ClassVar[text.CharBank]
    
    def __init__(self, *args, **kwargs):
        self.gold_drop = cast(int, kwargs.pop('gold', 0))
        drop_dict = kwargs.pop('drops', [])
        self.drops = spawn.parse_spawns(drop_dict)
        atk_mul = cast(float, kwargs.pop('atk_mul', 0.))
        def_mul = cast(float, kwargs.pop('def_mul', 0.))
        super().__init__(*args, **kwargs)
        difficulty: int = assets.variables['difficulty']
        self.attack_stat *= 1 + atk_mul * difficulty
        self.defense_stat *= 1 + def_mul * difficulty
    
    step_len_s: ClassVar[float] = .25
    
    def chase_player(self,
                     state: gamestate.GameState,
                     player_pos: Pos,
                     chase_radius: int) -> bool:
        state = cast('DungeonMapState', state)
        my_anim = self.anim
        path = state.dungeon_map.a_star(cast(Pos, tuple(self.dungeon_pos)),
                                        player_pos,
                                        chase_radius)
        if path is None:
            # Player cannot be reached, just sit still
            return False
        if len(path) < 3:
            # Player is within one square
            self.melee_attack(state, state.dungeon_map.player)
            return True
        next_step = path[1]
        # Animations and motion
        anim_state = sprite.AnimState.WALK
        prop = None
        if next_step[0] < self.dungeon_pos[0]:
            anim_dir = sprite.AnimDir.LEFT
            prop = 'x'
        elif next_step[0] > self.dungeon_pos[0]:
            anim_dir = sprite.AnimDir.RIGHT
            prop = 'x'
        elif next_step[1] < self.dungeon_pos[1]:
            anim_dir = sprite.AnimDir.UP
            prop = 'y'
        elif next_step[1] > self.dungeon_pos[1]:
            anim_dir = sprite.AnimDir.DOWN
            prop = 'y'
        if my_anim is not None:
            my_anim.state = anim_state
            my_anim.direction = anim_dir
        if prop is not None\
                and state.dungeon_map.move_entity(
                    cast(Pos, tuple(self.dungeon_pos)),
                    next_step):
            if my_anim is not None:
                my_anim.speed = 1
            self.animate_stepping_to(state,
                                     (self.dungeon_pos[0] * state.tile_size,
                                      self.dungeon_pos[1] * state.tile_size),
                                     self.step_len_s,
                                     sprite.AnimState.IDLE,
                                     0)
            return True
        return False
    
    hp_bar_y: ClassVar[float] = 1 / 2
    hp_bar_h: ClassVar[float] = 1 / 2
    hp_bar_color: ClassVar[Tuple[float, float, float, float]] = (1, 0, 0, 1)
    
    def render_entity_post(self, delta_time, renderer, base_offset):
        super().render_entity_post(delta_time, renderer, base_offset)
        pos = (self.rect.x + base_offset[0],
            self.rect.y + base_offset[1] - self.rect.h * self.hp_bar_y)
        self.hp_font.draw_str_in(f"{self.hp}",
                                        pos,
                                        (self.rect.w,
                                         self.rect.h * self.hp_bar_h),
                                        self.hp_bar_color)
    
    def entity_die(self, state, killer):
        super().entity_die(state, killer)
        if self.gold_drop > 0:
            assets.variables['coins'] += self.gold_drop
            self.pain_particle(state, f'+{self.gold_drop}', (1, 1, 0, 1))
        child = self.drops.populate(tuple(self.dungeon_pos))
        if child is not None:
            ent = child[1](**child[2])
            ent.be_at(self.dungeon_pos)
            state.dungeon_map.place_entity(ent)

