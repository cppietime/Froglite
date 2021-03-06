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
spr = sprite.Sprite(texture, (0, 0), texture.size)

spr_pos = tween.AnimatableMixin(50, 50, 200, 200)

mask_t = rend.load_texture('test_mask.png')
mask = sprite.Sprite(mask_t, (0, 0), mask_t.size)

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
    rend.clear(1, 0, 0, 1)
    rend.fbos['accum0'].use()
    rend.clear(0, 0.25, 0, 1)
    pos = (spr_pos.x, spr_pos.y)
    size = (spr_pos.w, spr_pos.h)
    rend.render_sprite(spr, pos, size, angle=spr_pos.rotation)
    rend.apply_bloom(5, 1, threshold=0.5);
    
    rend.fbos['vignette'].use()
    rend.clear(0, 0, 0, 0)
    rend.render_sprite(mask, (settings.SCREEN_SIZE[0]/2, settings.SCREEN_SIZE[1]/2), (settings.SCREEN_SIZE[0],)*2, positioning=('center', 'center'))
    
    rend.fbos['accum0'].use()
    rend.fbos['accum1'].clear(0, 0, 0, 0)
    rend.apply_vignette(rend.fbos['accum1'], rend.fbos['vignette'].color_attachments[0])

    rend.fbos['accum1'].use()
    rend.apply_exposure(None, exposure=2, gamma=1)
    
    pg.display.flip()
    clock.tick(144)
    print(clock.get_fps())

pg.quit()