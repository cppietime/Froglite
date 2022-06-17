"""
General world generation
"""
from dataclasses import dataclass
import random
from typing import (
    cast,
    Any,
    ClassVar,
    Collection,
    Dict,
    Iterable,
    List,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TYPE_CHECKING
)

import numpy as np
from numpy import typing as npt

from roguelike.world import (
    dungeon,
    wfc,
    lvl_entity
)
from roguelike.engine import (
    assets,
    utils
)

Pos = Tuple[int, int]
WallGrid = npt.NDArray[np.int32]
TileGrid = npt.NDArray[np.int32]

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
        border: Set[int] = set(source.get('border', ()))
        return WallGeneratorWFC(size, grid, pattern_size, palette, border)
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

class WallFeature(Protocol):
    """Modifies generated walls"""
    def apply_feature(self, walls: WallGrid) -> None:
        """Modifies walls in-place"""
        pass

class TileGenerator(Protocol):
    """Handles populating a grid with actual tiles"""
    def assign_tiles(self, walls: WallGrid) -> TileGrid:
        pass

def parse_tile_generator(source: Dict[str, Dict[str, Any]]) -> TileGenerator:
    kind = cast(str, source['kind'])
    if kind == 'pass':
        return TileGeneratorPassThru()
    else:
        raise ValueError('f{kind} is not a valid tile generator type')

class TileGeneratorPassThru:
    def assign_tiles(self, walls: WallGrid) -> TileGrid:
        return cast(TileGrid, walls)

@dataclass
class WorldGenerator:
    """Holds the data for generating worlds"""
    # Generation models
    wall_generator: WallGenerator
    wall_features: Iterable[WallFeature]
    tile_generator: TileGenerator
    tile_list: Sequence[dungeon.DungeonTile]
    max_boredom: float = 16
    vignette_color: Tuple[float, float, float, float] = (.2, .2, .2, 1)
    border: int = -1
    
    def generate_world(self,
                       size: Pos,
                       **kwargs)\
            -> dungeon.DungeonMapSpawner:
        # Generate wall classes
        walls = self.wall_generator.generate_walls(size)
        for feature in self.wall_features:
            feature.apply_feature(walls)
        
        # Fill in tiles
        # tiles = self.tile_generator(self, size, walls)
        tiles = walls
        
        # Make it fun
        passable_ids = set(map(lambda x: x[0],
                           filter(lambda x: x[1].passable,
                                  enumerate(self.tile_list))))
        passable_vec = np.vectorize(passable_ids.__contains__)
        passable = passable_vec(tiles)

        costs = np.where(passable, 1, np.inf)
        groups = utils.group(size, list(passable.flatten()))
        # TODO group connection/culling policy
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
        
        spawner.spawns.append((furthest_away, lvl_entity.LadderEntity,
                               {'size': size}))
        # TODO generate main goal(i.e. exit to next level)
        hot_path = utils.trace_djikstra(furthest_away, dists)
        dists = utils.populate_djikstra(costs, hot_path, dists)
        
        blocking = utils.clear_blockage(dists)
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
            # TODO while there are useless tiles: place something cool at
            # the furthest useless tile and update djikstra costs
            fun_path = utils.trace_djikstra(boring_pos, dists)
            dists = utils.populate_djikstra(costs, fun_path, dists)

        return spawner
    
world_generators: Dict[str, WorldGenerator] = {}
    
def init_generators() -> None:
    for name, value in assets.residuals['worldgen'].items():
        wall_generator = parse_wall_generator(value['wall'])
        # TODO parse features
        tile_generator = parse_tile_generator(value['tile'])
        tile_list = list(map(dungeon.tiles.__getitem__, value['tiles']))
        boredom = value.get('boredom', 16)
        vignette = cast(Tuple[float, float, float, float],
                        tuple(value.get('vignette', (.2, .2, .2, 1))))
        border = value.get('border', -1)
        world_generators[name] = WorldGenerator(wall_generator,
                                                (),
                                                tile_generator,
                                                tile_list,
                                                boredom,
                                                vignette,
                                                border)
