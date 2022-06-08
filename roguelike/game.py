from collections import defaultdict
import pygame as pg

from . import (
    gamestate,
    inputs,
    renderer
)

def gameloop(screen, gl_ctx, max_fps):
    clock = pg.time.Clock()
    inputstate  = inputs.InputState()
    state_manager = gamestate.GameStateManager()
    rend = renderer.Renderer(gl_ctx)
    
    running = True
    while running:
        # Gameloop logic
        inputstate.reset_input()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            else:
                inputstate.process_event(event)
        inputstate.record_mouse()
        delta_time = clock.tick(max_fps)
        state_manager.update(delta_time)
        state_manager.render(delta_time, rend)
        pg.display.flip()
    pg.quit()