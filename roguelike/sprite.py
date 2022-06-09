from dataclasses import dataclass
from typing import Tuple

import moderngl as mgl

@dataclass
class Sprite:
    texture: mgl.texture.Texture
    topleft_texels: Tuple[int, int]
    size_texels: Tuple[int, int]