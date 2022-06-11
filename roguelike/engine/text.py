from dataclasses import dataclass
from enum import IntEnum
from typing import (
    Dict,
    Optional,
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

class AlignmentH(IntEnum):
    LEFT = 0
    CENTER = 1
    RIGHT = 2

class AlignmentV(IntEnum):
    TOP = 0
    CENTER = 1
    BOTTOM = 2

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
        word_mkr_x = 0.
        for ch in msg:
            if ch == '\n':
                x = word_mkr_x
                y += self.line_height * scale[1]
                word_mkr_x = 0.
                continue
            if ord(ch) not in self.glyphs:
                continue
            glyph = self.glyphs[ord(ch)]
            size = glyph.size_texels
            width = size[0] * scale[0]
            if max_width > 0 and x + width >= max_width:
                x = 0.
                y += self.line_height * scale[1]
            if ch == ' ':
                word_mkr_x = 0
            else:
                word_mkr_x += width
            x += width
            max_x = max(x, max_x)
        return max_x, y + self.line_height * scale[1]
    
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
        i = 0
        while i < len(msg):
            next_space = msg.find(' ', i)
            if next_space == -1:
                next_space = len(msg)
            next_line = msg.find('\n', i)
            if next_line == -1:
                next_line = len(msg)
            until = min(next_space, next_line)
            word = msg[i:until]
            width = self.str_size(word, scale)[0]
            if max_width > 0 and x + width - pos[0] >= max_width:
                x = pos[0]
                y += self.line_height * scale[1]
            
            for ch in word:
                if ord(ch) not in self.glyphs:
                    continue
                glyph = self.glyphs[ord(ch)]
                size = glyph.size_texels
                width = size[0] * scale[0]
                height = size[1] * scale[1]
                self.renderer.render_sprite(glyph,
                                            (x, y),
                                            (width, height),
                                            color=color)
                x += width
            
            i = until
            while i < len(msg) and msg[i] in ' \n':
                if msg[i] == ' ':
                    x += self.glyphs[ord(' ')].size_texels[0] * scale[0]
                else:
                    x = pos[0]
                    y += self.line_height * scale[1]
                i += 1
            
        # for ch in msg:
            # if ch == '\n':
                # x = pos[0]
                # y += self.line_height * scale[1]
                # continue
            # if ord(ch) not in self.glyphs:
                # continue
            # glyph = self.glyphs[ord(ch)]
            # size = glyph.size_texels
            # width = size[0] * scale[0]
            # if max_width > 0 and x + width - pos[0] >= max_width:
                # x = pos[0]
                # y += self.line_height * scale[1]
            # height = size[1] * scale[1]
            # self.renderer.render_sprite(glyph,
                                        # (x, y),
                                        # (width, height),
                                        # color=color)
            # x += width
    
    def draw_str_in(self,
                 msg: str,
                 pos: Offset,
                 bounds: Offset,
                 color: Color=(1, 1, 1, 1),
                 scale: Optional[Offset]=None,
                 alignment: Tuple[AlignmentH, AlignmentV]=\
                    (AlignmentH.LEFT, AlignmentV.TOP)) -> None:
        if scale is None:
            scale_n = self.scale_to_bound(msg, bounds)
            scale = (scale_n, scale_n)
        str_size = self.str_size(msg, scale)
        
        x = pos[0]
        if alignment[0] == AlignmentH.CENTER:
            x += (bounds[0] - str_size[0]) / 2
        if alignment[0] == AlignmentH.RIGHT:
            x += (bounds[0] - str_size[0])
        
        y = pos[1]
        if alignment[1] == AlignmentV.CENTER:
            y += (bounds[1] - str_size[1]) / 2
        if alignment[1] == AlignmentV.BOTTOM:
            y += (bounds[1] - str_size[1])
        
        self.draw_str(msg, (x, y), color, scale)
    
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