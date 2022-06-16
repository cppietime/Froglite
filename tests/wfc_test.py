from roguelike.engine import (
    utils
)
from roguelike.world import wfc
from typing import (
    Set, Tuple, Dict
)

import numba # type: ignore
import numpy as np

# return_set = numba.types.DictType(numba.types.int64, numba.types.int64)
# input_set = numba.types.DictType(numba.types.int64, numba.types.int64)
# input_set_list = numba.types.ListType(input_set)
# @numba.njit(return_set(input_set, input_set_list, input_set))
# def agg_sets(initial_set, by_dir, state_set):
    # empty_set = numba.typed.Dict.empty(numba.int64, numba.int64)
    # # empty_set[-1] = 0
    # for state_no in state_set:
        # for key, val in by_dir[state_no].items():
            # empty_set[key] = val
        # # empty_set.update(by_dir[state_no])
    # return empty_set

# initial_set = numba.typed.Dict()
# initial_set.update({0: 0})
# input_set_list = numba.typed.List([numba.typed.List([
    # numba.typed.Dict.empty(numba.int64, numba.int64) for _ in range(2)
# ]) for __ in range(2)])
# print('Created')
# print(input_set_list)
# for pisl in input_set_list:
    # print(f'{pisl=}')
    # for isl in pisl:
        # print(f'{isl=}')
        # isl.update({9: 0, 8: 0})
# state_set = numba.typed.Dict()
# state_set.update({0: 0, 1: 0})
# print(agg_sets(initial_set, input_set_list[0], state_set))
# exit()

# classes = [
    # {0, 1, 2, 3}
# ]

# rules = [
    # { #0
        # utils.CardinalDirections.UP.value:    {0, 3},
        # utils.CardinalDirections.DOWN.value:  {0, 1},
        # utils.CardinalDirections.LEFT.value:  {0, 1, 2, 3},
        # utils.CardinalDirections.RIGHT.value: {0, 1, 2, 3},
        # (-1, -1):                             {0, 1, 2, 3},
        # (-1, 1):                              {0, 1, 2, 3},
        # (1, 1):                               {0, 1, 2, 3},
        # (1, -1):                              {0, 1, 2, 3}
    # },
    # { #1
        # utils.CardinalDirections.UP.value:    {0},
        # utils.CardinalDirections.DOWN.value:  {2},
        # utils.CardinalDirections.LEFT.value:  {0},
        # utils.CardinalDirections.RIGHT.value: {0},
        # (-1, -1):                             {0},
        # (-1, 1):                              {0},
        # (1, 1):                               {0},
        # (1, -1):                              {0}
    # },
    # { #2
        # utils.CardinalDirections.UP.value:    {1, 2},
        # utils.CardinalDirections.DOWN.value:  {2, 3},
        # utils.CardinalDirections.LEFT.value:  {0},
        # utils.CardinalDirections.RIGHT.value: {0},
        # (-1, -1):                             {0},
        # (-1, 1):                              {0},
        # (1, 1):                               {0},
        # (1, -1):                              {0}
    # },
    # { #3
        # utils.CardinalDirections.UP.value:    {2},
        # utils.CardinalDirections.DOWN.value:  {0},
        # utils.CardinalDirections.LEFT.value:  {0},
        # utils.CardinalDirections.RIGHT.value: {0},
        # (-1, -1):                             {0},
        # (-1, 1):                              {0},
        # (1, 1):                               {0},
        # (1, -1):                              {0}
    # }
# ]

# w, h = 10, 10
# gen = world_gen.WaveFunction(classes, rules, (2, 2))
# res = gen.wfc_tile((w, h), [0 for _ in range(w * h)])
# for y in range(h):
    # print(res[y*w:y*w+w])

w, h = 11, 11
pattern = (3, 3)
data = [
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1,
0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 1,
0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 1,
0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 1,
0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 1,
0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 1,
0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1,
]
data = np.asanyarray(data, dtype=int).reshape((h, w))
pattern_f, pattern_b, pattern_ids, adj = (wfc.find_adjacencies((w, h), data, pattern, True))
print(pattern_f)
print(list(enumerate(pattern_b)))
print(pattern_ids)
for y in range(h):
    print(pattern_ids[y*(w):(y+1)*(w)])
for i, a in enumerate(adj):
    print(f'\n{i}:')
    print(pattern_b[i])
    print(a)

w, h = 20, 20
floor = 0
wall = 1
ceiling = [wall] * w
wall = [wall] + [floor] * (w - 2) + [wall]
map_classes = ceiling + wall * (h - 2) + ceiling
all_patterns = set(pattern_f.values())
gen = wfc.WaveFunction([all_patterns, wfc.patterns_containing({0}, pattern_b)], adj, pattern)
res = gen.wfc_tile((w, h), map_classes)
for i, r in enumerate(res):
    res[i] = pattern_b[r][0][0]
for y in range(h):
    print(res[y*w:y*w+w])