from dataclasses import (
    dataclass,
    field
)
from enum import Enum
from typing import (
    Callable,
    ClassVar,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING
)

from roguelike.engine import (
    awaiting,
    gamestate,
    sprite,
    tween
)

if TYPE_CHECKING:
    from roguelike.engine.renderer import Renderer

@dataclass
class Entity:
    passable: bool
    dungeon_pos: List[int] = field(default_factory=lambda: [0, 0])
    rect: tween.AnimatableMixin =\
        field(init=False, default_factory=tween.AnimatableMixin)
    callbacks_on_update: List[Callable[['Entity',
                                        float,
                                        gamestate.GameState,
                                        Tuple[int, int]],
                                       None]] = field(default_factory=list)
    anim: Optional[sprite.AnimationState] = None
    lock: awaiting.AwaiterMixin = field(default_factory=awaiting.AwaiterMixin)
    
    class_anim: ClassVar[Optional[sprite.Animation]] = None
    actionable: ClassVar[bool] = False
    attackable: ClassVar[bool] = False
    base_size: ClassVar[int]
    name: ClassVar[str] = 'Entity'
    
    def __post_init__(self):
        if self.class_anim is not None:
            self.anim = sprite.AnimationState(self.class_anim)
        self.rect.w = self.rect.h = Entity.base_size
        self.rect.x = self.dungeon_pos[0] * Entity.base_size
        self.rect.y = self.dungeon_pos[1] * Entity.base_size
        self.anim.state = sprite.AnimState.IDLE
        self.anim.direction = sprite.AnimDir.DOWN
    
    def render_entity(self,
                      delta_time: float,
                      renderer: 'Renderer',
                      base_offset: Tuple[float, float]) -> None:
        """Default entity rendering technique"""
        if self.anim is not None:
            pos = (self.rect.x + base_offset[0], self.rect.y + base_offset[1])
            self.anim.render(renderer,
                             pos,
                             (self.rect.w, self.rect.h),
                             angle=self.rect.rotation)
            self.anim.increment(delta_time)
    
    def update_entity(self,
                      delta_time: float,
                      state: gamestate.GameState,
                      player_pos: Tuple[int, int]) -> None:
        for callback in self.callbacks_on_update:
            callback(self, delta_time, state, player_pos)

class ActingEntity(Entity):
    """Entities that take actions between turns
    """
    actionable = True
    name = 'Actor'
    
    detection_radius: ClassVar[int] = -1
    
    def __init__(self, *args, **kwargs):
        self.action_cost: float = kwargs.pop('action_cost')
        self.max_hp: int = kwargs.pop('max_hp')
        self.hp = self.max_hp
        self.energy = 0.
        super().__init__(*args, **kwargs)
    
    def expend_energy(self,
                      state: gamestate.GameState,
                      player_pos: Tuple[int, int]) -> None:
        while self.energy >= self.action_cost:
            self.energy -= self.action_cost
            self.take_action(state, player_pos)
    
    def give_energy(self, energy: float) -> None:
        self.energy += energy
    
    def take_action(self,
                    state: gamestate.GameState,
                    player_pos: Tuple[int, int]) -> None:
        pass

class EnemyEntity(ActingEntity):
    """Base class for enemies
    """
    attackable = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
