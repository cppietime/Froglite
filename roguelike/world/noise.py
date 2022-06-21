from typing import (
    Sequence,
    Tuple
)

import numpy as np
import numpy.typing as npt

Pos = Tuple[int, int]
IArray = npt.NDArray[np.int32]

def white(size: Pos,
          tiles: Sequence[int],
          weights: Sequence[float]) -> IArray:
    weights_arr = np.asanyarray(weights, dtype=float)
    weights_arr /= weights_arr.sum()
    return np.random.choice(tiles, size=size, p=weights_arr)

def _perlin_gradient(x: float, y: float) -> float:
    x0, y0 = int(x), int(y)
    xf, yf = x - x0, y - y0
    h00 = hash((x0, y0))
    h01 = hash((x0, y0 + 1))
    h10 = hash((x0 + 1, y0))
    h11 = hash((x0 + 1, y0 + 1))
    grad_00 = (xf if (h00&1) else -xf) + (yf if (h00&2) else -yf)
    grad_01 = (xf if (h01&1) else -xf) + (yf - 1 if (h01&2) else 1 - yf)
    grad_10 = (xf - 1 if (h10&1) else 1 - xf) + (yf if (h10&2) else -yf)
    grad_11 = (xf - 1 if (h11&1) else 1 - xf) + (yf - 1 if (h11&2) else 1 - yf)
    grad_x0 = grad_00 + (grad_10 - grad_00) * xf
    grad_x1 = grad_01 + (grad_11 - grad_01) * xf
    grad_xx = grad_x0 + (grad_x1 - grad_x0) * yf
    return grad_xx

def perlin(size: Pos,
           density: Tuple[float, float],
           tile_range: Sequence[int],
           offset: Tuple[float, float] = (0, 0),
           rectify: bool = True) -> IArray:
    height = np.zeros(size[::-1], dtype=float)
    for y in range(size[1]):
        yf = y / density[1] + offset[1]
        for x in range(size[0]):
            xf = x / density[0] + offset[0]
            height[y, x] = _perlin_gradient(xf, yf)
    if rectify:
        height = abs(height)
    else:
        height = height / 2 + .5
    mapper = np.vectorize(lambda x:\
        tile_range[min(len(tile_range) - 1, int((x * len(tile_range))))])
    return mapper(height)
