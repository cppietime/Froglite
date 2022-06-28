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
        self.target_type: Optional[str] = kwargs.pop('target', None)
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
                    f'Need {self.key_item.display} x{self.key_count}',
                    (1, 1, 0, 1))
            self.done_message = True
        player_ent = dms.dungeon_map.player
        if player_pos == self.dungeon_pos:
            if assets.persists.get('tutorial', 0) < 5:
                if not self.active:
                    self.pain_particle(
                        state,
                        'Finish tutorial first')
                    self.active = True
                return
            works = self.key_item is None
            if not works:
                works = player_ent.inventory.take_item(self.key_item,
                                                       self.key_count)
            if works:
                self.to_next_room(dms)
            elif not self.active:
                assets.Sounds.instance.ding.play()
                self.active = True
                self.pain_particle(
                    state,
                    f'Need {self.key_item.display} x{self.key_count}',
                    (1, 1, 0, 1))
        else:
            self.active = False
    
    def to_next_room(self, state: dungeon.DungeonMapState) -> None:
        logging.debug('Will move player to next room')
        assets.Sounds.instance.budu.play()
        assets.persists['tutorial'] = 6
        warp(state,
             self.target_type or assets.variables['world_gen'],
             self.size)

def warp(state: dungeon.DungeonMapState,
         world_type_name: str,
         size: Tuple[int, int],
         reset: bool=False) -> None:
    logging.debug(f'Warping to {world_type_name}')
    def _script(_state, event):
        world_type = world_gen.world_generators[world_type_name]
        while _state.locked():
            yield True
        if reset:
            assets.variables['difference'] = 0
        else:
            assets.variables['difficulty'] += 1
        assets.persists['highests'][world_type_name] =\
            max(assets.persists['highests'].get(world_type_name, 0),\
                assets.variables['difficulty'])
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
        if not assets.persists['unlocked'].get(world_type_name, False):
            _state.dungeon_map.player.pain_particle(
                _state, f'Unlocked {world_type.display_name}!')
            assets.persists['unlocked'][world_type_name] = True
        anim = tween.Animation([
            (0, tween.Tween(_state, 'blackout', 1, 0, .5))
        ])
        anim.attach(_state)
        _state.begin_animation(anim)
        yield False
    state.queue_event(event_manager.Event(_script))
    
        