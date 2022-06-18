"""
General world generation
"""
from dataclasses import (
    dataclass,
    field
)
import logging
import random
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
    dungeon,
    wfc,
    lvl_entity
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
    item_entity
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
        border_set: Set[int] = set(source.get('border', ()))
        return WallGeneratorWFC(size, grid, pattern_size, palette, border_set)
    elif kind == 'bsp':
        leaf_size = cast(Pos, source['leaf_size'])
        join = cast(bool, source.get('tunnel', True))
        inside = cast(int, source.get('inside', 0))
        outside = cast(int, source.get('outside', 1))
        border_id = cast(int, source.get('border', 1))
        return WallGeneratorBSP(inside, outside, border_id, leaf_size, join)
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
    else:
        raise ValueError(f'{kind} is not a valid feature type')

class WallFeatureDLA:
    def __init__(self, num_shots: int, outward: bool, sticky: int):
        self.num_shots = num_shots
        self.outward = outward
        self.sticky = sticky
    
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
                    if x == 0 or y == 0 or x == walls.shape[1] - 1\
                            or y == walls.shape[0] - 1:
                        stuck = True
                    else:
                        current = walls[y, x]
                        stuck = current != self.sticky
                    if stuck:
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
    def assign_tiles(self, walls: WallGrid) -> TileGrid:
        return cast(TileGrid, walls)

class TileGeneratorWhiteNoise:
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

def eval_preds(predicates: Predicates) -> bool:
    for varname, comparison, value in predicates:
        variable = assets.variables[varname]
        if comparison == '=' and variable != value:
            return False
        elif comparison == '!=' and variable == value:
            return False
        elif comparison == '>' and variable <= value:
            return False
        elif comparison == '>=' and variable < value:
            return False
        elif comparison == '<' and variable >= value:
            return False
        elif comparison == '<=' and variable > value:
            return False
    return True
    
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
class Spawn:
    spawn_class: Type[entity.Entity]
    params: Dict[str, Any]
    limit: int
    weight: float
    difficulty_range: Pos
    predicates: Predicates

@dataclass
class Populator:
    spawns: Sequence[Spawn]
    so_far: List[int] = field(init=False)
    def __post_init__(self):
        self.reset_counts()
    
    def reset_counts(self) -> None:
        self.so_far = [0] * len(self.spawns)
    
    """Puts something optional and interesting into a level"""
    def populate(self, pos: Pos) -> Optional[Tuple[Pos, type, Dict[str, Any]]]:
        options = [i for i, spn in enumerate(self.spawns)\
            if (self.so_far[i] < spn.limit or spn.limit < 0)\
            and eval_preds(spn.predicates)]
        if len(options) == 0:
            return None
        weights = np.array([self.spawns[i].weight for i in options],
                           dtype=float)
        choice = np.random.choice(options, p=weights/weights.sum())
        spawn = self.spawns[choice]
        self.so_far[choice] += 1
        return (pos, spawn.spawn_class, spawn.params)

def parse_spawns(source: List[Dict[str, Any]]) -> Populator:
    spawns: List[Spawn] = []
    for spawn_d in source:
        class_name = cast(str, spawn_d.pop('class'))
        clazz = entity.entities[class_name]
        anim_name = cast(Optional[str], spawn_d.pop('animation', None))
        limit = spawn_d.pop('limit', -1)
        weight = spawn_d.pop('weight', 1)
        diff = cast(Pos, tuple(spawn_d.pop('difficulty', [-1, -1])))
        preds = cast(Predicates,
                     tuple(map(tuple, spawn_d.pop('predicates', []))))
        params = dict(spawn_d)
        if anim_name is not None:
            if anim_name in assets.Animations.instance.animations:
                params['anim'] =\
                    assets.Animations.instance.animations[anim_name]
            elif anim_name in assets.Sprites.instance.sprites:
                params['anim'] = assets.Sprites.instance.sprites[anim_name]
            else:
                raise ValueError(f'{anim_name} is not a recognized asset')
        spawns.append(Spawn(clazz, params, limit, weight, diff, preds))
    return Populator(spawns)

@dataclass
class WorldGenerator:
    """Holds the data for generating worlds"""
    # Generation models
    wall_generator: WallGenerator
    wall_features: Iterable[WallFeature]
    tile_generator: TileGenerator
    tile_list: MutableSequence[dungeon.DungeonTile]
    populator: Populator
    exits: Sequence[ExitPlacer]
    max_boredom: float = 16
    vignette_color: Tuple[float, float, float, float] = (.2, .2, .2, 1)
    border: int = -1
    
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
        choices = tuple(filter(lambda x: eval_preds(x.predicates), self.exits))
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
                    {'item': key_item_nm, 'anim': key_item.icon,
                     'needed': key_count}))
                hot_path = utils.trace_djikstra(furthest_away, dists)
                dists = utils.populate_djikstra(costs, hot_path, dists)
                furthest_away = cast(Tuple[int, int], divmod(
                    np.where(np.isinf(dists) | ~passable,
                             -np.inf, dists).argmax(),
                    size[0])[::-1])
        logging.debug(f'Exit is at {furthest_away}')
        spawner.spawns.append((furthest_away, lvl_entity.LadderEntity,
                               {'size': size, 'key_item': key_item,
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
            spawn = self.populator.populate(boring_pos)
            if spawn is None:
                break
            spawner.spawns.append(spawn)
            fun_path = utils.trace_djikstra(boring_pos, dists)
            dists = utils.populate_djikstra(costs, fun_path, dists)
        logging.debug(f'List of spawns = {spawner.spawns}')
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
        spawns = parse_spawns(value.get('spawns', []))
        exits = parse_exits(value.get('exits', []))
        boredom = value.get('boredom', 16)
        vignette = cast(Tuple[float, float, float, float],
                        tuple(value.get('vignette', (.2, .2, .2, 1))))
        border = value.get('border', -1)
        world_generators[name] = WorldGenerator(
            wall_generator=wall_generator,
            wall_features=features,
            tile_generator=tile_generator,
            tile_list=tile_list,
            populator=spawns,
            exits=exits,
            max_boredom=boredom,
            vignette_color=vignette,
            border=border)
