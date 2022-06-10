from typing import TYPE_CHECKING

from . import (
    awaiting,
    event_manager,
    tween
)

if TYPE_CHECKING:
    from .renderer import Renderer

class GameState(event_manager.EventManagerMixin,
                tween.AnimationManagerMixin,
                awaiting.AwaiterMixin):
    """Game state base class"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inputstate = None
        self.manager = None
        self.callbacks_on_push = []
        self.callbacks_on_pop = []
        self.callbacks_on_covered = []
        self.callbacks_on_uncovered = []
        self.callbacks_on_update = []
        self.callbacks_on_render = []
    
    def render_gamestate(self,
                         delta_time: float,
                         renderer: 'Renderer') -> None:
        self.update_animations(delta_time)
        for callback in self.callbacks_on_render:
            callback(self, delta_time, renderer)
    
    def update_gamestate(self, delta_time: float) -> bool:
        """Returns True iff this state prevents states below it from
        updating"""
        self.dispatch(self)
        for callback in self.callbacks_on_update:
            callback(self, delta_time)
        return False
    
    def on_push(self, manager: 'GameStateManager') -> None:
        """Called when a state is pushed onto the stack"""
        self.manager = manager
        self.inputstate = manager.inputstate
        for callback in self.callbacks_on_push:
            callback(self)
    
    def on_pop(self) -> None:
        """Called when a state is popped from the stack"""
        for callback in self.callbacks_on_pop:
            callback(self)
    
    def on_covered(self) -> None:
        """Called when a state is covered from a push"""
        for callback in self.callbacks_on_covered:
            callback(self)
    
    def on_uncovered(self) -> None:
        """Called when a state is uncovered from a pop"""
        for callback in self.callbacks_on_uncovered:
            callback(self)
    
    def die(self) -> None:
        """Pop self"""
        self.manager.pop_state()

class GameStateManager:
    def __init__(self, *args, **kwargs):
        self.inputstate = kwargs.pop('inputstate')
        super().__init__(*args, **kwargs)
        self.state_stack = []
    
    def render(self, delta_time: float, renderer: 'Renderer') -> None:
        for state in self.state_stack:
            state.render_gamestate(delta_time, renderer)
    
    def update(self, delta_time: float) -> None:
        if not self.inputstate.app_active:
            return
        for state in reversed(self.state_stack):
            if state.update_gamestate(delta_time):
                break
    
    def push_state(self, new_state: GameState) -> None:
        if len(self.state_stack) > 0:
            self.state_stack[-1].on_covered()
        new_state.on_push(self)
        self.state_stack.append(new_state)
    
    def pop_state(self) -> GameState:
        if len(self.state_stack) == 0:
            raise AttributeError("State stack is already empty!")
        self.state_stack[-1].on_pop()
        removed = self.state_stack.pop()
        if len(self.state_stack) > 0:
            self.state_stack[-1].on_uncovered()
        return removed
    
    def any_states_active(self) -> bool:
        return len(self.state_stack) != 0