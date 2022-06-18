import logging
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
    from roguelike.world.world_gen import WorldGenerator

class LadderEntity(entity.Entity):
    def __init__(self, *args, **kwargs):
        self.size = kwargs.pop('size')
        self.key_item = kwargs.pop('key_item', None)
        self.key_count = kwargs.pop('key_count', 0)
        self.active = False
        self.done_message = False
        
        # Temporary debug
        self.class_anim = assets.Animations.instance.player
        super().__init__(*args, passable=True, **kwargs)
        self.callbacks_on_update.append(LadderEntity.move_callback)
    
    def move_callback(self,
                      delta_time: float,
                      state: 'GameState',
                      player_pos: Tuple[int, int]) -> None:
        dms = cast(dungeon.DungeonMapState, state)
        if self.key_item is not None and not self.done_message:
            player_ent = dms.dungeon_map.player
            player_ent.pain_particle(state,
                    f'Need {self.key_item.name} x{self.key_count}',
                    (1, 1, 0, 1))
            self.done_message = True
        player_ent = dms.dungeon_map.player
        if player_pos == self.dungeon_pos:
            works = self.key_item is None
            if not works:
                works = player_ent.inventory.take_item(self.key_item,
                                                       self.key_count)
            if works:
                self.to_next_room(dms)
            elif not self.active:
                self.active = True
                self.pain_particle(
                    state,
                    f'Need {self.key_item.name} x{self.key_count}',
                    (1, 1, 0, 1))
        else:
            self.active = False
    
    def to_next_room(self, state: dungeon.DungeonMapState) -> None:
        logging.debug('Will move player to next room')
        warp(state,
             world_gen.world_generators[assets.variables['world_gen']],
             self.size)

def warp(state: dungeon.DungeonMapState,
         world_type: 'WorldGenerator',
         size: Tuple[int, int]) -> None:
    def _script(_state, event):
        while _state.locked():
            yield True
        assets.variables['difficulty'] += 1
        def _thrd():
            _state.generate_from(world_type, size)
        thread = threading.Thread(target = _thrd)
        thread.start()
        anim = tween.Animation([
            (0, tween.Tween(_state, 'blackout', 0, 1, .5))
        ])
        anim.attach(_state)
        _state.begin_animation(anim)
        _state.lock()
        while thread.is_alive():
            yield True
        _state.unlock()
        _state.enter_loaded_room()
        anim = tween.Animation([
            (0, tween.Tween(_state, 'blackout', 1, 0, .5))
        ])
        anim.attach(_state)
        _state.begin_animation(anim)
        yield False
    state.queue_event(event_manager.Event(_script))
    
        