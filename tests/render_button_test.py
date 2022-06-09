import dataclasses

import moderngl as mgl
import pygame as pg

from roguelike import settings
from roguelike.engine import (
    event_manager,
    gamestate,
    inputs,
    renderer,
    sprite,
    text,
    tween
)
from roguelike.states import (
    ui
)

pg.init()
screen = pg.display.set_mode(settings.SCREEN_SIZE, pg.DOUBLEBUF | pg.OPENGL)
gl_ctx = mgl.create_context(require=330)
rend = renderer.Renderer(gl_ctx)
font = rend.get_font('Ariel', 100)

img = rend.load_texture('test_sprite.png')
spr = sprite.Sprite(img, (0, 0), img.size)

img_v = rend.load_texture('test_mask.png')
spr_v = sprite.Sprite(img_v, (0, 0), (400, 400))

inactive = ui.Label(spr, (50, 50, 200, 50), bg_color=(.75,.75,.75,.5), text="Inactive", text_rect=(50, 50, 200, 50), font=font)
active = ui.Label(spr, (50, 50, 200, 50), bg_color=(1,1,1,1), text="ACTIVE", text_rect=(50, 50, 200, 50), font=font)
label = ui.Label(None, None, None, text="Sep", text_rect=(50, 50, 200, 50), font=font)
button = ui.TwoLabelButton(inactive=inactive, active=active)
button2 = ui.TwoLabelButton(inactive=inactive, active=active)
q_inactive = ui.Label(None, None, None, text="Quit", text_rect=(50, 50, 200, 50), font=font, text_color=(1, 0, 0.4, .9))
q_active = ui.Label(None, None, None, text="QUIT", text_rect=(50, 50, 200, 50), font=font, text_color=(1, 1, 1, 1))
q_button = ui.TwoLabelButton(inactive=q_inactive, active=q_active, command = gamestate.GameState.die)

bglabel = dataclasses.replace(inactive)
bglabel.bg_rect = (0, 0, 200, 400)
bglabel.text = "m E n U"

def _wait_for_anim(state, event):
    anim = tween.Animation([
        (0   , tween.Tween(button2.offset, 'x', 0, -10, .25)),
        (.25 , tween.Tween(button2.offset, 'x', -10, 10, .5)),
        (0   , tween.Tween(button.offset, 'y', 0, 20, .375)),
        (.375, tween.Tween(button.offset, 'y', 20, -20, .375)),
        (.125, tween.Tween(button2.offset, 'x', 10, 0, .25)),
        (.25 , tween.Tween(button.offset, 'y', -20, 0, .25)),
    ])
    anim.attach(event)
    anim.attach(state)
    state.begin_animation(anim)
    while event.locked():
        yield True
    yield False

button.command = lambda state: state.queue_event(event_manager.Event(_wait_for_anim))
button2.command = lambda state: print("But I was activated!")

button3 = dataclasses.replace(button)
button4 = dataclasses.replace(button2)

holder1 = ui.WidgetHolder(bglabel, [button , button2, q_button], horizontal=False, spacing=50, zero_point=0)
holder2 = ui.WidgetHolder(bglabel, [button3, button4], horizontal=False, spacing=50, zero_point=0)

inputstate = inputs.InputState()

manager = gamestate.GameStateManager(inputstate=inputstate)
state = ui.MenuState()
state.widget.widget.background = bglabel
state.widget.widget.horizontal = True
state.widget.widget.widgets.append(ui.MetaWidget(holder1, (0, 0, 250, 150)))
state.widget.widget.widgets.append(ui.MetaWidget(holder2, (0, 0, 250, 150)))
state.widget.bounding_rect = (0, 0, 500, 150)
state.widget.widget.spacing = 250
manager.push_state(state)

clock = pg.time.Clock()
running=True
delta_time = 0
while running:
    inputstate.reset_input()
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running=False
        else:
            inputstate.process_event(event)
    inputstate.record_mouse()
    
    rend.screen.use()
    rend.clear(0, 0, 0, 0)
    
    # button.render(rend, (0, 0))
    manager.update(delta_time)
    manager.render(delta_time, rend)
    
    if not manager.any_states_active():
        running = False
    
    pg.display.flip()
    delta_time = clock.tick(144) / 1000
    # print(clock.get_fps())

pg.quit()