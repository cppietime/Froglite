from dataclasses import (
    dataclass,
    field
)
from typing import (
    Callable,
    ClassVar,
    List,
    Optional,
    Protocol,
    Tuple
)

import pygame as pg

from roguelike.engine import (
    gamestate,
    inputs,
    sprite,
    tween
)

Rect = List[float]

"""
The render method in these classes takes a 2-tuple base_offset which
represents the offset of the
parent widget, to add to the rendering
"""

Offset = List[float]

class Widget(Protocol):
    """Protocol class to represent widgets"""
    def selectable(self) -> bool:
        """Whether this widget can be selected when scrolling through a menu"""
        pass
    
    def render(self,
               delta_time: float,
               renderer: 'Renderer',
               base_offset: Offset,
               selected: bool) -> None:
        """Render the widget to the renderer at base_offset provided by parent widget"""
        pass
    
    def update(self, delta_time: float, state: gamestate.GameState) -> None:
        """Perform the update function"""
    
    def keydown(self,
                delta_time: float,
                state: gamestate.GameState,
                key: int) -> None:
        """What happens when a key is pressed while this is selected?"""
        pass
    
    def validate(self) -> None:
        """Make sure selection is valid"""
        pass

@dataclass
class Label:
    """A label with an optional bg image and optional text
    A Widget"""
    bg: 'Sprite'
    # (x, y, width, height) format starting at top-left
    bg_rect: Rect
    bg_color: Rect = field(default_factory=lambda: [1, 1, 1, 1])
    text: str = ""
    text_rect: Optional[Rect] = None
    font: Optional['CharBank'] = None
    text_color: Rect = field(default_factory=lambda: [1, 1, 1, 1])
    
    offset: tween.AnimatableMixin =\
        field(default_factory = tween.AnimatableMixin)
    
    def selectable(self) -> None:
        return False
    
    def render(self,
               delta_time: float,
               renderer: 'Renderer',
               base_offset: Offset,
               _: bool) -> None:
        if self.bg:
            pos = (self.bg_rect[0] + self.offset.x + base_offset[0],
                   self.bg_rect[1] + self.offset.y + base_offset[1])
            size = (self.bg_rect[2] + self.offset.w,
                    self.bg_rect[3] + self.offset.h)
            renderer.render_sprite(self.bg,
                                   pos,
                                   size,
                                   color=self.bg_color,
                                   angle=self.offset.rotation)
        if self.text and self.text_rect:
            pos = (self.text_rect[0] + self.offset.x + base_offset[0],
                   self.text_rect[1] + self.offset.y + base_offset[1])
            size = (self.text_rect[2] + self.offset.w,
                    self.text_rect[3] + self.offset.h)
            scale = self.font.scale_to_bound(self.text, size)
            scale = scale, scale
            self.font.draw_str(self.text, pos, tuple(self.text_color), scale)
            
    def update(self, delta_time: float, state: gamestate.GameState):
        pass
    
    def validate(self):
        pass

@dataclass
class Button:
    """Base class of anything that can be rendered and clicked
    A Widget"""
    selected: bool = field(init=False, default=False)
    
    command: Callable = None
    
    offset: tween.AnimatableMixin =\
        field(default_factory = tween.AnimatableMixin)
    
    def selectable(self) -> bool:
        return True
    
    def render(self,
               delta_time: float,
               renderer: 'Renderer',
               base_offset: Offset,
               selected: bool) -> None:
        pass
    
    def keydown(self, delta_time: float, state: gamestate.GameState, key: int):
        if key == pg.K_RETURN and self.command is not None:
            self.command(state)
    
    def update(self, delta_time, state):
        pass
    
    def validate(self):
        pass

