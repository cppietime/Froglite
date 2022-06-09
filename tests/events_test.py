from roguelike.engine import event_manager, awaiting

# event0 = event_manager.Event([
    # (lambda state, event: print("Event run!"), ()),
    # (lambda state, event: (state.start_event(event1), event1.attach(event)), ()),
    # (lambda state, event: print("Event done!"), ())
# ])

# event1 = event_manager.Event([
    # (lambda state, event: print("Event1!!!"), ()),
    # (lambda state, event: print("Goodbye"), ())
# ])

def _event0(state, event):
    print("Event run!")
    event1 = event_manager.Event(_event1)
    event1.attach(event)
    state.start_event(event1)
    while event.locked():
        print("Waiting")
        yield True
    print("Event done!")
    yield False

def _event1(state, event):
    print("Event1!!!")
    yield True
    print("Goodbye")
    yield False

class TestState(event_manager.EventManagerMixin):
    def __init__(self):
        super().__init__()
        self.delta_time = 0.15

state = TestState()
state.queue_event(event_manager.Event(_event0))
while state.events_left() > 0:
    print(f'{state.delta_time} elapsed')
    state.dispatch(state)