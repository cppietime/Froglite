import logging
import random
from typing import (
    List,
    Set,
    Tuple
)

import numpy as np
import numpy.typing as npt

Pos = Tuple[int, int]
Box = List[int] # Mutable so we can translate
IArray = npt.NDArray[np.int32]

def bsp(size: Pos,
        min_room_size: Pos,
        inside: int,
        outside: int,
        border: int,
        join: bool) -> IArray:
    width, height = size
    array = np.full((height, width), outside, dtype=np.int32)
    boxes = partition(size, min_room_size)
    for box in boxes:
        logging.debug(f'Box: {box}')
        for y in range(box[3]):
            for x in range(box[2]):
                if x == 0 or y == 0 or x == box[2] - 1 or y == box[3] - 1:
                    tile = border
                else:
                    tile = inside
                array[y + box[1], x + box[0]] = tile
    if join:
        groups: List[Set[Pos]] = []
        for box in boxes:
            center = box[0] + box[2] // 2, box[1] + box[3] // 2
            groups.append({center})
        while len(groups) > 1:
            i = random.randint(0, len(groups) - 2)
            j = random.randint(i + 1, len(groups) - 1)
            set_i = groups[i]
            set_j = groups[j]
            box_i = random.choice(list(set_i))
            box_j = random.choice(list(set_j))
            tunnel(array, box_i, box_j, inside, outside, border)
            set_i.update(set_j)
            groups.pop(j)
    return array

def partition(size: Pos,
              min_room_size: Pos) -> List[Box]:
    wide_enough = size[0] > min_room_size[0] * 2
    tall_enough = size[1] > min_room_size[1] * 2
    if wide_enough:
        if tall_enough:
            # choose a random direction
            horizontal = random.randint(0, 1) == 0
        else:
            horizontal = True
    elif tall_enough:
        horizontal = False
    else:
        width = random.randint(min_room_size[0], size[0])
        height = random.randint(min_room_size[1], size[1])
        x = random.randint(0, size[0] - width)
        y = random.randint(0, size[1] - height)
        return [[x, y, width, height]]
    if horizontal:
        split = random.randint(min_room_size[0], size[0] - min_room_size[0])
        left = partition((split, size[1]), min_room_size)
        right = partition((size[0] - split, size[1]), min_room_size)
        for box in right:
            box[0] += split
        return left + right
    else:
        split = random.randint(min_room_size[1], size[1] - min_room_size[1])
        top = partition((size[0], split), min_room_size)
        bottom = partition((size[0], size[1] - split), min_room_size)
        for box in bottom:
            box[1] += split
        return top + bottom

def tunnel(array: IArray,
           from_: Pos,
           to: Pos,
           inside: int,
           outside: int,
           border: int) -> None:
    logging.debug(f'Tunneling from {from_} to {to}')
    x_first = random.randint(0, 1) == 0
    x = from_[0]
    if x_first:
        x0 = min(from_[0], to[0])
        x1 = max(from_[0], to[0])
        for x in range(x0, x1 + 1):
            array[from_[1], x] = inside
            if from_[1] > 0\
                    and array[from_[1] - 1, x] == outside:
                array[from_[1] - 1, x] = border
            if from_[1] + 1 < array.shape[0]\
                    and array[from_[1] + 1, x] == outside:
                array[from_[1] + 1, x] = border
        x = to[0]
    y0 = min(from_[1], to[1])
    y1 = max(from_[1], to[1])
    for y in range(y0, y1 + 1):
        array[y, x] = inside
        if x > 0 and array[y, x - 1] == outside:
            array[y, x - 1] = border
        if x + 1 < array.shape[1] and array[y, x + 1] == outside:
            array[y, x + 1] = border
    if not x_first:
        x0 = min(from_[0], to[0])
        x1 = max(from_[0], to[0])
        for x in range(x0, x1 + 1):
            array[to[1], x] = inside
            if to[1] > 0\
                    and array[to[1] - 1, x] == outside:
                array[to[1] - 1, x] = border
            if to[1] + 1 < array.shape[0]\
                    and array[to[1] + 1, x] == outside:
                array[to[1] + 1, x] = border