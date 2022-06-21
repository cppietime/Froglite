import collections
import json
import math
import os
import sys
from typing import (
    cast,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    TYPE_CHECKING
)

import moderngl as mgl # type: ignore
import pygame as pg

from roguelike.engine import (
    sprite
)

if TYPE_CHECKING:
    from roguelike.engine.renderer import Renderer

def asset_path(base_path: str) -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        baesdir = sys._MEIPASS # type: ignore
    else:
        basedir = os.path.join(os.path.split(__file__)[0],
                               os.pardir,
                               os.pardir)
    return os.path.abspath(os.path.join(basedir, 'assets', base_path))

class Textures:
    instance: 'Textures'
    def __init__(self):
        self.textures: Dict[str, mgl.Texture] = {}
    
    def __getattr__(self, name: str) -> mgl.Texture:
        return self.textures[name]
    
    @staticmethod
    def load_textures(renderer: 'Renderer',
                      source: Dict[str, Dict[str, str]]) -> None:
        Textures.instance = Textures()
        for key, value in source.items():
            tex_name = value.pop("source")
            other_params: Dict[str, Any] = {}
            for p_key, p_value in value.items():
                if p_key == 'filter':
                    other_params[p_key] = p_value, p_value
                elif p_key in ['repeat_x', 'repeat_y']:
                    other_params[p_key] = p_value
            Textures.instance.textures[key] =\
                renderer.load_texture(tex_name, **other_params)

class Sprites:
    instance: 'Sprites'
    def __init__(self):
        self.sprites: Dict[str, sprite.Sprite] = {}
    
    def one_sprite(self,
               tex_name: str,
               spr_name: str,
               offset: Tuple[int, int]=(0, 0),
               size: Optional[Tuple[int, int]]=None,
               color: Tuple[float, float, float, float] = (1, 1, 1, 1),
               angle: float = 0)\
               -> sprite.Sprite:
        texture = Textures.instance.textures[tex_name]
        if size is None:
            t_size = texture.size
        else:
            t_size = size
        spr = sprite.Sprite(
            texture, offset, t_size, color, angle * math.pi / 180)
        self.sprites[spr_name] = spr
        return spr
    
    def sprites_of_size(self,
                        tex_name: str,
                        spr_names: Sequence[str],
                        offsets: Sequence[Tuple[int, int]],
                        sizes: Sequence[Tuple[int, int]],
                        colors: Sequence[Tuple[
                                        float, float,
                                        float, float]] = ((1, 1, 1, 1),),
                        angles: Sequence[float] = (0,))\
                        -> List[sprite.Sprite]:
        assert len(sizes) == 1 or len(sizes) == len(offsets)
        assert len(colors) == 1 or len(colors) == len(offsets)
        assert len(spr_names) == 1 or len(spr_names) == len(offsets)
        assert len(angles) == 1 or len(angles) == len(offsets)
        each_offset = (tuple(offset) for offset in offsets)
        each_size = (tuple(sizes[0]) for _ in offsets) if len(sizes) == 1\
            else (tuple(size) for size in sizes)
        each_color = (tuple(colors[0]) for _ in offsets) if len(colors) == 1\
            else (tuple(color) for color in colors)
        each_name = (f'{spr_names[0]}-{i}' for i, _ in enumerate(offsets))\
            if len(spr_names) == 1\
            else (name for name in spr_names)
        each_angle = (angles[0] for _ in offsets) if len(angles) == 1\
            else (angle for angle in angles)
        sprites_map = map(lambda x: self.one_sprite(tex_name, *x), # type: ignore
                          zip(each_name,
                              each_offset,
                              each_size,
                              each_color,
                              each_angle))
        return list(sprites_map)
    
    def __getattr__(self, name: str) -> sprite.Sprite:
        return self.sprites[name]

    @staticmethod
    def load_sprites(source: Dict[str, Dict[str, Any]]) -> None:
        Sprites.instance = Sprites()
        for name, big_dict in source.items():
            many = cast(bool, big_dict.get('many', False))
            tex_name = cast(str, big_dict['texture'])
            if many:
                offsets = cast(Sequence[Tuple[int, int]], big_dict['offsets'])
                sizes = cast(Sequence[Tuple[int, int]], big_dict['sizes'])
                colors = cast(Sequence[Tuple[float, float, float, float]],
                              big_dict.get('colors', ((1, 1, 1, 1),)))
                angles = cast(Sequence[float], big_dict.get('angles', (0,)))
                Sprites.instance.sprites_of_size(
                    tex_name, (name,), offsets, sizes, colors, angles)
            else:
                offset = cast(Tuple[int, int],
                              tuple(big_dict.get('offset', (0, 0))))
                size = cast(Optional[Tuple[int, int]],
                            big_dict.get('size', None))
                if size is not None:
                    size = cast(Tuple[int, int], tuple(size))
                color = cast(Tuple[float, float, float, float],
                             tuple(big_dict.get('color', (1, 1, 1, 1))))
                angle = cast(float, big_dict.get('angle', 0))
                Sprites.instance.one_sprite(
                    tex_name, name, offset, size, color, angle)

