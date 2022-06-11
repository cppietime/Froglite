import moderngl as mgl # type: ignore
import pygame as pg

from roguelike import settings
from roguelike.engine import (
    gamestate,
    renderer,
    sprite,
    inputs
)
from roguelike.bag import (
    inventory_state,
    item
)

pg.init()
screen = pg.display.set_mode(settings.SCREEN_SIZE, pg.DOUBLEBUF | pg.OPENGL)
gl_ctx = mgl.create_context(require=330)
rend = renderer.Renderer(gl_ctx)
inputstate = inputs.InputState()
manager = gamestate.GameStateManager(inputstate=inputstate)

inventory_state.InventoryBaseScreen.set_font(rend.get_font('Consolas', 64))
inventory_state.InventoryBaseScreen.init_globs()
tex = rend.load_texture('test_sprite.png')
spr = sprite.Sprite(tex, (0, 0), tex.size)

inventory = item.Inventory()
state = inventory_state.InventoryBaseScreen(inventory=inventory)
state.obscures = False
state.widget.reset_scr = [.5, .5, .5, 1]
manager.push_state(state)
manager.push_state(state)

def do_thing(game_state, ui_state, owner):
    ui_state.display_message("Cuck")

key_item = item.ConsumableItem(name='Key!', icon=spr, description="A key", on_use=do_thing)
dumb_item = item.ConsumableItem(name='dUmB', icon=spr, description="Dumbass\n mf key", on_use=do_thing)
knife = item.WeaponItem(name="Knife", icon=None, description="A fukkin knice", damage_mul=1)
inventory.give_item(key_item, 4)
inventory.give_item(dumb_item, 3)
inventory.give_item(knife, 1)

clock = pg.time.Clock()
running=True
delta_time = 0.
f_no = 0
max_fps = 144
while running:
    inputstate.reset_input()
    for event in pg.event.get():
        if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            running=False
        else:
            inputstate.process_event(event)
    inputstate.record_mouse()
    
    rend.screen.use()
    rend.clear(0, 0, 0, 0)
    
    manager.update(delta_time)
    manager.render(delta_time, rend)
    
    if not manager.any_states_active():
        running = False
    
    pg.display.flip()
    delta_time = clock.tick(max_fps) / 1000
    
    f_no += 1
    if f_no == 100:
        f_no = 0
        print(clock.get_fps())

pg.quit()