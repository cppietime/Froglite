from roguelike import event_manager, tween

rect = tween.AnimatableMixin()

def _animate(state, event):
    animation = tween.Animation(rect, [tween.Tween('x', 0, 1.5, 2)])
    animation.attach(event)
    state.begin_animation(animation)
    print("Started animation")
    while event.locked():
        print(f'{rect.x=:.3f}')
        yield True
    print("Done!")
    yield False

class TestState(event_manager.EventManagerMixin, tween.AnimationManagerMixin):
    def __init__(self):
        super().__init__()
        self.delta_time = 0.15

state = TestState()
state.queue_event(event_manager.Event(_animate))
while state.events_left() > 0 or state.animations_left() > 0:
    state.dispatch(state)
    state.update_animations(state.delta_time)