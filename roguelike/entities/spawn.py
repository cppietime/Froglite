from dataclasses import (
    dataclass,
    field
)
from typing import  (
    cast,
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TYPE_CHECKING
)

import numpy as np
import numpy.typing as npt

from roguelike.engine import (
    assets
)
from roguelike.entities import (
    entity
)

if TYPE_CHECKING:
    from roguelike.entities.entity import Entity

Pos = Tuple[int, int]
Predicates = Sequence[Tuple[str, str, Any, bool]]
def eval_preds(predicates: Predicates) -> bool:
    for varname, comparison, value, persists in predicates:
        pool = assets.persists if persists else assets.variables
        variable = pool[varname]
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
class Spawn:
    spawn_class: Optional[Type['Entity']]
    params: Dict[str, Any]
    # limit: int
    # weight: float
    # difficulty_range: Pos
    # predicates: Predicates

@dataclass
class SpawnCondition:
    spawn_name: str
    limit: int
    weight: float
    predicates: Predicates

@dataclass
class Populator:
    spawns: Sequence[SpawnCondition]
    so_far: List[int] = field(init=False)
    def __post_init__(self):
        self.reset_counts()
    
    def reset_counts(self) -> None:
        self.so_far = [0] * len(self.spawns)
    
    """Puts something optional and interesting into a level"""
    def populate(self, pos: Pos) -> Optional[Tuple[Pos, Type, Dict[str, Any]]]:
        options = [i for i, spn in enumerate(self.spawns)\
            if (self.so_far[i] < spn.limit or spn.limit < 0)\
            and eval_preds(spn.predicates)]
        if len(options) == 0:
            return None
        weights = np.array([self.spawns[i].weight for i in options],
                           dtype=float)
        choice = np.random.choice(options, p=weights/weights.sum())
        spawn = spawns[self.spawns[choice].spawn_name]
        if spawn.spawn_class is None:
            return None
        self.so_far[choice] += 1
        return (pos, spawn.spawn_class, spawn.params)

def parse_spawn(source: Dict[str, Any]) -> Spawn:
    class_name = cast(str, source.pop('class', None))
    clazz = None if class_name is None else entity.entities[class_name]
    anim_name = cast(Optional[str], source.pop('animation', None))
    # limit = source.pop('limit', -1)
    # weight = source.pop('weight', 1)
    # diff = cast(Pos, tuple(source.pop('difficulty', [-1, -1])))
    # preds = cast(Predicates,
                 # tuple(map(tuple, source.pop('predicates', []))))
    params = dict(source)
    if anim_name is not None:
        if anim_name in assets.Animations.instance.animations:
            params['anim'] =\
                assets.Animations.instance.animations[anim_name]
        elif anim_name in assets.Sprites.instance.sprites:
            params['anim'] = assets.Sprites.instance.sprites[anim_name]
        else:
            raise ValueError(f'{anim_name} is not a recognized asset')
    return Spawn(clazz, params)

def parse_spawns(source: List[Dict[str, Any]]) -> Populator:
    spawns: List[SpawnCondition] = []
    for spawn_d in source:
        limit = spawn_d.get('limit', -1)
        weight = spawn_d.get('weight', 1)
        preds = cast(Predicates,
                     tuple(map(tuple, spawn_d.get('predicates', []))))
        name = spawn_d['name']
        spawns.append(SpawnCondition(name, limit, weight, preds))
    return Populator(spawns)

spawns: Dict[str, Spawn] = {}

def init():
    for name, value in assets.residuals['spawns'].items():
        spawns[name] = parse_spawn(value)