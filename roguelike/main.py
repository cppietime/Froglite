import moderngl as mgl
import pygame as pg

from roguelike import (
    game,
    settings
)
from roguelike.engine import assets

pg.init()
ico = pg.image.load(assets.asset_path('icon.png'))
pg.display.set_icon(ico)
pg.display.set_caption(settings.NAME)
screen = pg.display.set_mode(settings.SCREEN_SIZE, pg.DOUBLEBUF | pg.OPENGL)
gl_ctx = mgl.create_context(require=330)
game.gameloop(screen, gl_ctx, settings.MAX_FPS)