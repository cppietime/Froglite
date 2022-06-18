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
    assets,
    event_manager,
    inputs,
    text,
    tween
)
from roguelike.bag import item
from roguelike.states import ui

if TYPE_CHECKING:
    from roguelike.engine.gamestate import GameState
    from roguelike.engine.sprite import Sprite


class InventoryBaseScreen(ui.PoppableMenu):
    """Base inventory screen to choose an item slot"""
    
    button_w: ClassVar[float] = 1440 / 4
    button_h: ClassVar[float] = 150
    button_y: ClassVar[float] = 300
    button_text_padding_x: ClassVar[float] = 60
    button_text_padding_y: ClassVar[float] = 15
    button_margin_x: ClassVar[float] = 15
    font: ClassVar[text.CharBank]
    header_scale: ClassVar[float]
    text_scale: ClassVar[float]
    active_button_bg: ClassVar['Sprite']
    inactive_button_bg: ClassVar['Sprite']
    bg_reset_clr: Tuple[float, float, float, float] = (0., 0., 0., .25)
    
    def __init__(self, *args, **kwargs):
        self.inventory: item.Inventory = kwargs.pop('inventory')
        super().__init__(*args, **kwargs)
        metawidget = self.widget
        metawidget.reset_scr = list(self.bg_reset_clr)
        # metawidget.bounding_rect = tween.AnimatableMixin(0, 0, 1000, 1000)
        self.mainholder = metawidget.widget
        self.mainholder.horizontal = False
        self.mainholder.base_offset.y = 1080
        self.desc_label = ui.Label(None, None)
        self.cycle_screen = ui.WidgetHolder(horizontal=True)
        self.mainholder.widgets.append(self.cycle_screen)
        self.cycle_screen.spacing = self.button_w
        self.cycle_screen.zero_point = (len(item.ItemSlot) - 1) / 2
        for i, slot in enumerate(item.ItemSlot):
            button = ui.build_button_widget(
                item.slot_names[i],
                [self.button_margin_x,
                 self.button_y,
                 self.button_w - self.button_margin_x * 2,
                 self.button_h],
                 self.header_scale,
                 (self.button_text_padding_x, self.button_text_padding_y),
                 lambda _, i=i: self.goto_subscreen(i),
                 alignment=text.CENTER_CENTER,
                 active_bg_sprite=self.active_button_bg,
                 inactive_bg_sprite=self.inactive_button_bg)
            self.cycle_screen.widgets.append(button)
        self.callbacks_on_push.append(lambda _: self._rise_up())
    
    def _trigger_pop(self):
        if self.auto_pop:
            self.mainholder.base_offset.y = 0
            self.die()
        else:
            def _anim_then_die(state, event):
                while state.locked():
                    yield True
                anim = tween.Animation([
                    (0., tween.Tween(self.mainholder.base_offset,
                                     'y',
                                     0,
                                     1080,
                                     .25))
                ])
                anim.attach(state)
                state.begin_animation(anim)
                while state.locked():
                    yield True
                self.die()
                yield False
            # print('Fake anim')
            # self.die()
            self.queue_event(event_manager.Event(_anim_then_die))
    
    def _rise_up(self):
        self.mainholder.base_offset.y = 1080
        def _anim(state, event):
            while state.locked():
                yield True
            anim = tween.Animation([
                (0., tween.Tween(self.mainholder.base_offset,
                                 'y',
                                 1080,
                                 0,
                                 .25))
            ])
            anim.attach(state)
            state.begin_animation(anim)
            yield False
        self.queue_event(event_manager.Event(_anim))
            
    
    def goto_subscreen(self, index: int) -> None:
        itemslot = item.ItemSlot(index)
        screen = _itemslotsubscreens[itemslot]
        slot_inv = cast(OrderedDict[item.BaseItem, int],
                        self.inventory[itemslot])
        screen._build_menu(slot_inv, self.inventory, self)
        self.manager.push_state(screen)
    
    @classmethod
    def init_globs(cls) -> None:
        global _itemslotsubscreens, _itemusescreen, _usetossscreen
        cls.font = ui.default_font
        w = cls.button_w - (cls.button_text_padding_x + cls.button_margin_x)* 2
        h = cls.button_h - cls.button_text_padding_y * 2
        cls.header_scale = cls.font.scale_to_bound(
            "Spells", (w, h))
        cls.text_scale = cls.font.scale_to_bound(
            "Spells", (w * .5, h * .5))
        cls.active_button_bg = assets.Sprites.instance.button_active
        cls.inactive_button_bg = assets.Sprites.instance.button_inactive
        _itemslotsubscreens = {
            slot: ItemSlotSubscreen() for slot in item.ItemSlot
        }
        _usetossscreen = UseTossScreen()
        _itemusescreen = ItemUseConfirmation()
        
