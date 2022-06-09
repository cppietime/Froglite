import dataclasses

import moderngl as mgl
import pygame as pg

from roguelike import (
    event_manager,
    game,
    inputs,
    renderer,
    settings,
    sprite,
    text,
    tween
)
from roguelike.states import (
    gamestate,
    ui
)

pg.init()
screen = pg.display.set_mode(settings.SCREEN_SIZE, pg.DOUBLEBUF | pg.OPENGL)
gl_ctx = mgl.create_context(require=330)
rend = renderer.Renderer(gl_ctx)
font = rend.get_font('Ariel', 100)

img = rend.load_texture('test_sprite.png')
spr = sprite.Sprite(img, (0, 0), img.size)

inactive = ui.Label(spr, (50, 50, 200, 50), bg_color=(.75,.75,.75,.5), text="Inactive", text_rect=(50, 50, 200, 50), font=font)
active = ui.Label(spr, (50, 50, 200, 50), bg_color=(1,1,1,1), text="ACTIVE", text_rect=(50, 50, 200, 50), font=font)
label = ui.Label(None, None, None, text="Sep", text_rect=(50, 50, 200, 50), font=font)
button = ui.TwoLabelButton(inactive=inactive, active=active)
button2 = ui.TwoLabelButton(inactive=inactive, active=active)

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


inputstate = inputs.InputState()

manager = gamestate.GameStateManager(inputstate=inputstate)
state = ui.MenuState()
state.widgets.background = bglabel
state.widgets.widgets.append(button)
state.widgets.widgets.append(label)
state.widgets.widgets.append(button2)
state.widgets.spacing = 100
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
    rend.clear(0, 0, 0, 1)
    
    # button.render(rend, (0, 0))
    manager.update(delta_time)
    manager.render(delta_time, rend)
    
    pg.display.flip()
    delta_time = clock.tick(144) / 1000
    print(clock.get_fps())

pg.quit()