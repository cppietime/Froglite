from dataclasses import dataclass
import os
import sys
from typing import (
    Any,
    Dict,
    Iterable,
    Optional,
    Sequence,
    Tuple
)

import moderngl as mgl # type: ignore
import numpy as np
import pygame as pg

from . import (
    assets,
    shaders,
    sprite,
    text
)

Offset = Tuple[float, float]
Color = Tuple[float, float, float, float]

class Renderer:
    def __init__(self, gl_ctx, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gl_ctx = gl_ctx
        self.gl_ctx.enable(mgl.BLEND)
        self.gl_ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        self.programs = {}
        self.vaos = {}
        self.fbos = {}
        self.fbo_stack = []
        self.fbo_stack_top = -1
        self.charbanks = {}
        self.screen = self.gl_ctx.screen
        self.screen_size = self.screen.size
        self.create_defaults()
    
    def register_program(self,
                         name: str,
                         vertex_shader: str,
                         fragment_shader: str,
                         varyings:Sequence[str]=()) -> mgl.Program:
        program = self.gl_ctx.program(vertex_shader=vertex_shader,
                                      fragment_shader=fragment_shader,
                                      varyings=varyings)
        self.programs[name] = program
        return program
    
    def register_vao(self,
                     name: str,
                     program: mgl.Program,
                     buffer_specs: Iterable[Tuple[Any, ...]])\
                     -> mgl.VertexArray:
        _buffer_specs = []
        for spec in buffer_specs:
            array = spec[0]
            buffer = self.gl_ctx.buffer(array)
            _buffer_specs.append((buffer, *spec[1:]))
        vao = self.gl_ctx.vertex_array(program, _buffer_specs)
        self.vaos[name] = vao
        return vao
    
    def register_fbo(self,
                     name: Optional[str],
                     size: Offset,
                     num_tex: int,
                     depth:bool=True,
                     register:bool=True,
                     tex_params:Dict[str,Any]={}) -> mgl.Framebuffer:
        textures = []
        for _ in range(num_tex):
            texture = self.gl_ctx.texture(size, 4, dtype='f2')
            texture.repeat_x = False
            texture.repeat_y = False
            for key, value in tex_params.items():
                setattr(texture, key, value)
            textures.append(texture)
        depth_att = None
        if depth:
            depth_att = self.gl_ctx.depth_texture(size)
            depth_att.repeat_x = False
            depth_att.repeat_y = False
        fbo = self.gl_ctx.framebuffer(tuple(textures), depth_att)
        if register:
            self.fbos[name] = fbo
        return fbo
    
    def current_fbo(self) -> mgl.Framebuffer:
        if isinstance(self.gl_ctx.fbo, mgl.mgl.InvalidObject):
            return self.screen
        return self.gl_ctx.fbo
    
    def push_fbo(self) -> mgl.Framebuffer:
        """Activates the next-up FBO"""
        self.fbo_stack_top += 1
        if self.fbo_stack_top == len(self.fbo_stack):
            new_fbo = self.register_fbo(None,
                                        self.screen_size,
                                        1,
                                        False,
                                        False)
            self.fbo_stack.append(new_fbo)
        new_fbo = self.fbo_stack[self.fbo_stack_top]
        new_fbo.use()
        return new_fbo
    
    def pop_fbo(self) -> mgl.Framebuffer:
        """Does not change FBO activation"""
        if self.fbo_stack_top < 0:
            raise AttributeError('Stack already empty')
        old_fbo = self.fbo_stack[self.fbo_stack_top]
        self.fbo_stack_top -= 1
        return old_fbo
    
    def load_texture(self,
                     imgname: str,
                     **kwargs) -> mgl.Texture:
        # if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # basedir = sys._MEIPASS
        # else:
            # basedir = os.path.join(os.path.split(__file__)[0], os.pardir)
        # assetdir = os.path.join(basedir, 'assets', imgname)
        assetdir = assets.asset_path(imgname)
        img = pg.transform.flip(pg.image.load(assetdir).convert_alpha(),
                                False,
                                True) # Flip vertically because OpenGL
        tex = self.gl_ctx.texture(img.get_size(), 4, img.get_buffer())
        tex.swizzle = 'BGRA'
        for key, value in kwargs.items():
            setattr(tex, key, value)
        return tex
    
    def _match_viewport(self) -> None:
        self.gl_ctx.viewport = (0, 0, *self.gl_ctx.fbo.size)
    
    def render_sprite(self,
                      sprite: sprite.Sprite,
                      pixel_pos: Offset,
                      size_pixels: Offset,
                      progname:str='quad',
                      angle:float=0,
                      positioning:Tuple[str, str]=('left', 'top'),
                      color:Color=(1, 1, 1, 1),
                      **kwargs) -> None:
        self._match_viewport()
        program = self.programs[progname]
        vao = self.vaos[progname]
        sprite.texture.use(0)
        program['tex'] = 0
        screen_size = self.gl_ctx.fbo.size
        
        if positioning[0].lower() == 'left':
            center_x_frac = pixel_pos[0] + size_pixels[0] / 2
        elif positioning[0].lower() == 'center':
            center_x_frac = pixel_pos[0]
        elif positioning[0].lower() == 'right':
            center_x_frac = pixel_pos[0] - size_pixels[0] / 2
        else:
            raise AttributeError(
                f'Unknown positioning specifier {positioning[0]}')
        if positioning[1].lower() == 'top':
            center_y_frac =\
                screen_size[1] - 1 - pixel_pos[1] - size_pixels[1] / 2
        elif positioning[1].lower() == 'center':
            center_y_frac = (screen_size[1] - 1 - pixel_pos[1])
        elif positioning[1].lower() == 'bottom':
            center_y_frac =\
                screen_size[1] - 1 - pixel_pos[1] + size_pixels[1] / 2
        else:
            raise AttributeError(
                f'Unknown positioning specifier {positioning[1]}')
        center_x_frac /= screen_size[0]
        center_y_frac /= screen_size[1]
        
        scale_x = size_pixels[0] / screen_size[0]
        scale_y = size_pixels[0] / screen_size[1]
        
        program['center_pos'] = center_x_frac * 2 - 1, center_y_frac * 2 - 1
        program['pre_scale'] = scale_x, scale_y
        program['post_scale'] = 1, size_pixels[1] / size_pixels[0]
        
        tex_size = sprite.texture.size
        program['uv_bottom_left'] = sprite.topleft_texels[0] / tex_size[0],\
            (tex_size[1] - 1 -
             sprite.topleft_texels[1]
             - sprite.size_texels[1]) / tex_size[1]
        program['uv_size'] = (sprite.size_texels[0] / tex_size[0],
                              sprite.size_texels[1] / tex_size[1])
        program['angle'] = angle + sprite.angle
        
        if 'colorMask' in program:
            m_col = [color[i] * sprite.color[i] for i in range(4)]
            program['colorMask'] = tuple(m_col)
        
        for key, value in kwargs.items():
            program[key] = value
        vao.render()
    
    def fbo_to_fbo(self,
                   dst: Optional[mgl.Framebuffer],
                   src: mgl.Framebuffer,
                   progname='quad',
                   **kwargs) -> None:
        if dst is None:
            dst = self.screen
        if dst is src:
            return
        self._match_viewport()
        program = self.programs[progname]
        vao = self.vaos[progname]
        dst.use()
        src.color_attachments[0].use(0)
        program['tex'] = 0
        program['center_pos'] = 0, 0
        program['pre_scale'] = 1, 1
        program['post_scale'] = 1, 1
        program['angle'] = 0
        program['uv_bottom_left'] = 0, 0
        program['uv_size'] = 1, 1
        if 'colorMask' in program and 'colorMask' not in kwargs:
            program['colorMask'] = 1, 1, 1, 1
        for key, value in kwargs.items():
            program[key] = value
        vao.render()
    
    def apply_bloom(self, size: int, passes: int, threshold:float=0.9)->None:
        current = self.gl_ctx.fbo
        if current == self.screen:
            raise AttributeError('Cannot bloom directly from screen')
        self.fbos['pingpong1'].clear(0, 0, 0, 0)
        self.fbo_to_fbo(self.fbos['pingpong1'],
                        current,
                        'extract_bloom',
                        threshold=threshold)
        
        self.fbos['pingpong0'].clear(0, 0, 0, 0)
        self.fbo_to_fbo(self.fbos['pingpong0'],
                        self.fbos['pingpong1'],
                        'blur',
                        horizontal=0,
                        blurSize=size)
        self.fbos['pingpong1'].clear(0, 0, 0, 0)
        self.fbo_to_fbo(self.fbos['pingpong1'],
                        self.fbos['pingpong0'],
                        'blur', horizontal=1,
                        blurSize=size)
        
        for i in range(1, passes):
            self.fbos['pingpong0'].clear(0, 0, 0, 0)
            self.fbo_to_fbo(self.fbos['pingpong0'],
                            self.fbos['pingpong1'],
                            'blur',
                            horizontal=0,
                            blurSize=size)
            self.fbos['pingpong1'].clear(0, 0, 0, 0)
            self.fbo_to_fbo(self.fbos['pingpong1'],
                            self.fbos['pingpong0'],
                            'blur', horizontal=1,
                            blurSize=size)
        
        self.fbo_to_fbo(self.fbos['pingpong0'], current)
        
        # pingpong0 holds the original image, pingpong1 holds the blur
        self.fbos['pingpong1'].color_attachments[0].use(1)
        self.fbo_to_fbo(current, self.fbos['pingpong0'], 'add', addition=1)
    
    def _safe_current(self,
                      dst: Optional[mgl.Framebuffer])\
                      -> Tuple[mgl.Framebuffer, mgl.Framebuffer]:
        current = self.gl_ctx.fbo
        if current == self.screen:
            raise AttributeError('Cannot apply effects directly from screen')
        if dst is None:
            dst = self.screen
        if dst == current:
            self.fbos['pingpong0'].clear(0, 0, 0, 0)
            self.fbo_to_fbo(self.fbos['pingpong0'], current)
            current = self.fbos['pingpong0']
        return dst, current
    
    def apply_exposure(self,
                       dst:Optional[mgl.Framebuffer]=None,
                       exposure:float=1,
                       gamma:float=2.2) -> None:
        dst, current = self._safe_current(dst)
        self.fbo_to_fbo(dst, current, 'gamma', exposure=exposure, gamma=gamma)
    
    def apply_vignette(self,
                       dst:Optional[mgl.Framebuffer]=None,
                       mask:Optional[mgl.Texture]=None) -> None:
        if mask is None:
            self.fbo_to_fbo(dst, self.gl_ctx.fbo)
            return
        dst, current = self._safe_current(dst)
        mask.use(1)
        self.fbo_to_fbo(dst, current, 'vignette', mask=1)
    
    def clear(self,
              r:float=0,
              g:float=0,
              b:float=0,
              a:float=0,
              depth:float=1) -> None:
        self.current_fbo().clear(r, g, b, a, depth)
    
    def get_font(self, name: str, size: int) -> text.CharBank:
        key = name, size
        if key not in self.charbanks:
            self.charbanks[key] = text.CharBank.fontCharBank(name,
                                                            self,
                                                            antialiasing=False,
                                                            size=size)
        return self.charbanks[key]
    
    def create_defaults(self) -> None:
        
        shaders.register_shaders(self)
        
        self.register_fbo('pingpong0', self.screen_size, 1)
        self.register_fbo('pingpong1', self.screen_size, 1)
        self.register_fbo('accum0', self.screen_size, 1)
        self.register_fbo('accum1', self.screen_size, 1)
        self.register_fbo('vignette', self.screen_size, 1)
