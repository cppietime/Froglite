"""
General world generation
"""
from dataclasses import (
    dataclass,
    field
)
import logging
import random
import sys
import traceback
from typing import (
    cast,
    Any,
    ClassVar,
    Collection,
    Dict,
    Iterable,
    List,
    MutableSequence,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Type,
    TYPE_CHECKING
)

import numpy as np
from numpy import typing as npt

from roguelike.world import (
    bsp,
    cellular,
    dungeon,
    lvl_entity,
    noise,
    wfc
)
from roguelike.engine import (
    assets,
    utils
)
from roguelike.bag import (
    item
)
from roguelike.entities import (
    entity,
    item_entity,
    spawn
)

Pos = Tuple[int, int]
WallGrid = npt.NDArray[np.int32]
TileGrid = npt.NDArray[np.int32]

MAX_SIZE = 50

class WallGenerator(Protocol):
    """Assigns each space in a grid to a certain class of tile"""
    def generate_walls(self, size: Pos) -> WallGrid:
        pass

def parse_wall_generator(source: Dict[str, Any]) -> WallGenerator:
    kind = cast(str, source['kind'])
    if kind == 'wfc':
        filename = cast(str, source['source'])
        size, grid = utils.load_grid(filename)
        pattern_size: Pos = cast(Pos, tuple(source['pattern_size']))
        palette = cast(List[int], source['palette'])
        border_set: Set[int] = set(source.get('border', ()))
        return WallGeneratorWFC(size, grid, pattern_size, palette, border_set)
    elif kind == 'bsp':
        leaf_size = cast(Pos, source['leaf_size'])
        join = cast(bool, source.get('tunnel', True))
        inside = cast(int, source.get('inside', 0))
        outside = cast(int, source.get('outside', 1))
        border_id = cast(int, source.get('border', 1))
        return WallGeneratorBSP(inside, outside, border_id, leaf_size, join)
    elif kind == 'white':
        tiles = source['tiles']
        weights = source.get('weights', (1,) * len(tiles))
        return WallGeneratorWhite(tiles, weights)
    elif kind == 'perlin':
        tiles = source['tiles']
        scale = cast(Pos, tuple(source['scale']))
        rectify = source.get('rectify', True)
        return WallGeneratorPerlin(tiles, scale, rectify)
    else:
        raise ValueError(f'{kind} is not a valid wall generator type')

_wfc_cache: Dict[
    Tuple[Pos, bytes, Pos],
    Tuple[List[npt.NDArray[np.int32]],
          List[List[Set[int]]],
          npt.NDArray[np.int32]]] = {}
class WallGeneratorWFC:
    """A generator that creates walls using WFC
    
    sample_size: 2-tuple of the width and height of the provided sample
    sample: 1D sequence of metaclasses representing input sample
    pattern_size: 2-tuple of width and height of each pattern_size
    class_mappings: sequence containing the tile class of each metaclass
    """
    def __init__(self,
                 sample_size: Pos,
                 sample: WallGrid,
                 pattern_size: Pos,
                 class_mappings: Sequence[int],
                 border: Collection[int]=()):
        self.pattern_size = pattern_size
        key = (sample_size, sample.tobytes(), pattern_size)
        if key in _wfc_cache:
            self.patterns, self.adjacencies, self.weights =\
                _wfc_cache[key]
        else:
            _, self.patterns, __, self.adjacencies, self.weights =\
                wfc.find_adjacencies(sample_size, sample, pattern_size, True)
            _wfc_cache[key] =\
                (self.patterns, self.adjacencies, self.weights)
        all_cls = set(range(len(self.patterns)))
        classes = [all_cls]
        if len(border) > 0:
            border_cls = wfc.patterns_containing(border, self.patterns)
            classes.append(border_cls)
        self.border = border
        self.wave_function = wfc.WaveFunction(classes,
                                              self.adjacencies,
                                              self.pattern_size,
                                              self.weights)
        self.class_mappings = class_mappings
    
    def generate_walls(self, size: Pos) -> WallGrid:
        classes = [0] * (size[0] * size[1])
        if len(self.border) > 0:
            for x in range(size[0]):
                classes[x] = classes[(size[1] - 1) * size[0] + x] = 1
            for y in range(1, size[1] - 1):
                classes[y * size[0]] = classes[y * size[0] + size[0] - 1] = 1
        grid = self.wave_function.wfc_tile(size,
                                           classes,
                                           use_jit=False,
                                           use_weights=True)
        for i, g in enumerate(grid):
            grid[i] = self.class_mappings[self.patterns[g][0, 0]]
        return np.array(grid, dtype=np.int32).reshape(size[::-1])

