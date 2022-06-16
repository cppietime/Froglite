"""
General world generation
"""
from typing import (
    Iterable,
    Protocol,
    Sequence,
    Tuple,
    TYPE_CHECKING
)

from roguelike.world import (
    dungeon,
    wfc
)
from roguelike.engine import (
    utils
)

Pos = Tuple[int, int]
WallGird = Sequence[int]
TileGrid = Sequence[int]

class WallGenerator(Protocol):
    """Assigns each space in a grid to a certain class of tile"""
    def generate_walls(self, size: Pos) -> WallGrid:
        pass

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
                 class_mappings: Sequence[int]):
        self.pattern_size = pattern_size
        _, self.patterns, __, self.adjacencies =\
            wfc.find_adjacencies(sample_size, sample, pattern_size, True)
        self.wave_function = wfc.WaveFunction([set(range(len(self.patterns)))],
                                              self.adjacencies,
                                              self.pattern_size)
        self.class_mappings = class_mappings
    
    def generate_walls(self, size: Pos) -> WallGrid:
        grid = self.wave_function.wfc_tile(size, [0] * (size[0] * size[1]))
        for i, g in grid:
            grid[i] = self.class_mappings[g]
        return grid

class WallFeature(Protocol):
    """Modifies generated walls"""
    def apply_feature(self, size: Pos, walls: WallGrid) -> None:
        """Modifies walls in-place"""
        pass

class TileGenerator(Protocol):
    """Handles populating a grid with actual tiles"""
    def assign_tiles(self, size: Pos, walls: WallGrid) -> TileGrid:
        pass

class WorldGenerator:
    """Holds the data for generating worlds"""
    # Generation models
    wall_generator: WallGenerator
    wall_features: Iterable[WallFeature]
    tile_generator: TileGenerator