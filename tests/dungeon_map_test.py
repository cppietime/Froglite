import dataclasses

import moderngl as mgl # type: ignore
import pygame as pg

from roguelike import settings
from roguelike.engine import (
    gamestate,
    renderer,
    sprite,
    inputs
)
from roguelike.states import dungeon
from roguelike.entities import (
    entity,
    player,
    slow_chaser
)
from roguelike.bag import inventory_state

pg.init()
screen = pg.display.set_mode(settings.SCREEN_SIZE, pg.DOUBLEBUF | pg.OPENGL)
gl_ctx = mgl.create_context(require=330)
rend = renderer.Renderer(gl_ctx)
inputstate = inputs.InputState()
manager = gamestate.GameStateManager(inputstate=inputstate)
tile_size = settings.BASE_TILE_SIZE

entity.Entity.base_size = tile_size

dungeon.DungeonMapState.init_sprites(rend)
player.PlayerEntity.init_sprites(rend)
slow_chaser.SlowChaserEntity.init_sprites(rend)
entity.EnemyEntity.hp_font = dungeon.DungeonMapState.font
tex = rend.load_texture('button_bg.png', filter=(mgl.NEAREST, mgl.NEAREST))
spr = sprite.Sprite(tex, (0, 0), tex.size)
inventory_state.InventoryBaseScreen.active_button_bg = spr
inventory_state.InventoryBaseScreen.inactive_button_bg = dataclasses.replace(spr)
inventory_state.InventoryBaseScreen.inactive_button_bg.color = (.5, .5, .5, .9)
inventory_state.InventoryBaseScreen.set_font(rend.get_font('Consolas', 64))
inventory_state.InventoryBaseScreen.init_globs()
bd = rend.load_texture('back_shadow.png', filter=(mgl.NEAREST, mgl.NEAREST))
bd_anim = sprite.Animation.from_atlas(bd, (32, 32), ((32, 32),))
entity.Entity.particle_backdrop = sprite.Animation({
    sprite.AnimState.DEFAULT: {sprite.AnimDir.DEFAULT: bd_anim}
}, 1)

tile_tex = rend.load_texture('tile.png', filter=(mgl.NEAREST, mgl.NEAREST))
tile_spr = sprite.Sprite(tile_tex, (0, 0), tile_tex.size, color=(1, 1, 0, 1))
tile_spr2 = sprite.Sprite(tile_tex, (0, 0), (-tile_tex.size[0], -tile_tex.size[1]), color=(1, 0, 1, 1))
tile_spr3 = sprite.Sprite(tile_tex, (0, 0), (-tile_tex.size[0], tile_tex.size[1]), color=(0, .5, .5, 1))
tile_spr4 = sprite.Sprite(tile_tex, (0, 0), (tile_tex.size[0], -tile_tex.size[1]), color=(.8, .2, .2, 1))
tile_anim = sprite.Animation({sprite.AnimState.DEFAULT: {sprite.AnimDir.DEFAULT: [tile_spr, tile_spr2, tile_spr3, tile_spr4]}}, 1.0)
tile_anims = sprite.AnimationState(tile_anim)
tile = dungeon.DungeonTile(tile_anims, True, offset_type = dungeon.RandomAnimType.X_MINUS_Y, offset_power = 0.25)
dungeon_map = dungeon.DungeonMap((100, 100), [tile], vignette_color=(.2, .2, .2, 1))
for y in range(100):
    for x in range(100):
        dungeon_map.tile_map[(x, y)] = 0
player_ent = player.PlayerEntity(dungeon_pos=[20, 20])
dungeon_map.player = player_ent

chaser = slow_chaser.SlowChaserEntity(dungeon_pos=[17, 17])
chaser2 = slow_chaser.SlowChaserEntity(dungeon_pos=[17, 20])
dungeon_map.place_entity(chaser)
dungeon_map.place_entity(chaser2)

state = dungeon.DungeonMapState(dungeon=dungeon_map, tile_size=tile_size)
manager.push_state(state)

clock = pg.time.Clock()
running=True
delta_time = 0.
f_no = 0

# These parameters work-ish
gamma = .5
exposure = 3
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
    
    if render_mode:
        new = rend.push_fbo()
    
    manager.update(delta_time)
    manager.render(delta_time, rend)
    
    if render_mode:
        rend.apply_bloom(2, 1, threshold=.9)
        rend.apply_exposure(old, gamma=gamma, exposure=exposure)
    # rend.fbo_to_fbo(old, new)
        rend.pop_fbo()
    old.use()
    # rend.screen.use()
    
    if not manager.any_states_active():
        running = False
    
    pg.display.flip()
    delta_time = clock.tick(144) / 1000
    
    f_no += 1
    if f_no == 100:
        f_no = 0
        print(clock.get_fps())

pg.quit()