class ItemSlotSubscreen(ui.PoppableMenu):
    """Screen for one item slot in inventory"""
    menu_w: ClassVar[float] = 1440 / 3
    menu_x: ClassVar[float] = 30
    menu_y: ClassVar[float] = 30
    panel_x: ClassVar[float] = 1440 / 2
    panel_w: ClassVar[float] = 1440 / 2
    panel_h: ClassVar[float] = 1080 / 3
    item_name_size: ClassVar[float] = 1440 / 4
    item_name_margin: ClassVar[float] = 10.
    item_name_padding: ClassVar[float] = 15.
    item_row_height: ClassVar[float] = 100.
    icon_size: ClassVar[float] = 100.
    icon_x: ClassVar[float] = (menu_w - icon_size) / 2
    item_spacing: ClassVar[float] = item_row_height + icon_size
    back_button_sep: ClassVar[float] = 30
    scroll_threshold: ClassVar[int] = 4
    scroll_zero_point: ClassVar[float] = 1080 / (100 + 100 + 15) / 2 - 1
    desc_padding: ClassVar[float] = 60
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obscures = False
        metawidget = self.widget
        metawidget.reset_scr = [0., 0., 0., .25]
        self.mainholder = metawidget.widget
        self.mainholder.base_offset = tween.AnimatableMixin(self.menu_x,
                                                       self.menu_y)
        self.mainholder.horizontal = True
        self.mainholder.spacing = self.panel_x - self.menu_x
        self.mainholder.buffer_display = 0
        self.menu_widget = ui.WidgetHolder(spacing=self.item_spacing\
                                                + self.back_button_sep,
                                           buffer_display=0)
        self.desc_widget = ui.Label(bg=InventoryBaseScreen.active_button_bg,
                                    bg_rect=[
                                        0., 0.,
                                        self.panel_w, self.panel_h],
                                    text_rect=[
                                        self.desc_padding, self.desc_padding,
                                        self.panel_w - self.desc_padding * 2,
                                        self.panel_h - self.desc_padding * 2],
                                    text="You should not see this",
                                    text_color=[0, 0, 0, 1],
                                    font=ui.default_font,
                                    scale=InventoryBaseScreen.text_scale,
                                    alignment=text.LEFT_TOP)
        self.mainholder.widgets += [self.menu_widget, self.desc_widget]
        
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
        
        is_big = len(self.slot) >= self.scroll_threshold
        self.menu_widget.scroll = is_big
        self.menu_widget.buffer_display = 1 if is_big else 0
        self.menu_widget.zero_point = self.scroll_zero_point if is_big else 0
        
        if self.menu_widget.selection >= len(self.slot) and len(self.slot) > 0:
            self.menu_widget.selection = len(self.slot) - 1
            self.menu_widget.offset.y = -self.menu_widget.selection\
                * self.menu_widget.spacing
        self.menu_widget.widgets.clear()
            
        for itm, count in self.slot.items():
            i = len(self.menu_widget.widgets)
            
            # Activation button
            active_color = [1., 0., 1., 1.]
            inactive_color = [.1, .1, .1, 1.]
            # Separate colors for equipped stuff
            if itm.equippable:
                equipment = cast(item.EquipableItem, itm)
                if self.inventory.equipped(equipment):
                    inactive_color = [1., .5, .5, 1.]
                    active_color = [.5, .2, 1., 1.]
            button = ui.build_button_widget(
                itm.name,
                [self.item_name_margin, 0,
                    self.item_name_size, self.item_row_height],
                InventoryBaseScreen.text_scale,
                (self.item_name_padding, self.item_name_padding),
                lambda _, i=i: self._on_button_press(i), # type: ignore
                active_color,
                inactive_color,
                text.CENTER_CENTER)
            
            # Preview icon
            icon = ui.Label(itm.icon,
                            [self.icon_x, 0., self.icon_size, self.icon_size])
            
            # X quantity indicator
            quantity = ui.Label(text=f'x{count}',
                                text_rect=[0.,
                                           0.,
                                           self.menu_w - self.item_name_size,
                                           self.item_row_height],
                                font=ui.default_font,
                                text_color=[0, 0, 0, 1],
                                scale = InventoryBaseScreen.text_scale)
            
            # Row 0: Name - quantity
            # Row 1: -----Icon------
            row_0 = ui.WidgetHolder(spacing=self.item_name_size\
                                        + self.item_name_margin * 2,
                                    horizontal=True,
                                    buffer_display=0)
            row_0.widgets += [button, quantity]
            
            bg_label = ui.Label(bg=InventoryBaseScreen.active_button_bg,
                                bg_rect=[0, 0, self.menu_w,
                                    self.icon_size + self.item_row_height])
            mini_holder = ui.WidgetHolder(spacing=self.item_row_height,
                                          buffer_display=0,
                                          background=bg_label)
            mini_holder.widgets += [row_0, icon]
            self.menu_widget.widgets.append(mini_holder)
        
        # Back button
        self.back_button = ui.build_button_widget(
            "Back",
            [0, 0,
             self.icon_size + 2 * self.icon_x,
             self.item_row_height],
            InventoryBaseScreen.header_scale,
            (InventoryBaseScreen.button_text_padding_x,
             InventoryBaseScreen.button_text_padding_y),
            lambda _: self._trigger_pop(),
            alignment=text.CENTER_CENTER,
            active_bg_sprite=InventoryBaseScreen.active_button_bg,
            inactive_bg_sprite=InventoryBaseScreen.inactive_button_bg)
        
        self.menu_widget.widgets.append(self.back_button)
    
    def render_gamestate(self, delta_time, renderer):
        if self.obscured:
            # print('submenu obscured')
            return
        if len(self.slot) == 0:
            text = "Nothing here..."
        elif self.menu_widget.selection == len(self.slot):
            text = "Return to previous menu"
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
    button_width: ClassVar[float] = 225.
    button_height: ClassVar[float] = 120.
    button_spacing: ClassVar[float] = 30.
    button_margin_x: ClassVar[float] = 30.
    button_margin_y: ClassVar[float] = 30.
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        metawidget = self.widget
        metawidget.reset_scr = [0., 0., 0., .25]
        mainholder = metawidget.widget
        mainholder.spacing = ItemSlotSubscreen.panel_x
        mainholder.buffer_display = 0
        mainholder.horizontal = True
        self.obscures = False
        self.holder = ui.WidgetHolder(
            spacing=self.button_height + self.button_spacing,
            buffer_display=0,
            scroll=False)
        self.holder.base_offset.x = ItemSlotSubscreen.menu_w\
            + ItemSlotSubscreen.back_button_sep
        self.holder.base_offset.y = ItemSlotSubscreen.panel_h\
            + ItemSlotSubscreen.back_button_sep
        self.desc_label = ui.Label(text="",
                                   bg=InventoryBaseScreen.active_button_bg,
                                   bg_rect=[
                                       0., 0.,
                                       ItemSlotSubscreen.panel_w,
                                       ItemSlotSubscreen.panel_h],
                                   text_rect=[
                                       ItemSlotSubscreen.desc_padding,
                                       ItemSlotSubscreen.desc_padding,
                                       ItemSlotSubscreen.panel_w\
                                          -2*ItemSlotSubscreen.desc_padding,
                                       ItemSlotSubscreen.panel_h\
                                          -2*ItemSlotSubscreen.desc_padding],
                                    text_color=[0, 0, 0, 1],
                                   font=ui.default_font,
                                   scale=InventoryBaseScreen.text_scale,
                                   alignment=text.LEFT_TOP)
        # mainholder.widgets += [self.holder, self.desc_label] # For when the description label is displayed, superfluous tho
        mainholder.widgets.append(self.holder)
        margins = (self.button_margin_x, self.button_margin_y)
        self.button_use = ui.build_button_widget(
            "Use",
            [*margins, self.button_width, self.button_height],
            None, #InventoryBaseScreen.header_scale,
            margins,
            lambda _: self.use(),
            alignment=text.CENTER_CENTER,
            active_bg_sprite=InventoryBaseScreen.active_button_bg,
            inactive_bg_sprite=InventoryBaseScreen.inactive_button_bg)
        self.button_equip = ui.build_button_widget(
            "Equip",
            [*margins, self.button_width, self.button_height],
            None, #InventoryBaseScreen.header_scale,
            margins,
            lambda _: self.equip(),
            alignment=text.CENTER_CENTER,
            active_bg_sprite=InventoryBaseScreen.active_button_bg,
            inactive_bg_sprite=InventoryBaseScreen.inactive_button_bg)
        self.button_toss = ui.build_button_widget(
            "Toss",
            [*margins, self.button_width, self.button_height],
            None, #InventoryBaseScreen.header_scale,
            margins,
            lambda _: self.toss(),
            alignment=text.CENTER_CENTER,
            active_bg_sprite=InventoryBaseScreen.active_button_bg,
            inactive_bg_sprite=InventoryBaseScreen.inactive_button_bg)
        self.button_back = ui.build_button_widget(
            "Back",
            [*margins, self.button_width, self.button_height],
            None, #InventoryBaseScreen.header_scale,
            margins,
            lambda _: self._trigger_pop(),
            alignment=text.CENTER_CENTER,
            active_bg_sprite=InventoryBaseScreen.active_button_bg,
            inactive_bg_sprite=InventoryBaseScreen.inactive_button_bg)
    
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
            self.holder.widgets.append(self.button_use)
        if self.item.equippable:
            equipment = cast(item.EquipableItem, self.item)
            if self.inventory.equipped(equipment):
                self.button_equip.active.widget.text = "Unequip"
                self.button_equip.inactive.widget.text = "Unequip"
            else:
                self.button_equip.active.widget.text = "Equip"
                self.button_equip.inactive.widget.text = "Equip"
            self.holder.widgets.append(self.button_equip)
        if self.item.tossable:
            tossable = True
            if self.item.equippable:
                equipment = cast(item.EquipableItem, self.item)
                tossable =\
                    self.inventory[equipment.equip_slot] is not equipment
            if tossable:
                self.holder.widgets.append(self.button_toss)
        self.holder.widgets.append(self.button_back)
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
        if len(self.manager.state_stack) >= 4:
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
    start_y: ClassVar[float] = 1080 - 350
    end_y: ClassVar[float] = 1080
    width: ClassVar[float] = 1440
    padding: ClassVar[float] = 60
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obscures = True
        metawidget = self.widget
        metawidget.reset_scr = [0., 0., 0., .25]
        self.holder = metawidget.widget
        self.textbox = ui.Label(bg=InventoryBaseScreen.active_button_bg,
                                bg_rect=[
                                    0, self.start_y, self.width,
                                    self.end_y - self.start_y],
                                text="",
                                text_rect=[
                                    self.padding, self.start_y + self.padding,
                                    self.width - self.padding * 2,
                                    self.end_y - self.start_y\
                                        - self.padding * 2],
                                    text_color=[0, 0, 0, 1],
                                font=ui.default_font,
                                scale=InventoryBaseScreen.text_scale,
                                alignment=text.LEFT_TOP)
        button = ui.TwoLabelButton(active=self.textbox,
                                   inactive=self.textbox,
                                   command=lambda _: self._trigger_pop())
        self.holder.widgets.append(button)
    
    def _build_message(self, msg: str):
        self.textbox.text = msg
    
    def _trigger_pop(self):
        self.die()

_itemslotsubscreens: Dict[item.ItemSlot, 'ItemSlotSubscreen']
_itemusescreen: ItemUseConfirmation
_usetossscreen: UseTossScreen