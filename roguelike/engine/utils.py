from collections import deque
from enum import Enum
import heapq
import math
import random
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple
)

import numpy as np
from numpy import typing as npt
from PIL import Image # type: ignore

from roguelike.engine import assets

Pos = Tuple[int, int]
Grid = Tuple[Pos, npt.NDArray[np.int32]]

_grid_cache: Dict[str, Grid] = {}
def load_grid(imgname: str) -> Grid:
    """Loads a paletted image as a grid of integers, cached by name"""
    if imgname in _grid_cache:
        return _grid_cache[imgname]
    asset_dir = assets.asset_path(imgname)
    with Image.open(asset_dir) as img:
        assert img.mode == 'P'
        grid = (img.size, np.array(img.getdata(), dtype=np.int32))
    _grid_cache[imgname] = grid
    return grid

def save_grid(grid: npt.NDArray[np.int32], fname: str) -> None:
    ba = bytearray()
    for px in grid.flatten():
        ba.append(px)
    im = Image.frombytes('P', grid.shape[::-1], bytes(ba))
    base = 51
    palette = []
    for i in range(216):
        gb, r = divmod(i, 6)
        b, g = divmod(gb, 6)
        palette += [((6 - r) % 6) * base,
                    ((6 - g) % 6) * base,
                    ((6 - b) % 6) * base]
    im.putpalette(palette, 'RGB')
    im.save(fname)

