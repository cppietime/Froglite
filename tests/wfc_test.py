from roguelike.engine import (
    utils
)
from roguelike.world import wfc
from typing import (
    Set, Tuple, Dict
)

import numba # type: ignore
import numpy as np

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
pattern_f, pattern_b, pattern_ids, adj, weights = (wfc.find_adjacencies((w, h), data, pattern, True))
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
gen = wfc.WaveFunction([all_patterns, wfc.patterns_containing({0}, pattern_b)], adj, pattern, weights)
res = gen.wfc_tile((w, h), map_classes)
for i, r in enumerate(res):
    res[i] = pattern_b[r][0][0]
for y in range(h):
    print(res[y*w:y*w+w])