@dataclass
class TwoLabelButton(Button):
    """A button rendered as two labels. One when active and one when inactive
    A Widget"""
    inactive: Label = None
    active: Label = None
    
    def render(self, delta_time, renderer, base_offset, selected):
        super().render(delta_time, renderer, base_offset, selected)
        x = base_offset[0] + self.offset.x
        y = base_offset[1] + self.offset.y
        if not selected or self.active is None:
            render_target = self.inactive
        else:
            render_target = self.active
        render_target.offset.w = self.offset.w
        render_target.offset.h = self.offset.h
        render_target.offset.rotation  = self.offset.rotation
        render_target.render(delta_time, renderer, (x, y), selected)
        
@dataclass
class WidgetHolder:
    """A container of other widgets arranged vertically or horizontally
    When there are selectable elements, you can scroll through them
    It will cycle if buffer_display > 0
    A Widget"""
    background: Widget = None
    widgets: List = field(default_factory=list)
    selection: int = 0
    base_offset: tween.AnimatableMixin =\
        field(default_factory=tween.AnimatableMixin)
    offset: tween.AnimatableMixin =\
        field(default_factory=tween.AnimatableMixin)
    selected: bool = False
    horizontal: bool = False
    spacing: float = 0
    buffer_display: int = 1
    zero_point: float = 0
    scroll_time: float = 0.2
    
    def selectable(self):
        return any(map(lambda w: w.selectable(), self.widgets))
    
    def render(self, delta_time, renderer, base_offset, selected):
        x = self.base_offset.x + base_offset[0]
        y = self.base_offset.y + base_offset[1]
        if self.background is not None:
            self.background.render(delta_time, renderer, (x, y), False)
        x += self.offset.x
        y += self.offset.y
        if self.horizontal:
            x -= self.spacing * (len(self.widgets) * self.buffer_display - self.zero_point)
        else:
            y -= self.spacing * (len(self.widgets) * self.buffer_display - self.zero_point)
        # Render surrounding instances if any to cycle around
        for _ in range(-self.buffer_display, self.buffer_display + 1):
            for w_no, widget in enumerate(self.widgets):
                w_sel = selected and w_no == self.selection
                widget.render(delta_time, renderer, (x, y), w_sel)
                if self.horizontal:
                    x += self.spacing
                else:
                    y += self.spacing
    
    def update(self, delta_time, state):
        if self.background is not None:
            self.background.update(delta_time, state)
        for w_no, widget in enumerate(self.widgets):
            # Update selection status
            if widget.selectable():
                widget.selected = w_no == self.selection
            # Propagate update
            widget.update(delta_time, state)
    
    def _get_selected(self) -> Optional[Widget]:
        """Helper function to get selected Widget, or None"""
        if self.selection >= len(self.widgets) or self.selection < 0:
            return None
        widget = self.widgets[self.selection]
        if not widget.selectable():
            return None
        return widget
    
    def _cycle_display(self,
                       state: gamestate.GameState,
                       direction: int) -> bool:
        """Helper function to cycle the window display on selection change"""
        o_sel = self.selection
        n_sel = (self.selection + direction) % len(self.widgets)
        offset = self.offset.x if self.horizontal else self.offset.y
        orig = offset
        base = orig + o_sel * self.spacing
        offset -= self.spacing * direction
        while n_sel != self.selection:
            if self.widgets[n_sel].selectable():
                self.selection = n_sel
                self.widgets[self.selection].selected = True
                break
            n_sel = (n_sel + direction) % len(self.widgets)
            offset -= direction * self.spacing
        if n_sel != o_sel:
            if self.horizontal:
                prop = 'x'
            else:
                prop = 'y'
            tweens = []
            if self.selection == len(self.widgets) - 1 and direction == -1:
                tw = tween.Tween(self.offset,
                                 prop,
                                 orig,
                                 orig - self.spacing * len(self.widgets),
                                 0)
                tweens.append((0, tw))
                orig -= self.spacing * len(self.widgets)
                offset -= self.spacing * len(self.widgets)
            tw = tween.Tween(self.offset,
                             prop,
                             orig,
                             offset,
                             self.scroll_time)
            tweens.append((0, tw))
            if self.selection == 0 and direction == 1:
                tw = tween.Tween(self.offset,
                                 prop,
                                 offset,
                                 base,
                                 0)
                tweens.append((self.scroll_time, tw))
            anim = tween.Animation(tweens)
            state.begin_animation(anim)
            anim.attach(state)
            return True
        return False
    
    def keydown(self, delta_time, state, key):
        # Ignore input if we are in an event
        if state.locked():
            return
        
        # Cache the selected widget for later
        selected = self._get_selected()
        
        # Propagate activation if relevant
        if key == pg.K_RETURN:
            if selected is not None:
                selected.keydown(delta_time, state, key)
                return
        
        # Handle navigation if we can
        k_next = pg.K_RIGHT if self.horizontal else pg.K_DOWN
        k_prev = pg.K_LEFT if self.horizontal else pg.K_UP
        # Which direction to travel in
        inc = 0
        if key == k_next and self.selectable():
            inc = 1
        elif key == k_prev and self.selectable():
            inc = -1
        if inc != 0:
            if self._cycle_display(state, inc):
                return
        
        # Any other checks will go here
        
        # Propagate down if we haven't returned
        if selected is not None:
            selected.keydown(delta_time, state, key)
    
    def validate(self):
        for widget in self.widgets:
            widget.validate()
        for i in range(len(self.widgets)):
            n_sel = (self.selection + i) % len(self.widgets)
            if self.widgets[n_sel].selectable():
                self.selection = n_sel
                break
        
