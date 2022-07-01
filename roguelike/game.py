from collections import defaultdict

import moderngl as mgl
import pygame as pg

from roguelike import settings

from roguelike.engine import (
    assets,
    gamestate,
    inputs,
    renderer
)
from roguelike.entities import (
    entity,
    player,
    npc,
    spawn
)
from roguelike.states import ui
from roguelike.world import (
    game_over,
    world_select,
    world_gen,
    dungeon
)
from roguelike.bag import (
    inventory_state,
    keys,
    charms,
    weapons,
    armor,
    consumables,
    spells
)

def init(rend: renderer.Renderer):
    assets.load_assets(rend, "assets.json")
    
    ui.default_font = rend.get_font(settings.TYPEFACE, settings.FONT_SIZE, antialiasing=False, bold=True)
    ui.Button.sound = assets.Sounds.instance.ding
    ui.WidgetHolder.sound = assets.Sounds.instance.ding
    ui.PoppableMenu.pop_sound = assets.Sounds.instance.ding

    tile_size = settings.BASE_TILE_SIZE
    dungeon.DungeonMapState.init_sprites(rend)
    
    entity.Entity.base_size = tile_size
    entity.EnemyEntity.hp_font = dungeon.DungeonMapState.font
    entity.FightingEntity.melee_sound = assets.Sounds.instance.pow
    
    inventory_state.InventoryBaseScreen.init_globs()
    world_select.WorldSelect.init_globs()
    game_over.GameOverState.init_resources()
    entity.Entity.particle_backdrop = assets.Animations.instance.shadow
    dungeon.init_tiles()
    consumables.init_items()
    keys.init_items()
    spells.init_items()
    weapons.init_items()
    armor.init_items()
    charms.init_items()
    npc.init_chats()
    world_gen.init_generators()
    spawn.init()
    
    assets.load_save()
    assets.persists.setdefault('unlocked', {})
    assets.persists['unlocked'][settings.FIRST_WORLD] = True
    assets.persists.setdefault('highests', {})
    
    def _rf():
        assets.variables['coins'] = 0
        assets.variables['difficulty'] = 0
    game_over.reset_func = _rf

def gameloop(screen, gl_ctx: 'Context', max_fps: int) -> None:
    clock = pg.time.Clock()
    inputstate = inputs.InputState()
    manager = gamestate.GameStateManager(inputstate=inputstate)
    rend = renderer.Renderer(gl_ctx, screen_size=(1440, 1080))
    
    init(rend)
    
    assets.running = True
    delta_time = 0
    
    menu_state = world_select.WorldSelect()
    manager.push_state(menu_state)
    
    while assets.running:
        # Gameloop logic
        
        # Record input
        inputstate.reset_input()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                assets.running = False
            else:
                inputstate.process_event(event)
        inputstate.record_mouse()
    
        old = rend.screen
        old.use()
        rend.clear(0, 0, 0, 0)
        
        base_fbo = rend.push_fbo(tex_params={'filter': (mgl.NEAREST, mgl.NEAREST)})
        new = rend.push_fbo()
        
        manager.update(delta_time)
        manager.render(delta_time, rend)
        
        rend.apply_bloom(settings.BLOOM_SIZE, settings.BLOOM_RUNS, threshold=settings.BLOOM_THRESHOLD, strength=settings.BLOOM_POW)
        rend.apply_exposure(base_fbo, gamma=settings.GAMMA, exposure=settings.EXPOSURE)
        rend.pop_fbo()
        rend.fbo_to_fbo(old, base_fbo)
        rend.pop_fbo()
        old.use()
        
        pg.display.flip()
        delta_time = clock.tick(settings.MAX_FPS) / 1000
    
    assets.save_save()
    pg.quit()