@dataclass
class WallGeneratorBSP:
    """Generates rectangular rooms by dividing the map into random
    BSPs and creating a room in each one, then optionally joining them
    with orthogonal tunnels
    """
    inside: int
    outside: int
    border: int
    leaf_size: Pos
    join: bool = True
    def generate_walls(self, size: Pos) -> WallGrid:
        return bsp.bsp(size,
                       self.leaf_size,
                       self.inside,
                       self.outside,
                       self.border,
                       self.join)

@dataclass
class WallGeneratorWhite:
    tiles: Sequence[int]
    weights: Sequence[float]
    def generate_walls(self, size: Pos) -> WallGrid:
        return noise.white(size, self.tiles, self.weights)

@dataclass
class WallGeneratorPerlin:
    tiles: Sequence[int]
    scale: Tuple[float, float]
    rectify: bool
    def generate_walls(self, size: Pos) -> WallGrid:
        dx = size[0] / self.scale[0]
        dy = size[1] / self.scale[1]
        off_x = random.random() * 1000
        off_y = random.random() * 1000
        return noise.perlin(size,
                            (dx, dy),
                            self.tiles,
                            (off_x, off_y),
                            self.rectify)

class WallFeature(Protocol):
    """Modifies generated walls"""
    def apply_feature(self, walls: WallGrid) -> None:
        """Modifies walls in-place"""
        pass

def parse_wall_feature(source: Dict[str, Any]) -> WallFeature:
    kind = cast(str, source['kind'])
    if kind == 'dla':
        num = cast(int, source['num'])
        out = cast(bool, source.get('out', False))
        sticky = cast(int, source['sticky'])
        return WallFeatureDLA(num, out, sticky)
    elif kind == 'join':
        passables = set(source['passable'])
        inside = source['inside']
        outside = source['outside']
        border = source.get('border', outside)
        return WallFeatureJoin(passables, inside, outside, border)
    elif kind == 'cellular':
        clear_below = source['clear_below']
        fill_from = source['fill_from']
        clear_with = source['clear_with']
        fill_with = source['fill_with']
        full = set(source['full'])
        iterations = source['iterations']
        corners = source.get('corners', True)
        return WallFeatureCA(
            clear_below, fill_from, clear_with,
            fill_with, full, iterations, corners)
    else:
        raise ValueError(f'{kind} is not a valid feature type')

@dataclass
class WallFeatureDLA:
    """Applies an erosion style effect with diffusion-limited aggregation"""
    num_shots: int
    outward: bool
    sticky: int
    def apply_feature(self, walls: WallGrid) -> None:
        for _ in range(self.num_shots):
            if self.outward:
                passable = list((walls == self.sticky).flatten())
                group = utils.group(cast(Pos, walls.shape[::-1]), passable)[0]
                position = random.choice(list(group))
            else:
                center = walls.shape[1] // 2, walls.shape[0] // 2
                if random.randint(0, 1) == 0:
                    # Top/bottom
                    x = random.randint(0, walls.shape[1] - 1)
                    y = [0, walls.shape[0] - 1][random.randint(0, 1)]
                else:
                    # Left/right
                    y = random.randint(0, walls.shape[0] - 1)
                    x = [0, walls.shape[1] - 1][random.randint(0, 1)]
                position = (x, y)
                dist = utils.diag_dist(position, center)
            while True:
                direction = random.choice(list(utils.CardinalDirections))
                x, y = position[0] + direction.value[0],\
                        position[1] + direction.value[1]
                if self.outward:
                    stuck = False
                    if x == 0 or y == 0 or x >= walls.shape[1] - 1\
                            or y >= walls.shape[0] - 1:
                        stuck = True
                    else:
                        current = walls[y, x]
                        stuck = current != self.sticky
                    if stuck:
                        if x >= 0 and y >= 0 and x < walls.shape[1]\
                                and y < walls.shape[0]:
                            walls[y, x] = self.sticky
                        break
                else:
                    if x < 0 or y < 0 or x >= walls.shape[1]\
                            or y >= walls.shape[0]:
                        continue
                    n_dist = utils.diag_dist((x, y), center)
                    if n_dist > dist and n_dist > 0:
                        continue
                    dist = n_dist
                    current = walls[y, x]
                    if current == self.sticky or n_dist == 0:
                        walls[position[::-1]] = self.sticky
                        break
                position = x, y

