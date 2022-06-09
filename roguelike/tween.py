"""
tween.py
Handles animation details
"""

from dataclasses import (
    dataclass,
    field
)
from typing import (
    List,
    Sequence,
    Tuple
)

import numpy as np

from roguelike.awaiting import *

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

@dataclass
class Tween:
    """A single tween action that acts on a single property of a single
    animatable"""
    target: AnimatableMixin
    prop: str
    start: float
    end: float
    duration: float
    elapsed: float = 0
    
    def is_active(self) -> bool:
        """Returns False when this tween is over"""
        return self.elapsed < self.duration
    
    def update(self, delta_time: float) -> None:
        """Applies an animation
        delta_time: time in seconds to apply this animation for
        """
        if not self.is_active():
            return 0
        self.elapsed += delta_time
        weight = min(1.0, max(0.0, self.elapsed / self.duration))
        value = self.start + (self.end - self.start) * weight
        if self.target and self.prop:
            setattr(self.target, self.prop, value)
        return max(0, self.elapsed - self.duration)

@dataclass
class Animation(AwaitableMixin):
    """
    A sequence of Tweens to apply to an animatable target
    Each tween can have different properties and targets
    Tweens need not be purely sequential. If one has a delta time less than
    the previous' duration, they will coincide
    """
    # target: AnimatableMixin
    tweens: Sequence[Tuple[float, Tween]]
    index: int = 0
    active_tweens: List[Tween] = field(default_factory=list)
    elapsed: float = 0
    accum: float = 0
    
    def __post_init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def update(self, delta_time: float) -> None:
        """Animates any active tweens and returns whether the animation is
        still going"""
        self.active_tweens[:] = [tween for tween in self.active_tweens if
                                 tween.update(delta_time) == 0]
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
