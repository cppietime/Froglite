"""
tween.py
Handles animation details
"""

from dataclasses import dataclass
import numpy as np
from typing import Sequence

from .awaiting import *

class AnimatableMixin:
    """Represents anything that has 2D position and scale and 1D rotation that can be animated"""
    def __init__(self):
        self.x, self.y, self.w, self.h, self.rotation = 0, 0, 1, 1, 0

@dataclass
class Tween:
    """A single tween action that acts on a single property of a single animatable"""
    prop: str
    start: float
    end: float
    duration: float
    elapsed: float = 0
    
    def is_active(self):
        """Returns False when this tween is over"""
        return self.elapsed < self.duration
    
    def update(self, target, delta_time):
        """Applies an animation
        target: what to apply the animation to
        delta_time: time in seconds to apply this animation for
        """
        if not self.is_active():
            return 0
        self.elapsed += delta_time
        weight = min(1.0, max(0.0, self.elapsed / self.duration))
        value = self.start + (self.end - self.start) * weight
        if target and self.prop:
            setattr(target, self.prop, value)
        return max(0, self.elapsed - self.duration)

@dataclass
class Animation(AwaitableMixin):
    """
    A sequence of Tweens to apply to an animatable target
    Each tween can have different properties but must all be on the same target
    """
    target: AnimatableMixin
    tweens: Sequence[Tween]
    index: int = 0
    
    def __post_init__(self):
        super().__init__()
    
    def update(self, delta_time):
        """Animates any active tweens and returns whether the animation is still going"""
        while delta_time > 0 and self.index < len(self.tweens):
            tween = self.tweens[self.index]
            delta_time = tween.update(self.target, delta_time)
            if not tween.is_active():
                self.index += 1
        if self.index >= len(self.tweens):
            self.conclude()
            return False
        return True

class AnimationManagerMixin:
    def __init__(self):
        super().__init__()
        self.active_anims = []
    
    def update_animations(self, delta_time):
        """Updates all aniations and removes those that are now done"""
        self.active_anims[:] = [anim for anim in self.active_anims if anim.update(delta_time)]
    
    def begin_animation(self, animation):
        """Begins a new animation. It will not update until update is called
        unless called from within another animation's update, which should never be done"""
        self.active_anims.append(animation)
    
    def animations_left(self):
        return len(self.active_anims)
