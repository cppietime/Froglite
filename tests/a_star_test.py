from roguelike.states import dungeon

floor = dungeon.DungeonTile(None, True)
wall = dungeon.DungeonTile(None, False)

start = (3, 2)
end = (10, 4)

dmap = dungeon.DungeonMap((40, 40), [floor, wall])
map_chrs = [
"XXXXXXXXXXXX",
"XOOOOOOOOOOX",
"XOOOOOOOOOOX",
"XOXXXXXXXXXX",
"XOOOOOOOOXOX",
"XOOOOOOOOOOX",
"XXXXXXXXXXXX"
]
for y, line in enumerate(map_chrs):
    for x, char in enumerate(line):
        if (x, y) == start:
            print('S', end='')
        elif (x, y) == 'end':
            print('E', end='')
        else:
            print(char, end='')
        dmap.tile_map[(x, y)] = 0 if char == 'O' else 1
    print()

steps = dmap.a_star((3, 2), (10, 4), maxdist=15)
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