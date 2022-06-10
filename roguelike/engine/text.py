from dataclasses import dataclass
from typing import (
    Dict,
    Tuple,
    TYPE_CHECKING
)

import moderngl as mgl # type: ignore
import pygame as pg

from . import (
    sprite
)

if TYPE_CHECKING:
    from .renderer import Renderer

Offset = Tuple[float, float]
Color = Tuple[float, float, float, float]

@dataclass
class CharBank:
    glyphs: Dict[int, sprite.Sprite]
    line_height: float
    renderer: 'Renderer'
    
    def str_size(self,
                 msg: str,
                 scale:Offset=(1, 1),
                 max_width:float=-1) -> Offset:
        x, y = 0., 0.
        max_x = 0.
        for ch in msg:
            if ch == '\n':
                x = 0.
                y += self.line_height * scale[1]
            if ord(ch) not in self.glyphs:
                continue
            glyph = self.glyphs[ord(ch)]
            size = glyph.size_texels
            width = size[0] * scale[0]
            if max_width > 0 and x + width >= max_width:
                x = 0.
                y += self.line_height * scale[1]
            x += width
            max_x = max(x, max_x)
        return max_x, y + self.line_height
    
    def scale_to_bound(self, msg: str, bounds: Offset) -> float:
        """Get the scale factor that allows msg to fit inside bounds"""
        if not bounds:
            return 1.
        size = 0.
        at_scale = self.str_size(msg)
        if bounds[0] > 0:
            size = bounds[0] / at_scale[0]
        if bounds[1] > 0:
            size_h = bounds[1] / at_scale[1]
            if size == 0 or size_h < size:
                size = size_h
        if size == 0:
            return 1.
        return size
    
    def draw_str(self,
                 msg: str,
                 pos: Offset,
                 color:Color=(1, 1, 1, 1),
                 scale:Offset=(1, 1),
                 max_width:float=-1) -> None:
        x, y = pos
        for ch in msg:
            if ch == '\n':
                x = pos[0]
                y += self.line_height * scale[1]
                continue
            if ord(ch) not in self.glyphs:
                continue
            glyph = self.glyphs[ord(ch)]
            size = glyph.size_texels
            width = size[0] * scale[0]
            if max_width > 0 and x + width - pos[0] >= max_width:
                x = pos[0]
                y += self.line_height * scale[1]
            height = size[1] * scale[1]
            self.renderer.render_sprite(glyph,
                                        (x, y),
                                        (width, height),
                                        color=color)
            x += width
    
    @staticmethod
    def fontCharBank(typeface: str,
                     renderer: 'Renderer',
                     antialiasing:bool=True,
                     size:int=64) -> 'CharBank':
        glyph_surfaces = {}
        font = pg.font.SysFont(typeface, size)
        sum_w, max_h = 0, 0
        for ch in range(32, 127):
            surf = font.render(chr(ch), antialiasing, (255, 255, 255))\
                .convert_alpha()
            glyph_surfaces[ch] = pg.transform.flip(surf, False, True)
            rect = surf.get_rect()
            sum_w += rect.width
            max_h = max(max_h, rect.height)
        fbo = renderer.register_fbo(None, (sum_w, max_h), 1, True, False)
        fbo.use()
        tex = fbo.color_attachments[0]
        tex.filter = mgl.NEAREST, mgl.NEAREST
        renderer.clear(0, 0, 0, 0)
        x = 0
        glyphs = {}
        for ch, glyph in glyph_surfaces.items():
            temp_tex = renderer.gl_ctx.texture(glyph.get_size(),
                                               4,
                                               glyph.get_buffer())
            temp_spr = sprite.Sprite(temp_tex, (0, 0), glyph.get_size())
            renderer.render_sprite(temp_spr, (x, 0), glyph.get_size())
            temp_tex.release()
            glyphs[ch] = sprite.Sprite(tex, (x, 0), glyph.get_size())
            x += glyph.get_rect().width
        fbo.release()
        return CharBank(glyphs, max_h, renderer)