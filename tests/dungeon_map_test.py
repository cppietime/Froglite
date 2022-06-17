import dataclasses
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
    player,
    slow_chaser,
    npc
)
from roguelike.bag import (
    consumables,
    inventory_state
)
from roguelike.world import (
    dungeon,
    wfc,
    world_gen
)
map_size = (20, 20)
pat_size = (4, 4)
use_jit = False
use_weights = True
tile_floor = 0
tile_wall = 1
tile_clear = 0
meta_map = [0, 1]

use_weights &= not use_jit
samp_size, samp_arr = utils.load_grid('map_sample.png')
samp_arr = samp_arr.reshape(samp_size[::-1])
f, b, ids, adjs, wts = wfc.find_adjacencies(samp_size, samp_arr, pat_size, True)
# print(samp_arr.reshape(samp_size[::-1]))
# print(f)
# print(np.array(ids).reshape(samp_size[::-1]))
# print(adjs)

# Initialize context and screen
pg.init()
screen = pg.display.set_mode(settings.SCREEN_SIZE, pg.DOUBLEBUF | pg.OPENGL)
gl_ctx = mgl.create_context(require=330)
rend = renderer.Renderer(gl_ctx, screen_size=(1440, 1080))
inputstate = inputs.InputState()
manager = gamestate.GameStateManager(inputstate=inputstate)

assets.load_assets(rend, "assets.json")
assets.variables['world_gen'] = 'mainworld'

# Set settings
tile_size = settings.BASE_TILE_SIZE
entity.Entity.base_size = tile_size

# Initialize assets
dungeon.DungeonMapState.init_sprites(rend)
entity.EnemyEntity.hp_font = dungeon.DungeonMapState.font
ui.default_font = rend.get_font('Consolas', 64, antialiasing=False, bold=False)
inventory_state.InventoryBaseScreen.init_globs()
game_over.GameOverState.init_resources()
entity.Entity.particle_backdrop = assets.Animations.instance.shadow
dungeon.init_tiles()
world_gen.init_generators()

# tile_anims = sprite.AnimationState(assets.Animations.instance.tile)
# wall_anims = sprite.AnimationState(assets.Animations.instance.wall)
# tile = dungeon.DungeonTile(tile_anims, True, offset_type = dungeon.RandomAnimType.X_MINUS_Y, offset_power = 0.25)
# wall = dungeon.DungeonTile(wall_anims, False)

consumables.init_items()
npc.init_chats()

# Setup dungeon map
# gen = wfc.WaveFunction([set(f.values()),
                        # wfc.patterns_containing({1}, b),
                        # wfc.patterns_containing({0}, b)], adjs, pat_size, wts)

# wave_gen_class = world_gen.WallGeneratorWFC(samp_size, samp_arr, pat_size, meta_map, {1})
# gener = world_gen.WorldGenerator(wave_gen_class, [], world_gen.TileGeneratorPassThru(), [dungeon.tiles['floor'], dungeon.tiles['wall']], border=1)
gener = world_gen.world_generators['mainworld']

ceiling = [tile_wall] * map_size[0]
space = [tile_wall] + [tile_floor] * (map_size[0] - 2) + [tile_wall]
map_classes = ceiling + space * ((map_size[1] - 2) // 1) + ceiling
map_classes[map_size[0] + 2] = tile_clear
map_classes[map_size[0] * 2 - 2] = tile_clear
map_classes[map_size[0] * (map_size[1] - 2) + 2] = tile_clear
map_classes[map_size[0] * (map_size[1] - 1) - 2] = tile_clear
print(len(ceiling), len(space), len(map_classes))

dungeon_map = dungeon.DungeonMapSpawner(map_size, [dungeon.tiles['floor'], dungeon.tiles['wall']], (20, 20), vignette_color=(.2, .2, .2, 1), spawns=[
    ((17, 17), slow_chaser.PursuantEnemy, {'anim': assets.Animations.instance.slow_chaser, 'action_cost': 1.5}),
    ((17, 20), slow_chaser.PursuantEnemy, {'anim': assets.Animations.instance.slow_chaser, 'action_cost': 2}),
    # ((20, 17), npc.NPCEntity, {'anim': assets.Animations.instance.player, 'chat': npc.chats['test_chat']})
])

# Generate the map multi-threadedly
def _thread_old():
    grid = gen.wfc_tile(map_size, map_classes, use_jit=use_jit, use_weights=use_weights)
    for y in range(map_size[1]):
        for x in range(map_size[0]):
            xy = y * map_size[0] + x
            pattern = grid[xy]
            choice = b[pattern][0, 0]
            dungeon_map.tile_map.append(meta_map[choice])
            # dungeon_map.tile_map.append(map_classes[xy])
    np.set_printoptions(threshold=10000)
    map_arr = np.array(dungeon_map.tile_map).reshape(map_size[::-1])
    utils.save_grid(map_arr, f'level_{pat_size[0]}x{pat_size[1]}_{use_weights}.png')
    groups = utils.group(map_size, [t == 0 for t in dungeon_map.tile_map])
    player_group = max(enumerate(groups), key=lambda x: len(x[1]))[0]
    dungeon_map.player_pos = random.choice(list(groups[player_group]))
    for i, group in enumerate(groups):
        if i == player_group:
            continue
        for pos in group:
            xy = pos[1] * map_size[0] + pos[0]
            dungeon_map.tile_map[xy] = 1
    tile_map = np.asanyarray(dungeon_map.tile_map, dtype=float)\
        .reshape(map_size[::-1])
    tile_map[tile_map == 1.] = float('inf')
    tile_map[tile_map == 0.] = 1
    djikstra = utils.populate_djikstra(tile_map, (dungeon_map.player_pos,))
    blocking = utils.clear_blockage(djikstra)
    pos = np.where(np.isinf(djikstra) | blocking, -np.inf, djikstra).argmax()
    y, x = divmod(pos, map_size[0])
    print((x, y))
    dungeon_map.spawns.append(((x, y), npc.NPCEntity, {'anim': assets.Animations.instance.player, 'chat': npc.chats['test_chat']}))

    state = dungeon.DungeonMapState(dungeon=dungeon_map, tile_size=tile_size)
    manager.push_state(state)
def _thread():
    dmap = gener.generate_world(map_size)
    state = dungeon.DungeonMapState(dungeon=dmap, tile_size=tile_size)
    manager.push_state(state)
thread = threading.Thread(target=_thread)
thread.start()

clock = pg.time.Clock()
running=True
delta_time = 0.
f_no = 0

# These parameters work-ish
gamma = .5
exposure = 3.
render_mode = True
while running:
    inputstate.reset_input()
    for event in pg.event.get():
        if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            running=False
        elif event.type == pg.KEYDOWN and event.key in (pg.K_u, pg.K_i, pg.K_o, pg.K_p, pg.K_y):
            if event.key == pg.K_u:
                gamma -= .1
            elif event.key == pg.K_i:
                gamma += .1
            elif event.key == pg.K_o:
                exposure -= .1
            elif event.key == pg.K_p:
                exposure += .1
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
    
    # if not manager.any_states_active():
        # running = False
    
    pg.display.flip()
    delta_time = clock.tick(144) / 1000
    
    f_no += 1
    if f_no == 100:
        f_no = 0
        print(clock.get_fps())

pg.quit()