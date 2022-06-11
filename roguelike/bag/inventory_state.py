import dataclasses
from typing import (
    cast,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    OrderedDict,
    Tuple,
    TYPE_CHECKING
)

import pygame as pg

from roguelike.engine import (
    inputs,
    text,
    tween
)
from roguelike.bag import item
from roguelike.states import ui

if TYPE_CHECKING:
    from roguelike.engine.gamestate import GameState

def _build_button_widget(txt: str,
                         rect: List[float],
                         scale: float,
                         command: Callable[['GameState'], None],
                         active_text_color: List[float]=None,
                         inactive_text_color: List[float]=None,
                         alignment: Tuple[text.AlignmentH, text.AlignmentV]=\
                            (text.AlignmentH.LEFT, text.AlignmentV.CENTER))\
                         -> ui.Widget:
    if active_text_color is None:
        active_text_color = [1, 0, 1, 1]
    if inactive_text_color is None:
        inactive_text_color = [1, 1, 1, 1]
    active_label = ui.Label(text=txt,
                            text_rect=rect,
                            scale=scale,
                            font=InventoryBaseScreen.font,
                            text_color=active_text_color)
    inactive_label = dataclasses.replace(active_label)
    inactive_label.text_color = inactive_text_color
    return ui.TwoLabelButton(
        active=active_label, inactive=inactive_label,
        command=command)

class InventoryBaseScreen(ui.PoppableMenu):
    """Base inventory screen to choose an item slot"""
    
    button_w: ClassVar[float] = 960 / 4
    button_h: ClassVar[float] = 360
    button_text_margin_x: ClassVar[float] = 35
    button_text_margin_y: ClassVar[float] = 35
    font: ClassVar[text.CharBank]
    header_scale: ClassVar[float]
    text_scale: ClassVar[float]
    
    def __init__(self, *args, **kwargs):
        self.inventory: item.Inventory = kwargs.pop('inventory')
        super().__init__(*args, **kwargs)
        metawidget = self.widget
        mainholder = metawidget.widget
        mainholder.horizontal = False
        self.desc_label = ui.Label(None, None)
        self.cycle_screen = ui.WidgetHolder(horizontal=True)
        mainholder.widgets.append(self.cycle_screen)
        self.cycle_screen.spacing = self.button_w
        self.cycle_screen.zero_point = (len(item.ItemSlot) - 1) / 2
        for i, slot in enumerate(item.ItemSlot):
            button = _build_button_widget(
                item.slot_names[i],
                [self.button_text_margin_x,
                 self.button_text_margin_y,
                 self.button_w - self.button_text_margin_x,
                 self.button_h - self.button_text_margin_y],
                 self.header_scale,
                 lambda _, i=i: self.goto_subscreen(i))
            self.cycle_screen.widgets.append(button)
    
    def _trigger_pop(self):
        if self.auto_pop:
            self.die()
        else:
            print('Fake anim')
            self.die()
    
    def goto_subscreen(self, index: int) -> None:
        itemslot = item.ItemSlot(index)
        screen = _itemslotsubscreens[itemslot]
        slot_inv = cast(OrderedDict[item.BaseItem, int],
                        self.inventory[itemslot])
        screen._build_menu(slot_inv, self.inventory, self)
        self.manager.push_state(screen)
    
    @classmethod
    def set_font(cls, font: text.CharBank) -> None:
        cls.font = font
        cls.header_scale = font.scale_to_bound(
            "Spells", (cls.button_w, cls.button_h))
        cls.text_scale = font.scale_to_bound(
            "Spells", (cls.button_w / 2, cls.button_h / 2))
    
    @staticmethod
    def init_globs() -> None:
        global _itemslotsubscreens, _itemusescreen, _usetossscreen
        _itemslotsubscreens = {
            slot: ItemSlotSubscreen() for slot in item.ItemSlot
        }
        _usetossscreen = UseTossScreen()
        _itemusescreen = ItemUseConfirmation()
        
