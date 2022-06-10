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

inputstate = inputs.InputState()
manager = gamestate.GameStateManager(inputstate=inputstate)
bottom_state = ui.MenuState()
top_state = ui.MenuState()
alter_state = ui.MenuState()
alter_state.callbacks_on_push.append(lambda _: print("Altered state pushed!"))
top_state.callbacks_on_pop.append(lambda _: print("Top state popped!"))

def _top_state_event(state, event):
    anim = tween.Animation([
        (0, tween.Tween(top_state.widget.widget.base_offset, 'x', -1000, 500, 1)),
        (0, tween.Tween(top_state.widget.bounding_rect, 'x', -1000, 500, 1)),
        (0, tween.Tween(label_nothing.text_color, 0, 0, 1, 0, is_list=True)),
        (0, tween.Tween(label_nothing.text_color, 0, 1, 0, 1.25, is_list=True, step=True)),
    ])
    anim.attach(state)
    state.begin_animation(anim)
    yield False

top_state.callbacks_on_push.append(lambda state: state.start_event(event_manager.Event(_top_state_event)))
top_state.callbacks_on_pop.append(lambda _: setattr(top_state.widget.bounding_rect, 'x', -1000))

font = rend.get_font('Ariel', 100)
img = rend.load_texture('test_sprite.png')
spr = sprite.Sprite(img, (0, 0), img.size)
img_v = rend.load_texture('test_mask.png')
spr_v = sprite.Sprite(img_v, (0, 0), (400, 400))

inactive = ui.Label(spr, (50, 50, 200, 50), bg_color=(.75,.75,.75,.5), text="Inactive", text_rect=(50, 50, 200, 50), font=font)
active = ui.Label(spr, (50, 50, 200, 50), bg_color=(1,1,1,1), text="ACTIVE", text_rect=(50, 50, 200, 50), font=font)

inactive_up = ui.Label(spr, (0, 0, 200, 50), bg_color=(.9, .7, .7, .75), text="Push state", text_rect=(0, 0, 200, 50), font=font)
active_up = ui.Label(spr, (0, 0, 200, 50), bg_color=(1, 1, 1, 1), text="Push state", text_rect=(0, 0, 200, 50), font=font, text_color=(1, 0, 0, 1))
inactive_down = ui.Label(spr, (0, 0, 200, 50), bg_color=(.5, .7, .7, .75), text="Pop state", text_rect=(0, 0, 200, 50), font=font)
active_down = ui.Label(spr, (0, 0, 200, 50), bg_color=(1, 1, 1, 1), text="Pop state", text_rect=(0, 0, 200, 50), font=font, text_color=(1, 0, 0, 1))
inactive_quit = ui.Label(spr, (0, 0, 200, 50), bg_color=(.5, .7, .7, .75), text="Quit", text_rect=(0, 0, 200, 50), font=font)
active_quit = ui.Label(spr, (0, 0, 200, 50), bg_color=(1, 1, 1, 1), text="Quit", text_rect=(0, 0, 200, 50), font=font, text_color=(1, 0, 0, 1))
inactive_alter = ui.Label(spr, (0, 0, 200, 50), bg_color=(.9, .7, .7, .75), text="Replace state", text_rect=(0, 0, 200, 50), font=font)
active_alter = ui.Label(spr, (0, 0, 200, 50), bg_color=(1, 1, 1, 1), text="Replace state", text_rect=(0, 0, 200, 50), font=font, text_color=(1, 0, 0, 1))
label_nothing = ui.Label(None, None, text="Label", text_rect=(0, 0, 200, 50), font=font)

button_push = ui.TwoLabelButton(inactive=inactive_up, active=active_up, command = lambda state: state.manager.push_state(top_state))
button_pop = ui.TwoLabelButton(inactive=inactive_down, active=active_down, command = lambda state: state.die())
button_quit = ui.TwoLabelButton(inactive=inactive_quit, active=active_quit, command = lambda state: state.die())
button_alter1 = ui.TwoLabelButton(inactive=inactive_alter, active=active_alter, command = lambda state: (state.die(), state.manager.push_state(alter_state)))
button_alter2 = ui.TwoLabelButton(inactive=inactive_alter, active=active_alter, command = lambda state: (state.die(), state.manager.push_state(bottom_state)))

bottom_state.widget.widget.widgets += [button_push, button_quit, button_alter1]
bottom_state.widget.widget.base_offset.x = 200
bottom_state.widget.widget.base_offset.y = 200
bottom_state.widget.widget.spacing = 50
bottom_state.widget.widget.zero_point = 1
bottom_state.widget.bounding_rect = tween.AnimatableMixin(200, 200, 200, 150)
top_state.widget.widget.widgets += [label_nothing, button_pop]
top_state.widget.widget.base_offset.x = 500
top_state.widget.widget.base_offset.y = 200
top_state.widget.widget.spacing = 50
top_state.widget.bounding_rect = tween.AnimatableMixin(-1000, 200, 200, 100)
alter_state.widget.widget.widgets += [button_alter2, button_push]
alter_state.widget.widget.base_offset.x = 200
alter_state.widget.widget.base_offset.y = 400
alter_state.widget.widget.spacing = 200
alter_state.widget.widget.horizontal = True
alter_state.widget.widget.zero_point = 0.5
alter_state.widget.bounding_rect = tween.AnimatableMixin(200, 400, 400, 50)

manager.push_state(bottom_state)

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
    
    manager.update(delta_time)
    manager.render(delta_time, rend)
    
    if not manager.any_states_active():
        running = False
    
    pg.display.flip()
    delta_time = clock.tick(144) / 1000
    # print(clock.get_fps())

pg.quit()