import random

from roguelike.world import noise

offset = (random.random() * 10, random.random() * 10)

print(noise.perlin((20, 20), (11, 11), (0, 1, 2, 3, 4), offset, rectify=True))