class ItemSlotSubscreen(ui.PoppableMenu):
    """Screen for one item slot in inventory"""
    menu_w: ClassVar[float] = 960 / 4
    panel_x: ClassVar[float] = 960 / 2
    panel_w: ClassVar[float] = 960 / 2
    item_name_size: ClassVar[float] = 960 / 5
    item_name_padding: ClassVar[float] = 30.
    item_row_height: ClassVar[float] = 100.
    icon_size: ClassVar[float] = 120.
    icon_x: ClassVar[float] = (menu_w - icon_size) / 2
    item_spacing: ClassVar[float] = item_row_height + icon_size
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        metawidget = self.widget
        mainholder = metawidget.widget
        mainholder.horizontal = True
        mainholder.spacing = self.panel_x
        mainholder.buffer_display = 0
        self.menu_widget = ui.WidgetHolder(spacing=self.item_spacing,
                                           buffer_display=0)
        self.desc_widget = ui.Label(text_rect=[
                                        0., 0.,
                                        self.panel_w, self.panel_w],
                                    text="Whatevs",
                                    font=InventoryBaseScreen.font,
                                    scale=InventoryBaseScreen.text_scale)
        mainholder.widgets += [self.menu_widget, self.desc_widget]
        
        # Back button
        self.back_button = _build_button_widget(
            "Back",
            [0, 0,
             self.item_name_size,
             self.item_row_height],
            InventoryBaseScreen.header_scale,
            lambda _: self._trigger_pop())
    
    def _build_menu(self,
                    slot: Optional[OrderedDict[item.BaseItem, int]]=None,
                    inventory: Optional[item.Inventory]=None,
                    parent: Optional['GameState']=None) -> None:
        if slot is not None:
            self.slot: OrderedDict[item.BaseItem, int] = slot
        if inventory is not None:
            self.inventory = inventory
        if parent is not None:
            self.parent = parent
        
        if self.menu_widget.selection >= len(self.slot) and len(self.slot) > 0:
            self.menu_widget.selection = len(self.slot) - 1
            self.menu_widget.offset.y = -self.menu_widget.selection\
                * self.menu_widget.spacing
        self.menu_widget.widgets.clear()
            
        for itm, count in self.slot.items():
            i = len(self.menu_widget.widgets)
            
            # Activation button
            active_color = [1., 0., 1., 1.]
            inactive_color = [1., 1., 1., 1.]
            # Separate colors for equipped stuff
            if itm.equippable:
                equipment = cast(item.EquipableItem, itm)
                if self.inventory.equipped(equipment):
                    inactive_color = [1., .5, .5, 1.]
                    active_color = [.5, .2, 1., 1.]
            button = _build_button_widget(
                itm.name,
                [0, 0, self.item_name_size, self.item_row_height],
                InventoryBaseScreen.header_scale,
                lambda _, i=i: self._on_button_press(i), # type: ignore
                active_color,
                inactive_color,
                (text.AlignmentH.RIGHT, text.AlignmentV.CENTER))
            
            # Preview icon
            icon = ui.Label(itm.icon,
                            [self.icon_x, 0., self.icon_size, self.icon_size])
            
            # X quantity indicator
            quantity = ui.Label(text=f'x{count}',
                                text_rect=[0.,
                                           0.,
                                           self.menu_w - self.item_name_size,
                                           self.item_row_height],
                                font=InventoryBaseScreen.font,
                                text_color=[1, 1, 1, 1],
                              scale = InventoryBaseScreen.text_scale)
            
            # Row 0: Name - quantity
            # Row 1: -----Icon------
            row_0 = ui.WidgetHolder(spacing=self.item_name_size\
                                        + self.item_name_padding,
                                    horizontal=True,
                                    buffer_display=0)
            row_0.widgets += [button, quantity]
            
            mini_holder = ui.WidgetHolder(spacing=self.item_row_height,
                                          buffer_display=0)
            mini_holder.widgets += [row_0, icon]
            self.menu_widget.widgets.append(mini_holder)
        
        self.menu_widget.widgets.append(self.back_button)
    
    def render_gamestate(self, delta_time, renderer):
        if self.menu_widget.selection >= len(self.slot):
            text = "Nothing here..."
        else:
            itm = list(self.slot.items())[self.menu_widget.selection][0]
            text = itm.description
            if itm.equippable:
                equipment = cast(item.EquipableItem, itm)
                if self.inventory.equipped(equipment):
                    text += "\nEquipped"
        self.desc_widget.text = text
        super().render_gamestate(delta_time, renderer)
    
    def _on_button_press(self, i: int) -> None:
        itm, count = list(self.slot.items())[i]
        if not itm.usable and not itm.tossable and not itm.equippable:
            return
        _usetossscreen._build_menu(itm,
                                   count,
                                   self.inventory,
                                   self)
        self.manager.push_state(_usetossscreen)
    
    def _trigger_pop(self):
        self.die()

