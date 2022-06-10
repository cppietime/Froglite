"""
tween.py
Handles animation details
"""

from dataclasses import (
    dataclass,
    field
)
import math
from typing import (
    cast,
    Any,
    Callable,
    List,
    Sequence,
    Tuple,
    Union,
    TYPE_CHECKING
)

import numpy as np

from .awaiting import *

if TYPE_CHECKING:
    pass

class AnimatableMixin:
    """Represents anything that has 2D position and scale and 1D rotation that
    can be animated"""
    def __init__(self,
                 x:float=0,
                 y:float=0,
                 w:float=1,
                 h:float=1,
                 rotation:float=0):
        self.x, self.y, self.w, self.h, self.rotation = x, y, w, h, rotation

def linear(x: float) -> float:
    return x

def smoothstep(x: float) -> float:
    x2 = x * x
    return 3 * x2 - 2 * x2 * x

def shake(cycles: float) -> Callable[[float], float]:
    def _fn(x: float) -> float:
        return math.sin(x * math.pi * 2 * cycles)
    return _fn

def bounce(bounces: float, power: float = 1) -> Callable[[float], float]:
    def _fn(x: float) -> float:
        return 1 - abs(math.cos(x * math.pi * bounces)) ** power
    return _fn

@dataclass
class Tween:
    """A single tween action that acts on a single property of a single
    animatable"""
    target: Any
    prop: Union[int, str]
    start: float
    end: Any
    duration: float
    elapsed: float = 0
    is_list: bool = False
    step: bool = False
    interpolation: Callable[[float], float] = linear
    
    def __post_init__(self):
        assert self.step or type(self.end) in (int, float)
    
    def is_active(self) -> bool:
        """Returns False when this tween is over"""
        return self.elapsed < self.duration
    
    def set_to(self, value: float) -> None:
        if self.is_list:
            cast(list, self.target)[cast(int, self.prop)] = value
        else:
            setattr(self.target, cast(str, self.prop), value)
    
    def update(self, delta_time: float) -> bool:
        """Applies an animation
        delta_time: time in seconds to apply this animation for
        returns True iff the animation is ongoing
        """
        self.elapsed += delta_time
        # if (self.duration == 0 and self.target and self.prop)\
                # or self.elapsed >= self.duration:
        # if self.duration == 0 or self.elapsed >= self.duration:
            # if self.target and self.prop:
                # # Check specifically for 0 duration case
                # self.set_to(self.end)
            # return False
        # if not self.step:
        if self.step:
            if (self.elapsed >= self.duration or self.duration == 0)\
                    and self.target and self.prop:
                self.set_to(self.end)
        else:
            if self.duration == 0:
                weight = 1.
            else:
                weight = min(1.0, max(0.0, self.elapsed / self.duration))
            weight = self.interpolation(weight)
            value = self.start + (self.end - self.start) * weight
            if self.target is not None and self.prop is not None:
                self.set_to(value)
        return self.elapsed < self.duration #True

@dataclass
class Animation(AwaitableMixin):
    """
    A sequence of Tweens to apply to an animatable target
    Each tween can have different properties and targets
    Tweens need not be purely sequential. If one has a delta time less than
    the previous' duration, they will coincide
    """
    tweens: Sequence[Tuple[float, Tween]]
    index: int = 0
    active_tweens: List[Tween] = field(default_factory=list)
    elapsed: float = 0
    accum: float = 0
    
    def __post_init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def update(self, delta_time: float) -> bool:
        """Animates any active tweens and returns whether the animation is
        still going"""
        self.active_tweens[:] = [tween for tween in self.active_tweens if
                                 tween.update(delta_time)]
        self.elapsed += delta_time
        while self.index < len(self.tweens):
            start_time, tween = self.tweens[self.index]
            if self.elapsed >= start_time + self.accum:
                self.accum += start_time
                tween.update(self.elapsed - self.accum)
                self.active_tweens.append(tween)
                self.index += 1
            else:
                break
        if len(self.active_tweens) == 0:
            self.conclude()
            return False
        return True

class AnimationManagerMixin:
    """Mixin-style class to process animations"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_anims = []
    
    def update_animations(self, delta_time: float) -> None:
        """Updates all aniations and removes those that are now done"""
        self.active_anims[:] = [anim for anim in self.active_anims if
                                anim.update(delta_time)]
    
    def begin_animation(self, animation: Animation) -> None:
        """Begins a new animation. It will not update until update is called
        unless called from within another animation's update, which should
        never be done"""
        self.active_anims.append(animation)
    
    def animations_left(self) -> int:
        return len(self.active_anims)
