import moderngl as mgl
import pygame as pg

from roguelike import settings
from roguelike.engine import (
    renderer,
    sprite,
    tween
)

pg.init()
screen = pg.display.set_mode(settings.SCREEN_SIZE, pg.DOUBLEBUF | pg.OPENGL)
gl_ctx = mgl.create_context(require=330)
rend = renderer.Renderer(gl_ctx)

texture = rend.load_texture('test_sprite.png')
sprite = sprite.Sprite(texture, (0, 0), texture.size)

spr_pos = tween.AnimatableMixin(0, 0, 200, 100)

clock = pg.time.Clock()
running=True
while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running=False
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_UP:
                spr_pos.y -= 5
            if event.key == pg.K_DOWN:
                spr_pos.y += 5
            if event.key == pg.K_LEFT:
                spr_pos.x -= 5
            if event.key == pg.K_RIGHT:
                spr_pos.x += 5
            if event.key == pg.K_RETURN:
                spr_pos.rotation += 0.5
    rend.screen.use()
    rend.clear()
    rend.fbos['pingpong0'].use()
    rend.clear()
    pos = (spr_pos.x, spr_pos.y)
    size = (spr_pos.w, spr_pos.h)
    rend.render_sprite(sprite, pos, size, angle=spr_pos.rotation)
    rend.fbo_to_fbo(None, rend.fbos['pingpong0'])
    pg.display.flip()
    clock.tick(144)
    print(clock.get_fps())

pg.quit()