class UseTossScreen(ui.PoppableMenu):
    """Option to use or toss an item"""
    button_width: ClassVar[float] = 150.
    button_height: ClassVar[float] = 80.
    button_spacing: ClassVar[float] = 20.
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mainholder = self.widget.widget
        mainholder.spacing = ItemSlotSubscreen.panel_x
        mainholder.buffer_display = 0
        mainholder.horizontal = True
        self.holder = ui.WidgetHolder(
            spacing=self.button_height + self.button_spacing,
            buffer_display=0)
        self.desc_label = ui.Label(text="",
                                   text_rect=[
                                       0., 0.,
                                       ItemSlotSubscreen.panel_w,
                                       ItemSlotSubscreen.panel_w],
                                   font=InventoryBaseScreen.font,
                                   scale=InventoryBaseScreen.text_scale)
        mainholder.widgets += [self.holder, self.desc_label]
        self.button_use = _build_button_widget(
            "Use",
            [0, 0, self.button_width, self.button_height],
            InventoryBaseScreen.header_scale,
            lambda _: self.use())
        self.button_equip = _build_button_widget(
            "Equip",
            [0, 0, self.button_width, self.button_height],
            InventoryBaseScreen.header_scale,
            lambda _: self.equip())
        self.button_toss = _build_button_widget(
            "Toss",
            [0, 0, self.button_width, self.button_height],
            InventoryBaseScreen.header_scale,
            lambda _: self.toss())
    
    def _build_menu(self,
                    itm: Optional[item.BaseItem]=None,
                    count: int=-1,
                    inventory: Optional[item.Inventory]=None,
                    parent: Optional['GameState']=None) -> None:
        if parent is not None:
            self.parent = parent
        if itm is not None:
            self.item = itm
        if count >= 0:
            self.count = count
        if inventory is not None:
            self.inventory = inventory
        
        self.desc_label.text = self.item.description
        
        self.holder.widgets.clear()
        if self.item.usable:
            meta = ui.MetaWidget(widget=self.button_use,
                                 bounding_rect=tween.AnimatableMixin(
                                     0, 0,
                                     self.button_width, self.button_height),
                                 reset_scr=[0., 0., 1., 1.])
            self.holder.widgets.append(meta)
        if self.item.equippable:
            equipment = cast(item.EquipableItem, self.item)
            if self.inventory.equipped(equipment):
                self.button_equip.active.text = "Unequip"
                self.button_equip.inactive.text = "Unequip"
            self.holder.widgets.append(self.button_equip)
        if self.item.tossable:
            tossable = True
            if self.item.equippable:
                equipment = cast(item.EquipableItem, self.item)
                tossable =\
                    self.inventory[equipment.equip_slot] is not equipment
            if tossable:
                self.holder.widgets.append(self.button_toss)
        self.holder.snap_selection(0)
    
    def use(self):
        self.auto_pop = True
        if self.item.tossable:
            self.inventory.take_item(self.item, 1)
            if self.inventory[self.item] == 0\
                    and len(self.inventory[self.item.itemslot]) == 0:
                self.parent.auto_pop = True
            else:
                self.parent._build_menu(self.parent.slot,
                                        self.parent.inventory)
        self.item.on_use(self.manager.state_stack[-4],
                         self,
                         self.inventory.owner)
    
    def display_message(self, msg: str):
        _itemusescreen._build_message(msg)
        self.manager.push_state(_itemusescreen)
        # TODO display confirmation
    
    def toss(self):
        self.inventory.take_item(self.item, 1)
        if self.inventory[self.item] == 0\
                and len(self.inventory[self.item.itemslot]) == 0:
            self.parent.auto_pop = True
        else:
            self.parent._build_menu(self.parent.slot, self.parent.inventory)
        self._trigger_pop()
    
    def equip(self):
        if self.inventory.equipped(self.item):
            self.inventory.equipment[self.item.equip_slot] = None
        else:
            self.inventory.equipment[self.item.equip_slot] = self.item
        self.parent._build_menu(self.parent.slot, self.parent.inventory)
        self._trigger_pop()
    
    def _trigger_pop(self):
        self.die()

class ItemUseConfirmation(ui.PoppableMenu):
    """Just a message box when you use something"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.holder = self.widget.widget
        self.textbox = ui.Label(text="",
                                text_rect=[0, 0, 200, 200],
                                font=InventoryBaseScreen.font,
                                scale=InventoryBaseScreen.text_scale)
        button = ui.TwoLabelButton(active=self.textbox,
                                   inactive=self.textbox,
                                   command=lambda _: self._trigger_pop())
        self.holder.widgets.append(button)
    
    def _build_message(self, msg: str):
        self.textbox.text = msg
    
    def _trigger_pop(self):
        self.die()

""" Left TODO:
Create the subscreen for each type in the below global dictionary
Finish building the menu skeleton for the item subscreen
Add the item use screen (use/toss/etc)
Implement using consumable items
Fix graphics (add icons, bounding rects, obscure hidden states, etc.)
"""

_itemslotsubscreens: Dict[item.ItemSlot, 'ItemSlotSubscreen']
_itemusescreen: ItemUseConfirmation
_usetossscreen: UseTossScreen