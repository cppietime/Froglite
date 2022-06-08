from . import (
    event_manager,
    tween
)

class GameState(event_manager.EventManagerMixin, tween.AnimationManagerMixin):
    """Game state base class"""
    def __init__(self, inputstate):
        super().__init__()
        self.inputstate = inputstate
    
    def render_gamestate(self, delta_time, renderer):
        pass
    
    def update_gamestate(self, delta_time):
        """Returns True iff this state prevents states below it from updating"""
        pass

class GameStateManager:
    def __init__(self):
        super().__init__()
        self.state_stack = []
    
    def render(self, delta_time, renderer):
        for state in self.state_stack:
            state.render(delta_time, renderer)
    
    def update(self, delta_time):
        for state in reversed(self.state_stack):
            if state.update(delta_time):
                break