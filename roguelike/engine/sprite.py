from dataclasses import dataclass
from enum import Enum
import math
from typing import (
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    TYPE_CHECKING
)

import moderngl as mgl # type: ignore

if TYPE_CHECKING:
    from .renderer import Renderer

class AnimState(Enum):
    DEFAULT = 0
    IDLE    = 1
    WALK    = 2
    RUN     = 3
    ATTACK  = 4
    HURT    = 5
    DIE     = 6

class AnimDir(Enum):
    DEFAULT = 0
    DOWN    = 1
    UP      = 2
    LEFT    = 3
    RIGHT   = 4

@dataclass
class Sprite:
    texture: mgl.texture.Texture
    topleft_texels: Tuple[int, int]
    size_texels: Tuple[int, int]
    color: Tuple[float, float, float, float] = (1, 1, 1, 1)
    angle: float = 0 # Rads

@dataclass
class Animation:
    sprites: Dict[AnimState, Dict[AnimDir, Sequence[Sprite]]]
    speed: float
    
    @staticmethod
    def from_atlas(atlas: mgl.texture.Texture,
                   size: Tuple[int, int],
                   offsets: Sequence[Tuple[int, int]]) -> List[Sprite]:
        return list(map(lambda offset: Sprite(atlas, offset, size), offsets))
    
@dataclass
class AnimationState:
    animation: Optional[Animation] = None
    state: AnimState = AnimState.DEFAULT
    direction: AnimDir = AnimDir.DEFAULT
    speed: float = 1
    time: float = 0
    
    def spr_list(self) -> Sequence[Sprite]:
        if self.animation is None:
            return []
        key_state = self.state
        if key_state not in self.animation.sprites:
            key_state = AnimState.DEFAULT
        dir_list = self.animation.sprites[key_state]
        key_dir = self.direction
        if key_dir not in dir_list:
            key_dir = AnimDir.DEFAULT
        return dir_list[key_dir]
    
    def render(self, renderer: 'Renderer',
               pos:     Tuple[float, float],
               size:    Tuple[float, float],
               angle: float=0,
               time_offset: float = 0) -> None:
        if self.animation is None:
            return
        key_state = self.state
        if key_state not in self.animation.sprites:
            key_state = AnimState.DEFAULT
        dir_list = self.animation.sprites[key_state]
        key_dir = self.direction
        if key_dir not in dir_list:
            key_dir = AnimDir.DEFAULT
        spr_list = self.spr_list()
        index = math.floor(self.time + time_offset) % len(spr_list)
        sprite = spr_list[index]
        renderer.render_sprite(sprite, pos, size)
    
    def increment(self, delta_time: float) -> None:
        if self.animation is None:
            return
        spr_list = self.spr_list()
        self.time = (self.time
            + delta_time * self.animation.speed * self.speed)\
            % len(spr_list)