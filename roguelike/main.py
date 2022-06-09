import moderngl as mgl
import pygame as pg

from roguelike import (
    game,
    settings
)

pg.init()
screen = pg.display.set_mode(settings.SCREEN_SIZE, pg.DOUBLEBUF | pg.OPENGL)
gl_ctx = mgl.create_context(require=330)
game.gameloop(screen, gl_ctx, settings.MAX_FPS)