@dataclass
class WallFeatureJoin:
    """Ensures connectedness between all passable groups of contiguous
    tiles. Basically makes sure the player can reach everywhere in the
    map.
    Superfluous on BSP maps where join is True
    """
    passable_classes: Set[int]
    inside: int
    outside: int
    border: int
    def apply_feature(self, walls: WallGrid) -> None:
        while True:
            passable = [i in self.passable_classes for i in walls.flatten()]
            groups = utils.group(cast(Pos, walls.shape[::-1]), passable)
            if len(groups) < 2:
                break
            i = random.randint(0, len(groups) - 2)
            j = random.randint(i + 1, len(groups) - 1)
            i_pos = random.choice(list(groups[i]))
            j_pos = random.choice(list(groups[j]))
            bsp.tunnel(walls, i_pos, j_pos,
                       self.inside, self.outside, self.border)

@dataclass
class WallFeatureCA:
    """Runs a cellular automaton
    """
    clear_below: int
    fill_from: int
    clear_with: int
    fill_with: int
    full: Set[int]
    iterations: int
    corners: bool
    def apply_feature(self, walls: WallGrid) -> None:
        cellular.run(
            walls, self.clear_below, self.fill_from,
            self.clear_with, self.fill_with, self.full,
            self.iterations, self.corners)

class TileGenerator(Protocol):
    """Handles populating a grid with actual tiles"""
    def assign_tiles(self, walls: WallGrid) -> TileGrid:
        pass

def parse_tile_generator(source: Dict[str, Any]) -> TileGenerator:
    kind = cast(str, source['kind'])
    if kind == 'pass':
        return TileGeneratorPassThru()
    elif kind == 'white':
        classes = source['classes']
        return TileGeneratorWhiteNoise(classes)
    else:
        raise ValueError('f{kind} is not a valid tile generator type')

class TileGeneratorPassThru:
    """Just converts tile classes to tiles"""
    def assign_tiles(self, walls: WallGrid) -> TileGrid:
        return cast(TileGrid, walls)

class TileGeneratorWhiteNoise:
    """Selects a random tile for each class, with weights"""
    def __init__(self, classes: Iterable[Iterable[Tuple[int, float]]]):
        self.classes: List[Tuple[npt.NDArray[np.int32],
                                 npt.NDArray[np.float64]]] = []
        for pairs in classes:
            tiles_lst = []
            prob_lst = []
            for tile, prob in pairs:
                tiles_lst.append(tile)
                prob_lst.append(prob)
            tiles = np.array(tiles_lst, dtype=np.int32)
            probs = np.array(prob_lst, dtype=float)
            self.classes.append((tiles, probs/probs.sum()))
    
    def assign_tiles(self, walls: WallGrid) -> TileGrid:
        tiles = np.zeros(walls.shape, dtype=np.int32)
        for y in range(tiles.shape[0]):
            for x in range(tiles.shape[1]):
                clazz = self.classes[walls[y, x]]
                tiles[y, x] = np.random.choice(clazz[0], p=clazz[1])
        return tiles

Predicates = Sequence[Tuple[str, str, Any]]
    
@dataclass
class ExitPlacer:
    key: Optional[str]
    weight: float
    predicates: Predicates
    count_range: Pos

def parse_exits(source: List[Dict[str, Any]]) -> List[ExitPlacer]:
    exits: List[ExitPlacer] = []
    for d in source:
        key = d.get('key', None)
        weight = d.get('weight', 1)
        predicates = cast(Predicates,
                          tuple(map(tuple, d.get('predicates', []))))
        crange = cast(Pos, tuple(d.get('count', [1, 1])))
        exits.append(ExitPlacer(key, weight, predicates, crange))
    return exits

