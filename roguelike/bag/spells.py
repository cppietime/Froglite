from dataclasses import (
    dataclass
)
from typing import (
    cast,
    ClassVar,
    Dict,
    TYPE_CHECKING
)

from roguelike.engine import (
    assets,
    event_manager,
    sprite,
    tween
)
from roguelike.bag import item
from roguelike.entities import player

if TYPE_CHECKING:
    from roguelike.entities.entity import (
        ActingEntity,
        FightingEntity
    )
    from roguelike.engine.gamestate import GameState
    from roguelike.world.dungeon import DungeonMapState

@dataclass(frozen=True, eq=True)
class ProjectileSpell(item.SpellItem):
    reach: int
    animation_name: str
    attack_pow: float
    
    tile_speed: ClassVar[float] = .1
    
    def on_use(self, state: 'GameState', user: 'FightingEntity') -> None:
        assert user.anim is not None
        dms = cast('DungeonMapState', state)
        dmap = dms.dungeon_map
        step_x, step_y = 0, 0
        if user.anim.direction == sprite.AnimDir.UP:
            step_y = -1
        elif user.anim.direction == sprite.AnimDir.DOWN:
            step_y = 1
        elif user.anim.direction == sprite.AnimDir.LEFT:
            step_x = -1
        elif user.anim.direction == sprite.AnimDir.RIGHT:
            step_x = 1
        x0, y0 = x1, y1 = user.dungeon_pos
        target = None
        for steps in range(1, 1 + self.reach):
            x1 += step_x
            y1 += step_y
            tile = dmap.tile_at((x1, y1))
            if tile is None or not tile.passable:
                break
            if (x1, y1) in dmap.entities:
                ent = dmap.entities[(x1, y1)]
                if ent.attackable:
                    target = cast('FightingEntity', ent)
                    break
        src_rect = user.rect
        rect = tween.AnimatableMixin(src_rect.x, src_rect.y,
            src_rect.w, src_rect.h)
        motion = tween.Animation([
            (0, tween.Tween(
                rect, 'x', rect.x, rect.x + (x1 - x0) * rect.w,
                self.tile_speed * steps)),
            (0, tween.Tween(
                rect, 'y', rect.y, rect.y + (y1 - y0) * rect.h,
                self.tile_speed * steps))
        ])
        motion.attach(dms)
        animation = assets.Animations.instance.animations[self.animation_name]
        dms.spawn_particle(rect, motion, animation=animation, direction=user.anim.direction)
        assets.Sounds.instance.pew.play()
        if target is not None:
            dmg = user._spell_attack_logic(self.attack_pow, dms, target)
            def _event(_state, event):
                while _state.locked():
                    yield True
                assets.Sounds.instance.fwsh.play()
                target.get_hit(_state, user, dmg)
                while _state.locked():
                    yield True
                if isinstance(user, player.PlayerEntity):
                    user.taken_action(_state)
                yield False
            dms.queue_event(event_manager.Event(_event))

@dataclass(frozen=True, eq=True)
class FreezeSpell(item.SpellItem):
    stall: float
    
    def on_use(self, state: 'GameState', user: 'FightingEntity') -> None:
        dms = cast('DungeonMapState', state)
        for ent in dms.dungeon_map.entities.values():
            if not ent.actionable:
                continue
            actor = cast('ActingEntity', ent)
            actor.energy = -self.stall
        assets.Sounds.instance.pew.play()

items: Dict[str, item.SpellItem] = {}

def init_items():
    source = assets.residuals.pop('spells')
    for name, value in source.items():
        icon = assets.Sprites.instance.sprites[value['icon']]
        description = value['description']
        display = value.get('display', name.title())
        cost = value.get('cost', 2)
        kind = value['kind']
        if kind == 'projectile':
            reach = value.get('reach', 4)
            anim_name = value['animation']
            attack = value['attack']
            spell = ProjectileSpell(name, icon, description, display, cost, reach=reach, animation_name=anim_name, attack_pow=attack)
        elif kind == 'freeze':
            stall = value.get('stall', 1)
            spell = FreezeSpell(name, icon, description, display, cost, stall)
        else:
            raise ValueError(f'{kind} is not a valid spell type')
        items[name] = spell
    item.items.update(items)
