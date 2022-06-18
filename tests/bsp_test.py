import numpy as np

from roguelike.engine import utils
from roguelike.world import bsp

size = (20, 20)
min_size = (5, 5)
arr = bsp.bsp(size, min_size, 0, 1, 2, False)
print(arr)

arr = bsp.bsp(size, min_size, 0, 1, 2, True)
print(arr)
utils.save_grid(arr, 'box.png')