@dataclass
class WorldGenerator:
    """Holds the data for generating worlds"""
    # Generation models
    wall_generator: WallGenerator
    wall_features: Iterable[WallFeature]
    tile_generator: TileGenerator
    tile_list: MutableSequence[dungeon.DungeonTile]
    populator: spawn.Populator
    exits: Sequence[ExitPlacer]
    max_boredom: float = 16
    vignette_color: Tuple[float, float, float, float] = (.2, .2, .2, 1)
    border: int = -1
    music: Optional[str] = None
    
    def generate_world(self,
                       size: Pos,
                       **kwargs)\
            -> dungeon.DungeonMapSpawner:
        logging.debug(f'Generating a new map that is {size[0]}x{size[1]}')
        # Generate wall classes
        walls = self.wall_generator.generate_walls(size)
        
        # Apply optional features
        for feature in self.wall_features:
            feature.apply_feature(walls)
        
        # Fill in tiles
        tiles = self.tile_generator.assign_tiles(walls)
        
        # Make it fun
        passable_ids = set(map(lambda x: x[0],
                           filter(lambda x: x[1].passable,
                                  enumerate(self.tile_list))))
        passable_vec = np.vectorize(passable_ids.__contains__)
        passable = passable_vec(tiles)

        costs = np.where(passable, 1, np.inf)
        groups = utils.group(size, list(passable.flatten()))
        group_no = max(enumerate(groups), key=lambda x: len(x[1]))[0]
        group = groups[group_no]
        player_pos = random.choice(list(group))
        
        spawner = dungeon.DungeonMapSpawner(size,
                                            self.tile_list,
                                            player_pos,
                                            tile_map=list(tiles.flatten()),
                                            spawns=[],
                                            vignette_color=self.vignette_color,
                                            border=self.border,
                                            **kwargs)
        
        dists = utils.populate_djikstra(costs, (player_pos,))
        furthest_away = cast(Tuple[int, int], divmod(
            np.where(np.isinf(dists) | ~passable,
                     -np.inf, dists).argmax(),
            size[0])[::-1])
        
        key_item_nm: Optional[str] = None
        key_item: Optional[item.BaseItem] = None
        key_count = 0
        choices = tuple(\
            filter(\
                lambda x: spawn.eval_preds(x.predicates), self.exits))
        if len(choices) > 0:
            weights = np.array([ex.weight for ex in choices], dtype=float)
            choice = np.random.choice(choices, p=weights/weights.sum()) # type: ignore
            key_item_nm = choice.key
            key_count = random.randint(*choice.count_range)
        if key_item_nm is not None:
            key_item = item.items[key_item_nm]
            logging.debug(f'Level will require {key_item_nm} x{key_count}')
            for _ in range(key_count):
                spawner.spawns.append((
                    furthest_away, item_entity.KeyEntity,
                    {'item': key_item_nm,
                     'needed': key_count}))
                hot_path = utils.trace_djikstra(furthest_away, dists)
                dists = utils.populate_djikstra(costs, hot_path, dists)
                furthest_away = cast(Tuple[int, int], divmod(
                    np.where(np.isinf(dists) | ~passable,
                             -np.inf, dists).argmax(),
                    size[0])[::-1])
        logging.debug(f'Exit is at {furthest_away}')
        w, h = size
        w = min(w + random.randint(0, 1), MAX_SIZE)
        h = min(h + random.randint(0, 1), MAX_SIZE)
        spawner.spawns.append((furthest_away, lvl_entity.LadderEntity,
                               {'size': (w, h), 'key_item': key_item,
                                'key_count': key_count}))
        # TODO generate main goal(i.e. exit to next level)
        hot_path = utils.trace_djikstra(furthest_away, dists)
        dists = utils.populate_djikstra(costs, hot_path, dists)
        
        blocking = utils.clear_blockage(dists)
        self.populator.reset_counts()
        while True:
            boring_pos = cast(Tuple[int, int], divmod(
                np.where(np.isinf(dists)\
                            | ~passable\
                            | blocking,
                         -np.inf, dists).argmax(),
                size[0])[::-1])
            boredom = dists[boring_pos[::-1]]
            if not np.isfinite(boredom) or boredom < self.max_boredom:
                break
            chosen_spawn = self.populator.populate(boring_pos)
            if chosen_spawn is None:
                break
            spawner.spawns.append(chosen_spawn)
            fun_path = utils.trace_djikstra(boring_pos, dists)
            dists = utils.populate_djikstra(costs, fun_path, dists)
        if self.music is not None:
            assets.Sounds.instance.play_music(self.music)
        return spawner
    
world_generators: Dict[str, WorldGenerator] = {}
    
def init_generators() -> None:
    for name, value in assets.residuals['worldgen'].items():
        wall_generator = parse_wall_generator(value['wall'])
        features = []
        for feature_dict in value.get('features', []):
            features.append(parse_wall_feature(feature_dict))
        tile_generator = parse_tile_generator(value['tile'])
        tile_list = list(map(dungeon.tiles.__getitem__, value['tiles']))
        spawns = spawn.parse_spawns(value.get('spawns', []))
        exits = parse_exits(value.get('exits', []))
        boredom = value.get('boredom', 16)
        vignette = cast(Tuple[float, float, float, float],
                        tuple(value.get('vignette', (.2, .2, .2, 1))))
        border = value.get('border', -1)
        music = value.get('music', None)
        world_generators[name] = WorldGenerator(
            wall_generator=wall_generator,
            wall_features=features,
            tile_generator=tile_generator,
            tile_list=tile_list,
            populator=spawns,
            exits=exits,
            max_boredom=boredom,
            vignette_color=vignette,
            border=border,
            music=music)