_AnimState_In = Dict[str, Dict[str, Sequence[str]]]
_AnimDir = List[sprite.Sprite]
_AnimState = Dict[sprite.AnimDir, Sequence[sprite.Sprite]]
_Animation = Dict[sprite.AnimState, _AnimState]

class Animations:
    instance: 'Animations'
    def __init__(self):
        self.animations: Dict[str, sprite.Animation] = {}
    
    def animation(self,
                  name: str,
                  anim_in: Dict[str, _AnimState_In],
                  speed: float) -> sprite.Animation:
        states: _Animation = {}
        for key, value in anim_in.items():
            state_key = sprite.AnimState[key]
            state: _AnimState = {}
            for d_key, d_value in value.items():
                dir_key = sprite.AnimDir[d_key]
                direction: _AnimDir = []
                for spr_name in d_value:
                    direction.append(Sprites.instance.sprites[spr_name])
                state[dir_key] = direction
            states[state_key] = state
        animation = sprite.Animation(states, speed)
        self.animations[name] = animation
        return animation
    
    def __getattr__(self, name: str) -> sprite.Animation:
        return self.animations[name]
    
    @staticmethod
    def load_animations(source: Dict[str, Dict[str, Any]]) -> None:
        Animations.instance = Animations()
        for name, value in source.items():
            speed = cast(float, value['speed'])
            anim_in = cast(Dict[str, _AnimState_In], value['animation'])
            Animations.instance.animation(name, anim_in, speed)

class Sounds:
    instance: 'Sounds'
    def __init__(self):
        self.sounds: Dict[str, pg.mixer.Sound] = {}
    
    def __getattr__(self, name: str) -> pg.mixer.Sound:
        return self.sounds[name]
    
    @staticmethod
    def load_sounds(source: Dict[str, Any]) -> None:
        Sounds.instance = Sounds()
        for name, path in source.items():
            path = asset_path(path)
            sound = pg.mixer.Sound(path)
            Sounds.instance.sounds[name] = sound

residuals: Dict[str, Any] = {}
variables: Dict[str, Any] = collections.defaultdict(lambda: None)
persists: Dict[str, Any] = collections.defaultdict(lambda: None)
running = True

def load_assets(renderer: 'Renderer', source: str) -> None:
    global residuals
    with open(asset_path(source)) as file:
        tdata: Dict[str, Any] = json.load(file)
    file_list = cast(List[str], tdata['files'])
    for filename in file_list:
        with open(asset_path(filename+'.json')) as file:
            fdata: Dict[str, Any] = json.load(file)
        residuals[filename] = fdata
    Textures.load_textures(renderer,
                           cast(Dict[str, Dict[str, str]],
                           residuals.pop('textures')))
    Sprites.load_sprites(cast(Dict[str, Dict[str, Any]],
                         residuals.pop('sprites')))
    Animations.load_animations(cast(Dict[str, Any],
                               residuals.pop('animations')))
    Sounds.load_sounds(residuals.pop('sounds'))

def save_path():
    if hasattr(sys, 'frozen'):
        basedir = os.path.abspath(os.path.expanduser('~'))
        basedir = os.path.join(basedir, '.this_game')
        if not os.path.exists(basedir):
            os.mkdir(basedir)
    else:
        basedir = os.path.join(os.path.split(__file__)[0],
                               os.pardir,
                               os.pardir)
    return os.path.abspath(os.path.join(basedir, 'save'))

def load_save():
    global variables, persists
    save_file = save_path()
    if not os.path.exists(save_file):
        return
    with open(save_file) as file:
        vp = json.load(file)
    saved_v = vp['variables']
    saved_p = vp['persists']
    variables.update(saved_v)
    persists.update(saved_p)

def save_save():
    vp = {'variables': variables, 'persists': persists}
    with open(save_path(), 'w') as file:
        json.dump(vp, file)