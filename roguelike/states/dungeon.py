from collections import defaultdict
from dataclasses import (
    dataclass,
    field
)
from enum import Enum
import heapq
import math
import random
from typing import (
    cast,
    ClassVar,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    TYPE_CHECKING
)

import pygame as pg

from roguelike.engine import (
    assets,
    gamestate,
    inputs,
    sprite,
    text,
    tween
)
from roguelike.entities import entity

if TYPE_CHECKING:
    from roguelike.engine.renderer import Renderer

class RandomAnimType(Enum):
    GLOBAL      = 0
    X           = 1
    Y           = 2
    X_PLUS_Y    = 3
    X_MINUS_Y   = 4
    RANDOM      = 5

@dataclass
class DungeonTile:
    anim: sprite.AnimationState
    passable: bool
    special_render: bool = False
    offset_type: RandomAnimType = RandomAnimType.GLOBAL
    offset_power: float = 0

@dataclass
class DungeonParticle:
    rect: tween.AnimatableMixin
    motion: tween.Animation
    animstate: Optional[sprite.AnimationState] = None
    msg: Optional[str] = None
    text_color: Tuple[float, float, float, float] = (0, 0, 0, 0)
    font: Optional[text.CharBank] = None
    
    def render_particle(self,
                        delta_time: float,
                        renderer: 'Renderer',
                        offset: Tuple[float, float]) -> bool:
        active = self.motion.update(delta_time)
        pos = (self.rect.x + offset[0], self.rect.y + offset[1])
        if self.animstate is not None:
            self.animstate.render(renderer,
                                  pos,
                                  (self.rect.w, self.rect.h))
        if self.msg:
            assert self.font is not None
            self.font.draw_str_in(self.msg,
                                  pos,
                                  (self.rect.w, self.rect.h),
                                  self.text_color,
                                  alignment=text.CENTER_CENTER)
        return active

class DungeonMap:
    """A map of a dungeon
    
    Arguments:
    size: Dimensions (w, h) in tiles, can probably be refactored out
    tiles: List of tiles that can be drawn from
    vignette_color: Color blended with tiles outside of FOV,
        can vary per map
    """
    def __init__(self,
                 size: Tuple[int, int],
                 tiles: List[DungeonTile],
                 vignette_color: Tuple[float, float, float, float] =\
                    (.3, .25, .4, 1)):
        self.size = size
        self.tiles = tiles
        self.tile_map: Dict[Tuple[int, int], int] = defaultdict(lambda: -1)
        self.foreground: Dict[Tuple[int, int], int] =\
            defaultdict(lambda: -1)
        self.entities: Dict[Tuple[int, int], Optional[entity.Entity]] =\
            defaultdict(lambda: None)
        self.player: entity.Entity = None # type: ignore
        self.vignette_color = vignette_color
    
    @staticmethod
    def _manhattan_dist(from_: Tuple[int, int], to: Tuple[int, int]) -> int:
        return abs(from_[0] - to[0]) + abs(from_[1] - to[1])
    
    @staticmethod
    def _diag_dist(from_: Tuple[int, int], to: Tuple[int, int]) -> int:
        return max(abs(from_[0] - to[0]), abs(from_[1] - to[1]))
    
    def a_star(self,
               from_: Tuple[int, int], 
               to: Tuple[int, int],
               maxdist: int = -1) -> Optional[Sequence[Tuple[int, int]]]:
        """Perform A* search to find the sequence of moves to get from
        from_ to to within an optional maximum distance
        Uses Manhattan distance as a heuristic, which is optimistic on
        the grid-based world. Distance increments by 1 at each step, and
        the entity can step in the 4 cardinal direction
        """
        visited = {from_}
        heap: List[Tuple[
                         int,
                         int,
                         Tuple[int, int],
                         Optional[Tuple[int, int]]]] =\
            [(DungeonMap._manhattan_dist(from_, to), 0, from_, None)]
        backtrack: Dict[Tuple[int, int], Tuple[int, int]] = {}
        while heap:
            cost, distance, pos, prev = heapq.heappop(heap)
            x, y = pos
            backtrack[(x, y)] = cast(Tuple[int, int], prev)
            if (x, y) == to:
                steps = [(x, y)]
                while (x, y) != from_:
                    x, y = backtrack[(x, y)]
                    steps.append((x, y))
                steps.reverse()
                return steps
            frontier = ((x+1,y),(x-1,y),(x,y+1),(x,y-1))
            for each in frontier:
                if each in visited:
                    continue
                if not self.is_free(each) and each != to:
                    continue
                visited.add(each)
                if maxdist < 0 or distance + 1 <= maxdist:
                    cost = distance + DungeonMap._manhattan_dist(each, to)
                    heapq.heappush(heap, (cost, distance + 1, each, (x, y)))
        return None
    
    def tile_at(self, pos: Tuple[int, int]) -> Optional[DungeonTile]:
        if pos in self.tile_map:
            index = self.tile_map[pos]
            if index == -1:
                return None
            return self.tiles[index]
        return None
    
    def is_free(self, pos: Tuple[int, int]) -> bool:
        tile = self.tile_at(pos)
        if tile is None or not tile.passable:
            return False
        any_ent = self.entities.get(pos, None)
        if any_ent is not None:
            if not any_ent.passable:
                return False
        return True
    
    def move_entity(self, from_: Tuple[int, int], to: Tuple[int, int]) -> bool:
        if from_ not in self.entities\
                or self.entities.get(to, None) is not None\
                or not self.is_free(to):
            return False
        ent = self.entities.pop(from_)
        if ent is None:
            return False
        self.entities[to] = ent
        ent.dungeon_pos = list(to)
        return True
    
    def place_entity(self, ent: entity.Entity) -> bool:
        check_pos = cast(Tuple[int, int], tuple(ent.dungeon_pos))
        if not self.is_free(check_pos):
            return False
        self.entities[check_pos] = ent
        return True
    
    def remove_entity(self, ent: entity.Entity) -> None:
        check_pos = cast(Tuple[int, int], tuple(ent.dungeon_pos))
        if self.entities.get(check_pos, None) is ent:
            self.entities.pop(check_pos)