@dataclass
class MetaWidget:
    # Bounding rect MUST NOT BE NONE if mask_sprite is used
    widget: Widget
    bounding_rect: Optional[tween.AnimatableMixin] = None # Rectangular cutoff
    mask_sprite: Optional[sprite.Sprite] = None # Alpha mask sprite
    
    def selectable(self):
        return self.widget.selectable()
    
    def update(self, delta_time, state):
        self.widget.update(delta_time, state)
    
    def keydown(self, delta_time, state, key):
        self.widget.keydown(delta_time, state, key)
    
    def render(self, delta_time, renderer, base_offset, selected):
        # Get the base offset accounting for the rect
        x, y = base_offset
        if self.bounding_rect is not None:
            x += self.bounding_rect.x
            y += self.bounding_rect.y
            # If we need to clear and render on our own, push a new FBO
            old_fbo = renderer.current_fbo()
            new_fbo = renderer.push_fbo()
            renderer.clear()
        
        self.widget.render(delta_time, renderer, base_offset, selected)
        if self.bounding_rect is not None:
            size = (self.bounding_rect.w, self.bounding_rect.h)
            if self.mask_sprite is None:
                base_tex = new_fbo.color_attachments[0]
                cutoff_sprite = sprite.Sprite(base_tex,
                                              (x, y),
                                              size)
                renderer.pop_fbo()
                old_fbo.use()
                renderer.render_sprite(cutoff_sprite,
                                       (x, y),
                                       size)
            else:
                renderer.fbos['vignette'].use()
                renderer.clear()
                renderer.render_sprite(self.mask_sprite,
                                       (x, y),
                                       size)
                new_fbo.use()
                renderer.apply_vignette(old_fbo,
                                        renderer.fbos['vignette']\
                                            .color_attachments[0])
                renderer.pop_fbo()
                old_fbo.use()
    
    def validate(self):
        self.widget.validate()
            

class MenuState(gamestate.GameState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget = MetaWidget(WidgetHolder())
        self.offset = tween.AnimatableMixin()
    
    def render_gamestate(self,
                         delta_time: float,
                         renderer: 'Renderer') -> None:
        super().render_gamestate(delta_time, renderer)
        self.widget.render(delta_time, renderer, (0, 0), True)
    
    def update_gamestate(self, delta_time: float) -> None:
        super().update_gamestate(delta_time)
        self.widget.update(delta_time, self)
        for key, status in self.inputstate.keys.items():
            if status[inputs.KeyState.DOWN]:
                self.widget.keydown(delta_time, self, key)
        return True
    
    def on_push(self, manager: gamestate.GameStateManager) -> None:
        super().on_push(manager)
        self.widget.validate()