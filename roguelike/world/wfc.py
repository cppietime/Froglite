"""
Wave function collapse utilities
"""

from collections import (
    deque
)
from dataclasses import dataclass
import math
import random
import time
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    TYPE_CHECKING
)

import numba # type: ignore
import numpy as np
from numpy import typing as npt

from roguelike.engine import utils

Pos = Tuple[int, int]
WFMap = Sequence[int]
TileMap = Sequence[int]
TileState = Set[int]
TileRule = Sequence[TileState]
OffsetRule = Sequence[TileState]
History = Tuple[int, TileState, bool] # Position and previous valid states
Pattern = npt.NDArray[np.int64]
PKey = bytes

def pattern_at(size: Pos,
               data: Pattern,
               pattern_size: Pos,
               position: Pos) -> Pattern:
    pattern_list: Pattern = np.zeros(pattern_size, dtype=int)
    for y in range(pattern_size[1]):
        for x in range(pattern_size[0]):
            py = (y + position[1]) % size[1]
            px = (x + position[0]) % size[0]
            pattern_list[y, x] = data[py, px]
    return pattern_list

def gen_offsets(pattern_size: Pos) -> List[Pos]:
    return list(map(lambda x: x.value, utils.CardinalDirections))

def offset_pattern(pattern: Pattern,
                   pattern_size: Pos,
                   offset: Pos) -> Pattern:
    if offset[0] >= 0:
        slice_x = slice(offset[0], pattern_size[0])
    else:
        slice_x = slice(0, offset[0])
    if offset[1] >= 0:
        slice_y = slice(offset[1], pattern_size[1])
    else:
        slice_y = slice(0, offset[1])
    return pattern[slice_y, slice_x]

@numba.njit
def rotate_list(width: int, height: int, lst: List[int]) -> List[int]:
    rlst = [0] * (width * height)
    ctr = 0
    for x in range(width):
        for y in range(height):
            xy = y * width + x
            rlst[ctr] = lst[xy]
            ctr += 1
    return rlst

