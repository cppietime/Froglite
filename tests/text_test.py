import moderngl as mgl
import pygame as pg

from roguelike import settings
from roguelike.engine import (
    renderer,
    sprite,
    text,
    tween
)

pg.init()
screen = pg.display.set_mode(settings.SCREEN_SIZE, pg.DOUBLEBUF | pg.OPENGL)
gl_ctx = mgl.create_context(require=330)
rend = renderer.Renderer(gl_ctx)
font = rend.get_font('Ariel', 100)

clock = pg.time.Clock()
running=True
while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running=False
    
    rend.screen.use()
    rend.clear(0, 0, 0, 1)
    spr = font.glyphs[ord('A')]
    rend.render_sprite(spr, (200, 200), spr.size_texels, positioning=('left', 'top'), color=(1, 0, 0.5, 1))
    
    font.draw_str("Hello, world!", (50, 50))
    font.draw_str("Wrap me", (50, 500), scale=(2, 2), max_width=200)
    
    pg.display.flip()
    clock.tick(144)
    # print(clock.get_fps())

pg.quit()