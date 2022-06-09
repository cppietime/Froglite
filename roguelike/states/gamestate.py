from roguelike import (
    awaiting,
    event_manager,
    tween
)

class GameState(event_manager.EventManagerMixin,
                tween.AnimationManagerMixin,
                awaiting.AwaiterMixin):
    """Game state base class"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inputstate = None
        self.manager = None
    
    def render_gamestate(self,
                         delta_time: float,
                         renderer: 'Renderer') -> None:
        self.update_animations(delta_time)
        pass
    
    def update_gamestate(self, delta_time: float) -> None:
        """Returns True iff this state prevents states below it from
        updating"""
        self.dispatch(self)
        pass
    
    def on_push(self, manager: 'GameStateManager') -> None:
        """Called when a state is pushed onto the stack"""
        self.manager = manager
        self.inputstate = manager.inputstate
    
    def on_pop(self) -> None:
        """Called when a state is popped from the stack"""
        pass
    
    def on_covered(self) -> None:
        """Called when a state is covered from a push"""
        pass
    
    def on_uncovered(self) -> None:
        """Called when a state is uncovered from a pop"""
        pass

class GameStateManager:
    def __init__(self, *args, **kwargs):
        self.inputstate = kwargs.pop('inputstate')
        super().__init__(*args, **kwargs)
        self.state_stack = []
    
    def render(self, delta_time: float, renderer: 'Renderer') -> None:
        for state in self.state_stack:
            state.render_gamestate(delta_time, renderer)
    
    def update(self, delta_time: float) -> None:
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