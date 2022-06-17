import threading
from typing import (
    cast,
    Tuple,
    TYPE_CHECKING
)

from roguelike.engine import (
    assets,
    event_manager,
    tween
)
from roguelike.entities import entity
from roguelike.world import (
    dungeon,
    world_gen
)

if TYPE_CHECKING:
    from roguelike.engine.gamestate import GameState

class LadderEntity(entity.Entity):
    def __init__(self, *args, **kwargs):
        self.size = kwargs.pop('size')
        self.class_anim = assets.Animations.instance.player
        super().__init__(*args, passable=True, **kwargs)
        self.callbacks_on_update.append(LadderEntity.move_callback)
    
    def move_callback(self,
                      delta_time: float,
                      state: 'GameState',
                      player_pos: Tuple[int, int]) -> None:
        if player_pos == self.dungeon_pos:
            def _script(_state, event):
                dms = cast(dungeon.DungeonMapState, _state)
                while dms.locked():
                    yield True
                def _thrd():
                    world_gen_name = assets.variables['world_gen']
                    wgen = world_gen.world_generators[world_gen_name]
                    dms.generate_from(wgen, self.size)
                thread = threading.Thread(target = _thrd)
                thread.start()
                anim = tween.Animation([
                    (0, tween.Tween(dms, 'blackout', 0, 1, .5))
                ])
                anim.attach(dms)
                dms.begin_animation(anim)
                dms.lock()
                while thread.is_alive():
                    yield True
                dms.unlock()
                dms.enter_loaded_room()
                anim = tween.Animation([
                    (0, tween.Tween(dms, 'blackout', 1, 0, .5))
                ])
                anim.attach(dms)
                dms.begin_animation(anim)
                yield False
            state.queue_event(event_manager.Event(_script))
        