@numba.njit
def reflect_list_lr(width: int, height: int, lst: List[int]) -> List[int]:
    # rlst = [0] * (width * height)
    for y in range(height):
        for x in range((width + 1) // 2):
            xy0 = y * width + x
            xy1 = y * width + height - 1 - x
            # rlst[xy1] = lst[xy0]
            # rlst[xy0] = lst[xy1]
            lst[xy0], lst[xy1] = lst[xy1], lst[xy0]
    return lst

def rotated(size: Pos, data: npt.NDArray[np.int64], num_rotations: int) ->\
        Generator[Tuple[Pos, npt.NDArray[np.int64]], None, None]:
    yield (size, data)
    ctr = 0
    while ctr < num_rotations:
        if ctr % 2 == 1:
            # Rotate 90 degrees
            # rotated: List[int] = rotate_list(size[0], size[1], data)
            # for x in range(size[0]):
                # for y in range(size[1]):
                    # xy = y * size[0] + x
                    # rotated.append(data[xy])
            # data = rotated
            data = np.rot90(data)
            size = size[::-1]
        else:
            # Reflect on Y axis
            # reflect_list_lr(size[0], size[1], data)
            data = np.flip(data, 1)
            # for y in range(size[1]):
                # for x0 in range(size[0] // 2):
                    # x1 = size[0] - 1 - x0
                    # xy0 = y * size[0] + x0
                    # xy1 = y * size[0] + x1
                    # data[xy0], data[xy1] = data[xy1], data[xy0]
        yield (size, data)
        ctr += 1

def valid_overlap(left: Pattern, right: Pattern, offset: Pos) -> bool:
    """TODO test if two patterns can have an adjacency at a given offset
    Note that as adjacencies are symmetric, I can cut the calls to this
    function in half
    """
    pass

def find_adjacencies(size: Pos,
                     data: npt.NDArray[np.int64],
                     pattern_size: Pos,
                     cyclic: bool = False,
                     num_rotations: int = 7) -> Tuple[Dict[PKey, int],
                                                      List[Pattern],
                                                      List[int],
                                                      List[List[TileState]]]:
    """Break apart provided data into patterns of a specified size
    Performs no rotations/reflections
    Returns (Pattern to ID map,
             ID to Pattern map,
             Pattern ID list,
             Adjacency rule list)
    
    TODO this function is not working how I really want it to
    I need to check valid overlaps instead of just positioning of patterns
    Like this, many valid adjacencies are never registered
    Still not sure about rotations though. I'll work on it after
    Would probably reduce backtracking, dunno how speed would change
    """
    # Initialize some vars
    pattern_ids: Dict[PKey, int] = {}
    patterns: List[Pattern] = []
    ids_at: List[int] = []
    array = np.asanyarray(data, dtype=int).reshape(size[::-1])
    
    # Determine all offsets used
    offsets: List[Pos] = gen_offsets(pattern_size)
    
    intersections: List[Dict[PKey, Set[int]]] = [{} for _ in offsets]
    
    # Empty adjacencies list
    adjacencies: List[List[Set[int]]] =\
        [[] for _ in offsets]
    
    # Rotations
    rot_gen = rotated(size, array, num_rotations)
    
    for rot_i in range(num_rotations + 1):
        # Get rotated params
        size, array = next(rot_gen)
        # Cache and ID all patterns
        end_x = size[0] - (0 if cyclic else pattern_size[0] - 1)
        end_y = size[1] - (0 if cyclic else pattern_size[1] - 1)
        for y in range(end_y):
            for x in range(end_x):
                pattern = pattern_at(size, array, pattern_size, (x, y))
                pattern_key = pattern.tobytes()
                if pattern_key not in pattern_ids:
                    patterns.append(pattern)
                    pattern_num = pattern_ids[pattern_key] = len(pattern_ids)
                    ids_at.append(pattern_num)
                    for adj_off in adjacencies:
                        adj_off.append(set())
                    for i, offset in enumerate(offsets):
                        invoff = (-offset[0], -offset[1])
                        segment = offset_pattern(pattern, pattern_size, invoff)
                        segkey = segment.tobytes()
                        intersections[i]\
                            .setdefault(segkey, set())\
                            .add(pattern_num)
                else:
                    ids_at.append(pattern_ids[pattern_key])
        
    # Identify adjacencies
    for pattern_i, pattern in enumerate(patterns):
        for offset_i, offset in enumerate(offsets):
            adjs = adjacencies[offset_i][pattern_i]
            segment = offset_pattern(pattern, pattern_size, offset)
            segkey = segment.tobytes()
            adjs.update(intersections[offset_i][segkey])
        # for y0 in range(end_y):
            # for x0 in range(end_x):
                # xy = y0 * end_x + x0
                # pattern_id = ids_at[xy]
                # for offset_i, offset in enumerate(offsets):
                    # x = x0 + offset[0]
                    # y = y0 + offset[1]
                    # if cyclic:
                        # x %= size[0]
                        # y %= size[1]
                    # else:
                        # if x < 0 or x >= end_x or y < 0 or y >= end_y:
                            # continue # Next offset
                    # xy = y * end_x + x
                    # adj_pattern_id = ids_at[xy]
                    # adjacencies[offset_i][pattern_id].add(adj_pattern_id)
    
    return (pattern_ids, patterns, ids_at, adjacencies)

def patterns_containing(tiles: TileState,
                        patterns: List[Pattern]) -> TileState:
    """Returns a set of which patterns correspond to any of the provided
    tiles
    """
    return set(filter(lambda i: patterns[i][0, 0] in tiles,
                      range(len(patterns))))

@numba.njit(numba.int64[:](numba.int64[:], numba.types.ListType(numba.types.List(numba.int64, reflected=True)), numba.types.ListType(numba.types.List(numba.int64)), numba.int64[:], numba.int64[:, :]), debug=True)
def _fast_wfc_tile(pat_size, adj_list_lst, states_lst, size, offsets):
    """Probably won't even use this because it appears to be slower somehow"""
    history = [(numba.int64(0), {numba.int64(0)}, numba.bool_(False)) for _ in range(0)]
    num_offsets = offsets.shape[0]
    states = [{numba.int64(0)} for _ in range(0)]
    for lst in states_lst:
        states.append(set(lst))
    adj_list = [{numba.int64(0)} for _ in range(0)]
    for lst in adj_list_lst:
        adj_list.append(set(lst))
        
    while True:
        min_ent = math.inf
        min_pos = [0 for _ in range(0)]
        for xy, state in enumerate(states):
            num_pos = len(state)
            if num_pos == 1:
                continue
            elif num_pos == 0:
                resolved = False
                while len(history) > 0:
                    pos, state, choice = history.pop()
                    if choice:
                        valid = state.difference(states[pos])
                        if len(valid) == 0:
                            continue # Keep backtracking to last choice
                        states[pos] = valid
                        state = valid
                        resolved = True
                        break
                    else:
                        states[pos] = state
                if not resolved:
                    raise Exception("Could not collapse wave function")
            if num_pos < min_ent:
                min_ent = len(state)
                min_pos = [xy]
            elif num_pos == min_ent:
                min_pos.append(xy)
        if math.isinf(min_ent):
            break
        _i_xy = random.randint(0, len(min_pos) - 1)
        xy = min_pos[_i_xy]
        state = states[xy]
        
        # Collapse it to a random state
        history.append((xy, state, True))
        _i_xy = random.randint(0, len(state) - 1)
        states[xy] = set([list(state)[_i_xy]])
        
        # Propagate
        frontier = [xy]
        while len(frontier) > 0:
            head = frontier.pop()
            state = states[head]
            for delta_i, delta in enumerate(offsets):
                valid_states = set()
                # This union of all the states is where most of the
                # time is spent. I would like to JIT it but that
                # poses plenty of problems on its own
                for i in state:
                    adj = adj_list[i * num_offsets + delta_i]
                    valid_states.update(adj)
                if len(valid_states) == 0:
                    continue
                oy, ox = divmod(head, size[0])
                x, y = ox + delta[0],\
                       oy + delta[1] # New XY position to check
                if x < 0 or y < 0 or x >= size[0] or y >= size[1]:
                    continue
                n_xy = y * size[0] + x
                other_state = states[n_xy]
                intersect = other_state.intersection(valid_states)
                if len(intersect) == len(other_state):
                    continue
                history.append((n_xy, other_state, False))
                states[n_xy] = intersect
                frontier.append(n_xy)
    return np.array(list(map(lambda s: next(iter(s)), states)), dtype=np.int64)

@dataclass
class WaveFunction:
    tile_classes: Sequence[TileState] # Tiles of each class
    allowed_adjacencies: Sequence[TileRule]
    pattern_size: Pos
    
    def wfc_tile(self,
                 size: Pos,
                 input_states: WFMap,
                 use_jit: Optional[bool]=None) -> List[int]:
        assert len(self.allowed_adjacencies) > 0
        if use_jit is None:
            use_jit = size[0] * size[1] >= 50 * 50
        offsets = gen_offsets(self.pattern_size)
        history: List[History] = []
        states: List[TileState] = list(map(self.tile_classes.__getitem__,
                                           input_states))
        
        start_time = time.time_ns()
        if use_jit:
            _states_numba = numba.typed.List(lsttype=numba.types.ListType(numba.types.List(numba.int64)))
            for state in states:
                _states_numba.append(list(state))
            _adj_numba = numba.typed.List()
            for state_i in range(len(self.allowed_adjacencies[0])):
                for offset_i, offset_rules in enumerate(self.allowed_adjacencies):
                    _adj_numba.append(list(offset_rules[state_i]))
            _psize_nubma = np.array(self.pattern_size, dtype=np.int64)
            _size_numba = np.array(size, dtype=np.int64)
            _offsets_numba = np.array(offsets, dtype=np.int64)
            fast_lst = _fast_wfc_tile(_psize_nubma,
                           _adj_numba,
                           _states_numba,
                           _size_numba,
                           _offsets_numba)
            print('jit_time =', (time.time_ns() - start_time) * 1e-9)
            return list(fast_lst)

        while True:
            # Find a minimum entropy position
            min_ent = float('inf')
            min_pos = []
            for xy, state in enumerate(states):
                num_pos = len(state)
                if num_pos == 1:
                    continue
                elif num_pos == 0:
                    resolved = False
                    while len(history) > 0:
                        pos, state, choice = history.pop()
                        if choice:
                            valid = state.difference(states[pos])
                            if len(valid) == 0:
                                continue # Keep backtracking to last choice
                            states[pos] = valid
                            state = valid
                            resolved = True
                            break
                        else:
                            states[pos] = state
                    if not resolved:
                        raise Exception("Could not collapse wave function")
                if num_pos < min_ent:
                    min_ent = len(state)
                    min_pos = [xy]
                elif num_pos == min_ent:
                    min_pos.append(xy)
            if min_ent == float('inf'):
                break
            xy = random.choice(min_pos)
            state = states[xy]
            
            # Collapse it to a random state
            history.append((xy, state, True))
            states[xy] = set([random.choice(list(state))])
            
            # Propagate
            frontier = deque([xy])
            while len(frontier) > 0:
                head = frontier.pop()
                state = states[head]
                for delta_i, delta in enumerate(offsets):
                    valid_states = set()
                    # This union of all the states is where most of the
                    # time is spent. I would like to JIT it but that
                    # poses plenty of problems on its own
                    for i in state:
                        adj = self.allowed_adjacencies[delta_i][i]
                        valid_states.update(adj)
                    if len(valid_states) == 0:
                        continue
                    oy, ox = divmod(head, size[0])
                    x, y = ox + delta[0],\
                           oy + delta[1] # New XY position to check
                    if x < 0 or y < 0 or x >= size[0] or y >= size[1]:
                        continue
                    n_xy = y * size[0] + x
                    other_state = states[n_xy]
                    intersect = other_state.intersection(valid_states)
                    if len(intersect) == len(other_state):
                        continue
                    history.append((n_xy, other_state, False))
                    states[n_xy] = intersect
                    frontier.append(n_xy)
        print('int_time =', (time.time_ns() - start_time) * 1e-9)
        return list(map(lambda s: next(iter(s)), states))