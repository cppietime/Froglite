import collections
from enum import IntEnum
from dataclasses import (
    dataclass
)
from typing import (
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    OrderedDict,
    Union,
    TYPE_CHECKING
)

if TYPE_CHECKING:
    from roguelike.engine.gamestate import GameState
    from roguelike.engine.sprite import Sprite
    from roguelike.entities.entity import FightingEntity

class ItemSlot(IntEnum):
    EQUIPMENT = 0
    SPELLS = 1
    KEYS = 2
    CONSUMABLES = 3

slot_names = ["Gear", "Spells", "Keys", "Items"]

@dataclass(frozen=True, eq=True)
class BaseItem:
    """Base class for anything that can be in the inventory
    
    Arguments:
    name: Display name when selected
    icon: Image to display in inventory
    description: Free-form text to display
    """
    name: str
    icon: 'Sprite'
    description: str
    
    itemslot: ClassVar[ItemSlot]
    usable: ClassVar[bool] = False
    tossable: ClassVar[bool] = True
    equippable: ClassVar[bool] = False

@dataclass(frozen=True, eq=True)
class ConsumableItem(BaseItem):
    """An item that can be used, consumed or not
    
    Arguments:
    on_use: Function called when used
    """
    on_use: Callable[['GameState', Optional['GameState'], 'FightingEntity'],
                     None]
    
    itemslot = ItemSlot.CONSUMABLES
    usable = True

@dataclass(frozen=True, eq=True)
class KeyItem(BaseItem):
    """Key items, like keys to progress etc
    """
    
    itemslot = ItemSlot.KEYS
    
    tossable = False

class EquipmentSlot(IntEnum):
    WEAPON = 0
    SPELL = 1
    ARMOR = 2

@dataclass(frozen=True, eq=True)
class EquipableItem(BaseItem):
    """Equipment that can be equipped
    Probably just a base class for other stuff
    """
    equip_slot: ClassVar[EquipmentSlot]
    
    equippable = True
    
@dataclass(frozen=True, eq=True)
class WeaponItem(EquipableItem):
    """Melee weapons
    """
    damage_mul: float
    
    itemslot = ItemSlot.EQUIPMENT
    equip_slot = EquipmentSlot.WEAPON

@dataclass(frozen=True, eq=True)
class ArmorItem(EquipableItem):
    """Armor"""
    def_mul: float
    
    itemslot = ItemSlot.EQUIPMENT
    equip_slot = EquipmentSlot.ARMOR

@dataclass(frozen=True, eq=True)
class SpellItem(EquipableItem):
    """Not really an item but it can be accessed through the
    player's inventory all the same
    """
    def on_use(self, state: 'GameState', user: 'FightingEntity') -> None:
        pass
    
    itemslot = ItemSlot.SPELLS
    equip_slot = EquipmentSlot.SPELL

class Inventory:
    def __init__(self, *args, **kwargs):
        self.owner: 'FightingEntity' = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        self.items: Dict[ItemSlot, OrderedDict[BaseItem, int]] = {
            slottype: collections.OrderedDict() for slottype in ItemSlot
        }
        self.equipment: Dict[EquipmentSlot, BaseItem] = {
            eqtype: None for eqtype in EquipmentSlot
        }
    
    def __getitem__(self, key: Union[ItemSlot, BaseItem, EquipmentSlot])\
            -> Union[OrderedDict[BaseItem, int], int, BaseItem, None]:
        if isinstance(key, ItemSlot):
            return self.items[key]
        elif isinstance(key, BaseItem):
            slots = self.items[key.itemslot]
            return slots.get(key, 0)
        elif isinstance(key, EquipmentSlot):
            return self.equipment.get(key, None)
        raise ValueError('Key must be ItemSlot or BaseItem')
    
    def __contains__(self, item: BaseItem) -> bool:
        return self[item] != 0
    
    def give_item(self, item: BaseItem, count: int) -> None:
        slots = self.items[item.itemslot]
        if item not in slots:
            slots[item] = 0
        slots[item] += count
    
    def take_item(self, item: BaseItem, count: int) -> bool:
        """Returns True iff the item was successfully taken"""
        slots = self.items[item.itemslot]
        current_count = slots.get(item, 0)
        if current_count < count:
            return False
        slots[item] -= count
        if slots[item] == 0:
            slots.pop(item)
        return True
    
    def equipped(self, item: EquipableItem) -> bool:
        return self.equipment[item.equip_slot] is item

items: Dict[str, BaseItem] = {}
    