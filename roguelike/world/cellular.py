from typing import (
    Set,
    Tuple
)

import numpy as np
import numpy.typing as npt

IArray = npt.NDArray[np.int32]

def run(grid: IArray,
        clear_below: int, 
        fill_from: int,
        clear_with: int, 
        fill_with: int,
        full: Set[int],
        num: int,
        corners: bool = True,
        border: bool = True) -> None:
    """Apply a cellular automaton to a 2D grid"""
    is_full = np.vectorize(full.__contains__)
    neighbors: Tuple[Tuple[int, int], ...] = (
        (0, 1),
        (0, -1),
        (1, 0),
        (-1, 0)
    )
    if corners:
        ord_neighbors = (
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1)
        )
        neighbors += ord_neighbors
    for _ in range(num):
        filled = np.where(is_full(grid), 1, 0)
        for y in range(grid.shape[0]):
            for x in range(grid.shape[1]):
                population = 0
                for dx, dy in neighbors:
                    if x + dx < 0 or x + dx >= grid.shape[1]\
                            or y + dy < 0 or y + dy >= grid.shape[0]:
                        population += 1 if border else 0
                        continue
                    population += filled[y + dy, x + dx]
                if population < clear_below:
                    grid[y, x] = clear_with
                elif population >= fill_from:
                    grid[y, x] = fill_with