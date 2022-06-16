"""Actually tests Djikstra, too"""
import math

from roguelike.world import dungeon
from roguelike.engine import utils

floor = dungeon.DungeonTile(None, True)
wall = dungeon.DungeonTile(None, False)

start = (3, 2)
end = (10, 4)

map_chrs = [
"XXXXXXXXXXXX",
"XOOOOOOOOOOX",
"XOOOOOOOOOOX",
"XOXXXXXXXXXX",
"XOOOOOOOOXOX",
"XOOOOOOOOOOX",
"XXXXXXXXXXXX"
]
dmap = dungeon.DungeonMap((len(map_chrs[0]), len(map_chrs)), [floor, wall])
costs = []
for row in map_chrs:
    for char in row:
        if char == 'X':
            costs.append(float('inf'))
        else:
            costs.append(1)
for y, line in enumerate(map_chrs):
    for x, char in enumerate(line):
        if (x, y) == start:
            print('S', end='')
        elif (x, y) == 'end':
            print('E', end='')
        else:
            print(char, end='')
        dmap.tile_map.append(0 if char == 'O' else 1)
    print()

# steps = utils.a_star((10, 10), costs, (3, 2), (10, 4), max_cost=None)
steps = dmap.a_star((3, 2), (10, 4))
print(steps)

if steps is not None:
    steps = set(steps)

    for y, line in enumerate(map_chrs):
        for x, char in enumerate(line):
            if (x, y) == start:
                print('S', end='')
            elif (x, y) == end:
                print('E', end='')
            elif (x, y) in steps:
                print('.', end='')
            else:
                print(char, end='')
        print()

start = ((2, 2),)
dj = (utils.populate_djikstra(dmap.size, costs, start))
for y in range(len(map_chrs)):
    line = dj[y*len(map_chrs[0]) : (y+1)*len(map_chrs[0])]
    for c in line:
        if not math.isfinite(c):
            print('---', end=' ')
        else:
            print(f'{c:3}', end=' ')
    print()
print()

start = ((10, 4),)
dj = utils.populate_djikstra(dmap.size, costs, start, dj)
for y in range(len(map_chrs)):
    line = dj[y*len(map_chrs[0]) : (y+1)*len(map_chrs[0])]
    for c in line:
        if not math.isfinite(c):
            print('---', end=' ')
        else:
            print(f'{c:3}', end=' ')
    print()

group_chrs = [
'XXXXXXXXXX',
'XOOOXOOOOX',
'XOOOXOOOOX',
'XOOOXOOOOX',
'XXXXXXXXXX',
'XOXOOOOOOX',
'XOOOOXXXXX',
'XXXXXXOOOX',
'XXXXXXOOOX',
'XXXXXXXXXX'
]
size = (len(group_chrs[0]), len(group_chrs))
groups = (utils.group(size, tuple(map(lambda x: x=='O', ''.join(group_chrs)))))
print(groups)
for i, group in enumerate(groups):
    for pos in group:
        x, y = pos
        line = group_chrs[y]
        group_chrs[y] = line[:x] + str(i) + line[x+1:]
print('\n'.join(group_chrs))