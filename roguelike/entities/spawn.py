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
class Spawn:
    spawn_class: Optional[Type['Entity']]
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
    def populate(self, pos: Pos) -> Optional[Tuple[Pos, Type, Dict[str, Any]]]:
        options = [i for i, spn in enumerate(self.spawns)\
            if (self.so_far[i] < spn.limit or spn.limit < 0)\
            and eval_preds(spn.predicates)]
        if len(options) == 0:
            return None
        weights = np.array([self.spawns[i].weight for i in options],
                           dtype=float)
        choice = np.random.choice(options, p=weights/weights.sum())
        spawn = self.spawns[choice]
        if spawn.spawn_class is None:
            return None
        self.so_far[choice] += 1
        return (pos, spawn.spawn_class, spawn.params)

def parse_spawns(source: List[Dict[str, Any]]) -> Populator:
    spawns: List[Spawn] = []
    for spawn_d in source:
        print(spawn_d)
        spawn_d = dict(spawn_d)
        class_name = cast(str, spawn_d.pop('class', None))
        clazz = None if class_name is None else entity.entities[class_name]
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