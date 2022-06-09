from roguelike.engine import event_manager

def _wait(state, event):
    print("Waiting for 1sec")
    remaining = 1
    while remaining > 0:
        print(f'{remaining:.2f} seconds left')
        yield True
        remaining -= state.delta_time
    print("Done waiting")
    yield False

class TestState(event_manager.EventManagerMixin):
    def __init__(self):
        super().__init__()
        self.delta_time = 0.15

state = TestState()
state.queue_event(event_manager.Event(_wait))
while state.events_left() > 0:
    print(f'{state.delta_time} elapsed')
    state.dispatch(state)