class DungeonMapState(gamestate.GameState):
    """Gamestate for traversing a dungeon
    
    Arguments:
    dungeon: DungeonMap instance for the level
    tile_size: Size in pixels of each tile
    
    ClassVars:
    vignette_sprite: Masking sprite for vignette effect
    font: CharBank to render text in
    base_text_scale: Adjustment parameter to scale text
    """
    vignette_sprite: ClassVar[sprite.Sprite]
    font: ClassVar[text.CharBank]
    base_text_scale: ClassVar[float]
    base_tile_size: ClassVar[float] = 64

    def __init__(self, *args, **kwargs):
        self.dungeon_map = kwargs.pop('dungeon')
        self.tile_size = kwargs.pop('tile_size')
        super().__init__(*args, **kwargs)
        self.camera = tween.AnimatableMixin()
        self.particles: List[DungeonParticle] = []
        self.vignette_sprite = assets.Sprites.instance.vignette
    
    def render_gamestate(self,
                         delta_time: float,
                         renderer: 'Renderer') -> None:
        super().render_gamestate(delta_time, renderer)
        player = self.dungeon_map.player
        # Get important camera info
        
        num_tiles_x = (renderer.screen_size[0] + self.tile_size - 1)\
            // self.tile_size + 2
        num_tiles_y = (renderer.screen_size[1] + self.tile_size - 1)\
            // self.tile_size + 2
        c_x = self.camera.x + player.rect.x + player.rect.w // 2
        c_y = self.camera.y + player.rect.y + player.rect.h // 2
        adj_x = c_x - renderer.screen_size[0] // 2
        adj_y = c_y - renderer.screen_size[1] // 2
        start_tile_x = math.floor(
            (c_x - renderer.screen_size[0] // 2)\
            // self.tile_size - 1)
        start_tile_y = math.floor(
            (c_y - renderer.screen_size[1] // 2)\
            // self.tile_size - 1)
        
        player_scr_x = player.rect.x + player.rect.w // 2 - adj_x
        player_scr_y = player.rect.y + player.rect.h // 2 - adj_y
        
        # Render background tiles
        oldest_fbo = renderer.current_fbo()
        
        stack_fbo = renderer.push_fbo()
        stack_fbo.clear(0, 0, 0, 1)
        for y in range(start_tile_y, start_tile_y + num_tiles_y):
            for x in range(start_tile_x, start_tile_x + num_tiles_x):
                if (x, y) in self.dungeon_map.tile_map:
                    tile = self.dungeon_map.tile_at((x, y))
                    if tile is not None:
                        if tile.special_render:
                            tile.render(delta_time,
                                        renderer,
                                        (x, y),
                                        self.tile_size)
                        else:
                            dt = 0
                            if tile.offset_type == RandomAnimType.X:
                                dt += x * tile.offset_power
                            elif tile.offset_type == RandomAnimType.Y:
                                dt += y * tile.offset_power
                            elif tile.offset_type == RandomAnimType.X_PLUS_Y:
                                dt += (x + y) * tile.offset_power
                            elif tile.offset_type == RandomAnimType.X_MINUS_Y:
                                dt += (x - y) * tile.offset_power
                            elif tile.offset_type == RandomAnimType.RANDOM:
                                dt += random.random() * tile.offset_power
                            tile.anim.render(renderer,
                                             (x * self.tile_size - adj_x,
                                              y * self.tile_size - adj_y),
                                             (self.tile_size, self.tile_size),
                                             0,
                                             dt)
        # Experimenal, bloom?
        # renderer.apply_bloom(5, 1, .7)
        # Nah
        
        # Render dark FBO
        renderer.fbo_to_fbo(oldest_fbo,
                            stack_fbo,
                            colorMask = self.dungeon_map.vignette_color)
        
        # Draw vignette sprite
        renderer.fbos['accum0'].use()
        renderer.clear()
        renderer.render_sprite(self.vignette_sprite,
                               (player_scr_x, player_scr_y),
                               (renderer.screen_size[1],
                                renderer.screen_size[1]),
                               positioning=('center', 'center'))
        stack_fbo.use()
        renderer.apply_vignette(oldest_fbo,
                                renderer.fbos['accum0'].color_attachments[0])
        renderer.pop_fbo()
        
        # Increment tile animations
        for tile in self.dungeon_map.tiles:
            tile.anim.increment(delta_time)
        
        # TODO: render foreground
        
        # Render other entities w/ vignette effect
        stack_fbo = renderer.push_fbo()
        renderer.clear()
        for pos, ent in self.dungeon_map.entities.items():
            if (ent.rect.x < renderer.screen_size[0]
                    or ent.rect.x + ent.rect.w >= 0)\
                    and (ent.rect.y < renderer.screen_size[1]
                    or ent.rect.y + ent.rect.h >= 0):
                ent.render_entity(delta_time, renderer, (-adj_x, -adj_y))
        # Do post effects after
        for pos, ent in self.dungeon_map.entities.items():
            if (ent.rect.x < renderer.screen_size[0]
                    or ent.rect.x + ent.rect.w >= 0)\
                    and (ent.rect.y < renderer.screen_size[1]
                    or ent.rect.y + ent.rect.h >= 0):
                ent.render_entity_post(delta_time, renderer, (-adj_x, -adj_y))

        # Vignette on visibility of mobs
        renderer.fbos['accum0'].use()
        renderer.clear()
        renderer.render_sprite(self.vignette_sprite,
                               (player_scr_x, player_scr_y),
                               (renderer.screen_size[1],
                                renderer.screen_size[1]),
                               positioning=('center', 'center'))
        stack_fbo.use()
        renderer.apply_vignette(oldest_fbo,
                                renderer.fbos['accum0'].color_attachments[0])
        renderer.pop_fbo()
        oldest_fbo.use()
        
        # Render player
        player.render_entity(delta_time,
                             renderer,
                             (-adj_x + player.shaky_cam[0],
                              -adj_y + player.shaky_cam[1]))
        
        # Render particles
        self.particles[:] = [p for p in self.particles if
            p.render_particle(delta_time, renderer, (-adj_x, -adj_y))]
        
        # Render UI
        hp_str = f'HP:{player.hp:4}/{player.max_hp:4}'
        self.font.draw_str(hp_str,
                                      (self.tile_size // 4,) * 2,
                                      (0, 1, 0, 1),
                                      (self.base_text_scale,) * 2)
    
    def update_gamestate(self, delta_time: float) -> bool:
        super().update_gamestate(delta_time)
        if self.locked():
            return True
        # Update entities
        player_pos = self.dungeon_map.player.dungeon_pos
        for entity in self.dungeon_map.entities.values():
            entity.update_entity(delta_time, self, player_pos)
            
        # Update player
        self.dungeon_map.player.update_entity(delta_time, self, player_pos)
        return True
    
    def let_entities_move(self) -> None:
        """Called after the player takes an action so other entities can
        take their actions, if applicable
        """
        player_pos = cast(Tuple[int, int],
                          tuple(self.dungeon_map.player.dungeon_pos))
        entities = tuple(self.dungeon_map.entities.values())
        for ent in entities:
            if ent.actionable:
                actor = cast(entity.ActingEntity, ent)
                sees_player = actor.detection_radius < 0
                if not sees_player:
                    sees_player =\
                        self.dungeon_map._diag_dist(actor.dungeon_pos,
                                                         player_pos)\
                             <= actor.detection_radius
                if sees_player:
                    actor.give_energy(1.)
                    actor.expend_energy(self, player_pos)
    
    def spawn_particle(self,
                       rect: tween.AnimatableMixin,
                       motion: tween.Animation,
                       msg: Optional[str] = None,
                       text_color: Tuple[float, float, float, float]=\
                           (0, 0, 0, 0),
                       animation: Optional[sprite.Animation] = None) -> None:
        animstate = None if animation is None\
            else sprite.AnimationState(animation)
        particle = DungeonParticle(
            rect, motion, animstate, msg, text_color, self.font)
        self.particles.append(particle)
    
    @classmethod
    def init_sprites(cls, renderer: 'Renderer') -> None:
        # tex = renderer.load_texture('vignette.png')
        # cls.vignette_sprite = sprite.Sprite(tex, (0, 0), tex.size)
        cls.font = renderer.get_font('Consolas', 64)
        cls.base_text_scale = cls.font.scale_to_bound(
            "O", (cls.base_tile_size,) * 2)
        print(cls.base_text_scale)