class CardinalDirections(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

def manhattan_dist(from_: Pos, to: Pos) -> int:
    return abs(from_[0] - to[0]) + abs(from_[1] - to[1])

def diag_dist(from_: Pos, to: Pos) -> int:
    return max(abs(from_[0] - to[0]), abs(from_[1] - to[1]))

AS_State = Tuple[float, float, Pos, Pos]

def a_star(costs: npt.NDArray[np.float64],
           from_: Pos,
           to: Pos,
           max_cost: Optional[float]=None) -> Optional[List[Pos]]:
    """Using A-star to calculate the shortest path from from_ to to
    Manhattan distance is used as the heuristic
    costs: row-major sequence of floats with the cost to enter each tile
    from_: starting point of search
    to: goal/end point of search
    max_cost: ignore paths that excede this value if it is provided
    Returns a list of tiles stepped on along the path, or None
    """
    size = costs.shape[::-1]
    frontier: List[AS_State] = []
    backtrack: Dict[Pos, Pos] = {}
    visited = {from_}
    heapq.heappush(frontier, (0, 0, from_, (0, 0)))
    while len(frontier) > 0:
        estimate, cost, current, previous = heapq.heappop(frontier)
        backtrack[current] = previous
        if current == to:
            path = [current]
            while current != from_:
                previous = backtrack[current]
                path.append(previous)
                current = previous
            path.reverse()
            return path
        x, y = current
        next_steps = [e.value for e in CardinalDirections]
        random.shuffle(next_steps)
        for step in next_steps:
            step = current[0] + step[0], current[1] + step[1]
            if step in visited:
                continue
            x, y = step
            if x < 0 or x >= size[0]:
                continue
            if y < 0 or y >= size[1]:
                continue
            heuristic = manhattan_dist(step, to)
            n_cost = cost + costs[y, x]
            if not math.isfinite(n_cost):
                continue
            if max_cost is None or cost <= max_cost:
                heapq.heappush(frontier,
                               (heuristic + n_cost, n_cost, step, current))
                visited.add(step)
    return None

def populate_djikstra(costs: npt.NDArray[np.float64],
                      starting_points: Iterable[Pos],
                      start_costs: Optional[
                        npt.NDArray[np.float64]] = None)\
                    -> npt.NDArray[np.float64]:
    """Populates each tile with a djikstra distance
    costs: row-major sequence of floats with the cost to enter each tile
    starting_points: points to update with cost of 0
    start_costs: optional previously calculated cost table,
        set all to infinity if None
    Returns a row-major sequence of the total costs to each each tile
        from the starting points
    """
    size = costs.shape[::-1]
    if start_costs is None:
        # start_costs = [float('inf')] * (size[0] * size[1])
        start_costs = np.full(costs.shape, float('inf'), dtype=float)
    else:
        start_costs = np.asanyarray(start_costs, dtype=float)
    frontier: List[Tuple[float, Pos]] =\
        list(map(lambda point: (0, point), starting_points))
    for x, y in starting_points:
        start_costs[y, x] = 0
    while len(frontier) > 0:
        cost, pos = heapq.heappop(frontier)
        x0, y0 = pos
        for direction in CardinalDirections:
            x, y = x0 + direction.value[0], y0 + direction.value[1]
            if x < 0 or x >= size[0] or y < 0 or y >= size[1]:
                continue
            old_cost = start_costs[y, x]
            new_cost = cost + costs[y, x]
            if not math.isfinite(new_cost):
                continue
            if new_cost < old_cost:
                start_costs[y, x] = new_cost
                heapq.heappush(frontier, (new_cost, (x, y)))
    return start_costs

def trace_djikstra(start: Pos, dists: npt.NDArray[np.float64]) -> List[Pos]:
    """Get a path from a specified starting point to a local minimum"""
    path: List[Pos] = [start]
    head = start
    while True:
        min_neighbor = head
        min_dist = dists[head[::-1]]
        for direction in CardinalDirections:
            x, y = head[0] + direction.value[0], head[1] + direction.value[1]
            if x < 0 or x >= dists.shape[1] or y < 0 or y >= dists.shape[0]:
                continue
            dist = dists[y, x]
            if dist < min_dist:
                min_dist = dist
                min_neighbor = x, y
        if min_neighbor == head:
            return path
        path.append(min_neighbor)
        head = min_neighbor

def clear_blockage(dists: npt.NDArray[np.float64]) ->\
        npt.NDArray[np.bool_]:
    """Returns a copy of dists where any grids that potentially block
    1-wide paths have infinite cost
    """
    finite = np.isfinite(dists)
    up = np.roll(finite, 1, 0) # Entries above each
    down = np.roll(finite, -1, 0)
    left = np.roll(finite, 1, 1)
    right = np.roll(finite, -1, 1)
    up_left = np.roll(up, 1, 1)
    up_right = np.roll(up, -1, 1)
    down_left = np.roll(down, 1, 1)
    down_right = np.roll(down, -1, 1)
    blockage = up & ~up_left & ~up_right
    blockage |= down & ~down_left & ~down_right
    blockage |= left & ~up_left & ~down_left
    blockage |= right & ~up_right & ~down_right
    blockage |= up & left & ~up_left &\
        ~(up_right & right & down_right & down & down_left)
    blockage |= up & right & ~up_right &\
        ~(up_left & left & down_left & down & down_right)
    blockage |= down & left & ~down_left &\
        ~(down_right & right & up_right & up & up_left)
    blockage |= down & right & ~down_right &\
        ~(down_left & left & up_left & up & up_right)
    return blockage

def group(size: Pos,
          passable: Sequence[bool]) -> List[Set[Pos]]:
    """Partition a map into groups of reachable tiles from each other
    passable: a row-major sequence of bools, True iff passable
    Returns a list of sets of the positions of all tiles in each group
    """
    # Initialize groups
    counts: List[Set[Pos]] = [] # Number of points in each group
    group_ids: List[int] = [] # Group peresnt at each point
    for xy, p in enumerate(passable):
        if not p:
            group_ids.append(-1)
            continue
        group_ids.append(len(counts))
        counts.append({divmod(xy, size[0])[::-1]})
    
    # Iterate over each unprocessed group until all joined
    igroup = 0
    ogroup = 0
    while True:
        # Identify next input group to use
        while igroup < len(counts) and len(counts[igroup]) == 0:
            igroup += 1
        if igroup == len(counts):
            # Complete
            break
        # Reassign to the lowest empty group
        if igroup != ogroup:
            counts[ogroup] = counts[igroup]
            counts[igroup] = set()
            for x, y in counts[ogroup]:
                xy = y * size[0] + x
                group_ids[xy] = ogroup
        group = counts[ogroup]
        starting_point = next(iter(group))
        
        # Flood fill
        frontier = deque([starting_point])
        while len(frontier) > 0:
            x0, y0 = frontier.pop()
            for direction in CardinalDirections:
                x, y = x0 + direction.value[0], y0 + direction.value[1]
                if x < 0 or x >= size[0] or y < 0 or y >= size[1]:
                    continue
                xy = y * size[0] + x
                if not passable[xy]:
                    continue
                old_group = group_ids[xy]
                if old_group == ogroup:
                    group_ids[xy] = ogroup
                    continue
                counts[old_group].remove((x, y))
                group_ids[xy] = ogroup
                frontier.append((x, y))
                counts[ogroup].add((x, y))
        igroup += 1
        ogroup += 1
    return counts[:ogroup]
