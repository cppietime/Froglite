from dataclasses import dataclass
from typing import (
    Optional,
    Tuple,
    TYPE_CHECKING
)

from roguelike.engine import (
    text,
    sprite,
    tween
)

if TYPE_CHECKING:
    from roguelike.engine.renderer import Renderer

@dataclass
class DungeonParticle:
    rect: tween.AnimatableMixin
    motion: tween.Animation
    animstate: Optional[sprite.AnimationState] = None
    msg: Optional[str] = None
    text_color: Tuple[float, float, float, float] = (0, 0, 0, 0)
    font: Optional[text.CharBank] = None
    
    def render_particle(self,
                        delta_time: float,
                        renderer: 'Renderer',
                        offset: Tuple[float, float]) -> bool:
        active = self.motion.update(delta_time)
        pos = (self.rect.x + offset[0], self.rect.y + offset[1])
        if self.animstate is not None:
            self.animstate.render(renderer,
                                  pos,
                                  (self.rect.w, self.rect.h))
            self.animstate.increment(delta_time)
        if self.msg:
            assert self.font is not None
            self.font.draw_str_in(self.msg,
                                  pos,
                                  (self.rect.w, self.rect.h),
                                  self.text_color,
                                  alignment=text.CENTER_CENTER)
        return active