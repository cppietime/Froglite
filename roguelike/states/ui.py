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

from roguelike import (
    inputs,
    settings,
    tween
)
from roguelike.states import gamestate

"""
The render method in these classes takes a 2-tuple base_offset which
represents the offset of the
parent widget, to add to the rendering
"""

Offset = Tuple[float, float]

class Widget(Protocol):
    """Protocol class to represent widgets"""
    def selectable(self) -> bool:
        """Whether this widget can be selected when scrolling through a menu"""
        pass
    
    def render(self,
               delta_time: float,
               renderer: 'Renderer',
               base_offset: Offset) -> None:
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

@dataclass
class Label:
    """A label with an optional bg image and optional text
    A Widget"""
    bg: 'Sprite'
    # (x, y, width, height) format starting at top-left
    bg_rect: Tuple[float, float, float, float]
    bg_color: Tuple[float, float, float, float] = (1, 1, 1, 1)
    text: str = ""
    text_rect: Tuple[float, float, float, float] = ()
    font: 'CharBank' = None
    text_color: Tuple[float, float, float, float] = (1, 1, 1, 1)
    
    offset: tween.AnimatableMixin =\
        field(default_factory = tween.AnimatableMixin)
    
    def selectable(self) -> None:
        return False
    
    def render(self,
               delta_time: float,
               renderer: 'Renderer',
               base_offset: Offset) -> None:
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
            self.font.draw_str(self.text, pos, self.text_color, scale)
            
    def update(self, delta_time: float, state: gamestate.GameState):
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
               base_offset: Offset) -> None:
        pass
    
    def keydown(self, delta_time: float, state: gamestate.GameState, key: int):
        if key == pg.K_RETURN and self.command is not None:
            self.command(state)
    
    def update(self, delta_time, state):
        pass

@dataclass
class TwoLabelButton(Button):
    """A button rendered as two labels. One when active and one when inactive
    A Widget"""
    inactive: Label = None
    active: Label = None
    
    def render(self, delta_time, renderer, base_offset):
        super().render(delta_time, renderer, base_offset)
        x = base_offset[0] + self.offset.x
        y = base_offset[1] + self.offset.y
        if not self.selected or self.active is None:
            render_target = self.inactive
        else:
            render_target = self.active
        render_target.offset.w = self.offset.w
        render_target.offset.h = self.offset.h
        render_target.offset.rotation  = self.offset.rotation
        render_target.render(delta_time, renderer, (x, y))
        
@dataclass
class WidgetHolder:
    """A container of other widgets arranged vertically or horizontally
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
    
    def selectable(self):
        return any(map(lambda w: w.selectable(), self.widgets))
    
    def render(self, delta_time, renderer, base_offset):
        x = self.base_offset.x + base_offset[0]
        y = self.base_offset.y + base_offset[1]
        if self.background is not None:
            self.background.render(delta_time, renderer, (x, y))
        x += self.offset.x
        y += self.offset.y
        for widget in self.widgets:
            widget.render(delta_time, renderer, (x, y))
            if self.horizontal:
                x += self.spacing
            else:
                y += self.spacing
    
    def update(self, delta_time, state):
        if self.background is not None:
            self.background.update(delta_time, state)
        for w_no, widget in enumerate(self.widgets):
            if widget.selectable():
                widget.selected = w_no == self.selection
            widget.update(delta_time, state)
    
    def get_selected(self) -> Optional[Widget]:
        if self.selection >= len(self.widgets) or self.selection < 0:
            return None
        widget = self.widgets[self.selection]
        if not widget.selectable():
            return None
        return widget
    
    def keydown(self, delta_time, state, key):
        if state.locked():
            return
        selected = self.get_selected()
        if key == pg.K_RETURN:
            if selected is not None:
                selected.keydown(delta_time, state, key)
        k_next = pg.K_RIGHT if self.horizontal else pg.K_DOWN
        k_prev = pg.K_LEFT if self.horizontal else pg.K_UP
        inc = 0
        if key == k_next and self.selectable():
            inc = 1
        elif key == k_prev and self.selectable():
            inc = -1
        if inc != 0:
            n_sel = (self.selection + inc) % len(self.widgets)
            offset = self.offset.x if self.horizontal else self.offset.y
            orig = offset
            offset += self.spacing * self.selection
            while n_sel != self.selection:
                if self.widgets[n_sel].selectable():
                    self.selection = n_sel
                    self.widgets[n_sel].selected = True
                    break
                n_sel = (n_sel + inc) % len(self.widgets)
            offset -= self.spacing * self.selection
            if self.horizontal:
                prop = 'x'
            else:
                prop = 'y'
            tw = tween.Tween(self.offset,
                             prop,
                             orig,
                             offset,
                             settings.MENU_TRANSITION_TIME)
            anim = tween.Animation([(0, tw)])
            state.begin_animation(anim)
            anim.attach(state)

class MenuState(gamestate.GameState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widgets = WidgetHolder()
        self.offset = tween.AnimatableMixin()
    
    def render_gamestate(self,
                         delta_time: float,
                         renderer: 'Renderer') -> None:
        super().render_gamestate(delta_time, renderer)
        self.widgets.render(delta_time, renderer, (0, 0))
    
    def update_gamestate(self, delta_time: float) -> None:
        super().update_gamestate(delta_time)
        self.widgets.update(delta_time, self)
        for key, status in self.inputstate.keys.items():
            if status[inputs.KeyState.DOWN]:
                self.widgets.keydown(delta_time, self, key)
    
    def on_push(self, manager: gamestate.GameStateManager) -> None:
        super().on_push(manager)