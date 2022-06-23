import dataclasses
import logging
import random
import threading

import moderngl as mgl # type: ignore
import numpy as np
import pygame as pg

from roguelike import settings
from roguelike.engine import (
    assets,
    gamestate,
    renderer,
    sprite,
    inputs,
    utils
)
from roguelike.states import (
    ui,
    game_over
)
from roguelike.entities import (
    entity,
    item_entity,
    player,
    slow_chaser,
    npc,
    spawn
)
from roguelike.bag import (
    consumables,
    inventory_state,
    keys,
    spells,
    weapons
)
from roguelike.world import (
    dungeon,
    wfc,
    world_gen,
    world_select
)
map_size = (20, 20)
pat_size = (4, 4)
use_jit = False
use_weights = True
tile_floor = 0
tile_wall = 1
tile_clear = 0
meta_map = [0, 1]
world_name = 'bspworld'

# logging.basicConfig(level=logging.DEBUG)

# Initialize context and screen
pg.mixer.pre_init(channels=1)
pg.init()
screen = pg.display.set_mode(settings.SCREEN_SIZE, pg.DOUBLEBUF | pg.OPENGL)
gl_ctx = mgl.create_context(require=330)
rend = renderer.Renderer(gl_ctx, screen_size=(1440, 1080))
inputstate = inputs.InputState()
manager = gamestate.GameStateManager(inputstate=inputstate)

assets.load_assets(rend, "assets.json")
assets.variables['world_gen'] = world_name

# Set settings
tile_size = settings.BASE_TILE_SIZE
entity.Entity.base_size = tile_size

# Initialize assets
dungeon.DungeonMapState.init_sprites(rend)
entity.EnemyEntity.hp_font = dungeon.DungeonMapState.font
ui.default_font = rend.get_font('Consolas', 64, antialiasing=False, bold=False)
inventory_state.InventoryBaseScreen.init_globs()
world_select.WorldSelect.init_globs()
game_over.GameOverState.init_resources()
entity.Entity.particle_backdrop = assets.Animations.instance.shadow
dungeon.init_tiles()
consumables.init_items()
keys.init_items()
spells.init_items()
weapons.init_items()
npc.init_chats()
world_gen.init_generators()
spawn.init()
ui.Button.sound = assets.Sounds.instance.ding
ui.WidgetHolder.sound = assets.Sounds.instance.ding
ui.PoppableMenu.pop_sound = assets.Sounds.instance.ding
entity.FightingEntity.melee_sound = assets.Sounds.instance.pow
assets.load_save()
assets.persists.setdefault('unlocked', {})
assets.persists['unlocked'][world_name] = True
assets.persists.setdefault('highests', {})

gener = world_gen.world_generators[world_name]

def reset_func():
    assets.variables['coins'] = 0
    assets.variables['difficulty'] = 0
game_over.reset_func = reset_func
# Generate the map multi-threadedly
def _thread():
    game_over.reset_func()
    # dmap = gener.generate_world(map_size)
    state = dungeon.DungeonMapState(tile_size=tile_size,
                                    base_generator=gener,
                                    base_size=map_size)
    manager.push_state(state)
# thread = threading.Thread(target=_thread)
# thread.start()

menu_state = world_select.WorldSelect()
manager.push_state(menu_state)

clock = pg.time.Clock()
delta_time = 0.
f_no = 0

# These parameters work-ish
gamma = .5
exposure = 3.
render_mode = True
while assets.running:
    inputstate.reset_input()
    for event in pg.event.get():
        if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            assets.running=False
        elif event.type == pg.KEYDOWN and event.key in (pg.K_u, pg.K_i, pg.K_o, pg.K_p, pg.K_y, pg.K_z, pg.K_x):
            if event.key == pg.K_u:
                gamma -= .1
            elif event.key == pg.K_i:
                gamma += .1
            elif event.key == pg.K_o:
                exposure -= .1
            elif event.key == pg.K_p:
                exposure += .1
            elif event.key == pg.K_z:
                assets.Sounds.instance.adjust_vol(False)
            elif event.key == pg.K_x:
                assets.Sounds.instance.adjust_vol(True)
            else:
                render_mode = not render_mode
            print(f'{gamma=}, {exposure=}')
        else:
            inputstate.process_event(event)
    inputstate.record_mouse()
    
    old = rend.screen
    old.use()
    rend.clear(0, 0, 0, 0)
    
    base_fbo = rend.push_fbo(tex_params={'filter': (mgl.NEAREST, mgl.NEAREST)})
    
    if render_mode:
        new = rend.push_fbo()
    
    manager.update(delta_time)
    manager.render(delta_time, rend)
    
    if render_mode:
        rend.apply_bloom(2, 1, threshold=.9)
        rend.apply_exposure(base_fbo, gamma=gamma, exposure=exposure)
        rend.pop_fbo()
    
    rend.fbo_to_fbo(old, base_fbo)
    rend.pop_fbo()
    old.use()
    
    pg.display.flip()
    delta_time = clock.tick(144) / 1000
    
    f_no += 1
    if f_no == 1000:
        f_no = 0
        logging.info(f'FPS: {clock.get_fps()}')

logging.debug('Running terminated')

assets.save_save()
pg.quit()