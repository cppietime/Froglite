from dataclasses import (
    dataclass,
    field
)
from typing import (
    cast,
    Any,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TYPE_CHECKING
)

from roguelike.engine import (
    assets,
    event_manager,
    sprite,
    text,
    tween
)
from roguelike.entities import (
    entity
)
from roguelike.states import ui
from roguelike.bag import (
    inventory_state,
    item
)

if TYPE_CHECKING:
    from roguelike.entities.player import PlayerEntity
    from roguelike.engine.gamestate import GameState
    from roguelike.engine.text import CharBank

class ChatPredicate(Protocol):
    def is_fulfilled(self, state: 'ChatPromptState') -> bool:
        pass
    
def parse_predicate(source: Dict[str, Any]) -> ChatPredicate:
    kind: str = cast(str, source['kind'])
    if kind == 'always':
        return AlwaysPredicate()
    elif kind == 'choice':
        num = cast(int, source['num'])
        return ChoicePredicate(num)
    elif kind == 'var':
        name = cast(str, source['name'])
        value: Any = source['value']
        comp = cast(str, source.get('function', '='))
        return VarPredicate(name, value, comp)
    elif kind == 'not':
        negative_dict = cast(Dict[str, Any], source['predicate'])
        negative = parse_predicate(negative_dict)
        return NotPredicate(negative)
    elif kind == 'and':
        p_list = cast(List[Dict[str, Any]], source['predicates'])
        predicates = map(parse_predicate, p_list)
        return AndPredicate(tuple(predicates))
    elif kind == 'or':
        p_list = cast(List[Dict[str, Any]], source['predicates'])
        predicates = map(parse_predicate, p_list)
        return OrPredicate(tuple(predicates))
    elif kind == 'has_item':
        item_name = cast(str, source['item'])
        amount = cast(int, source.get('amount', 1))
        return HasPredicate(item_name, amount)
    elif kind == 'action':
        action_dict = cast(Dict[str, Any], source['action'])
        action = parse_action(action_dict)
        return ActionPredicate(action)
    else:
        raise ValueError(f'{kind} is not a valid predicate type')

@dataclass
class AlwaysPredicate:
    def is_fulfilled(self, _: 'ChatPromptState') -> bool:
        return True

@dataclass
class ChoicePredicate:
    num: int
    
    def is_fulfilled(self, state: 'ChatPromptState') -> bool:
        return state.choice_menu.selection == self.num

@dataclass
class VarPredicate:
    varname: str
    value: Any
    comp: str
    
    def is_fulfilled(self, _: 'ChatPromptState') -> bool:
        value: Any = assets.variables[self.varname]
        if self.comp == '=':
            return value == self.value
        elif self.comp == '>':
            return value > self.value
        elif self.comp == '<':
            return value < self.value
        elif self.comp == '!=':
            return value != self.value
        elif self.comp == '>=':
            return value >= self.value
        elif self.comp == '<=':
            return value <= self.value
        raise ValueError(f'{self.comp} is not a valid comparison')

@dataclass
class NotPredicate:
    negative: ChatPredicate
    
    def is_fulfilled(self, state: 'ChatPromptState') -> bool:
        return not self.negative.is_fulfilled(state)

@dataclass
class AndPredicate:
    terms: Iterable[ChatPredicate]
    
    def is_fulfilled(self, state: 'ChatPromptState') -> bool:
        return all(map(lambda t: t.is_fulfilled(state), self.terms))

@dataclass
class OrPredicate:
    terms: Iterable[ChatPredicate]
    
    def is_fulfilled(self, state: 'ChatPromptState') -> bool:
        return any(map(lambda t: t.is_fulfilled(state), self.terms))

@dataclass
class HasPredicate:
    item_name: str
    amount: int
    
    def is_fulfilled(self, state: 'ChatPromptState') -> bool:
        return state.player.inventory[item.items[self.item_name]]\
            >= self.amount

@dataclass
class ActionPredicate:
    action: 'ChatAction'
    
    def is_fulfilled(self, state: 'ChatPromptState') -> bool:
        return self.action.perform_action(state)

class ChatAction(Protocol):
    def perform_action(self,
                       state: 'ChatPromptState') -> bool:
        pass

def parse_action(source: Dict[str, Any]) -> ChatAction:
    kind = cast(str, source['kind'])
    if kind == 'give':
        item_name = cast(str, source['item'])
        amount = cast(int, source.get('amount', 1))
        return GiveAction(item_name, amount)
    elif kind == 'take':
        item_name = cast(str, source['item'])
        amount = cast(int, source.get('amount', 1))
        return TakeAction(item_name, amount)
    elif kind == 'var':
        varname = cast(str, source['name'])
        value: Any = source['value']
        func: str = cast(str, source.get('function', '='))
        return VarAction(varname, value, func)
    else:
        raise ValueError(f'{kind} is not a valid action')

@dataclass
class GiveAction:
    item_name: str
    amount: int
    
    def perform_action(self,
                       state: 'ChatPromptState') -> bool:
        state.player.inventory.give_item(item.items[self.item_name],
                                         self.amount)
        return True

@dataclass
class TakeAction:
    item_name: str
    amount: int
    
    def perform_action(self,
                       state: 'ChatPromptState') -> bool:
        inventory = state.player.inventory
        itm = item.items[self.item_name]
        if inventory[itm] < self.amount:
            return False
        inventory.take_item(itm, self.amount)
        return True

@dataclass
class VarAction:
    varname: str
    value: Any
    func: str
    
    def perform_action(self,
                       state: 'ChatPromptState') -> bool:
        if self.func == '=':
            assets.variables[self.varname] = self.value
        elif self.func == '+':
            assets.variables[self.varname] += self.value
        elif self.func == '-':
            assets.variables[self.varname] -= self.value
        else:
            raise ValueError(f'{self.func} is not a valid function')
        return True

@dataclass
class ChatPrompt:
    """A single window of text and pointers to choices/next options"""
    message: str
    menu_choices: Optional[Sequence[str]] = None
    next_prompts: List[Tuple[ChatPredicate,
                             Optional['ChatPrompt']]] =\
        field(default_factory=list)
    icon: Optional[sprite.Sprite] = None
    actions: List[ChatAction] = field(default_factory=list)

class ChatPromptState(ui.MenuState):
    """The UI game state for speaking with NPCs"""
    start_y: ClassVar[float] = 1080 * 2 // 3
    height: ClassVar[float] = 1080 * 1 // 3
    start_x: ClassVar[float] = 0
    width: ClassVar[float] = 1440
    text_padding: ClassVar[float] = 40
    menu_height: ClassVar[float] = 150
    button_width: ClassVar[float] = 300
    menu_margins: ClassVar[float] = 20
    scroll_threshold: ClassVar[int] = 5
    scroll_zero_point: ClassVar[float] = 1440 / 320 / 2 - .5
    icon_y: ClassVar[float] = 50
    icon_size: ClassVar[float] = 400
    bg_sprite: ClassVar[sprite.Sprite]
    bg_button_active: ClassVar[sprite.Sprite]
    bg_button_inactive: ClassVar[sprite.Sprite]
    
    def __init__(self, *args, **kwargs):
        self.chat: 'ChatPrompt' = kwargs.pop('chat')
        self.player: 'PlayerEntity' = kwargs.pop('player')
        
        super().__init__(*args, **kwargs)
        
        self.bg_sprite = assets.Sprites.instance.button_active
        self.bg_button_active = assets.Sprites.instance.button_active
        self.bg_button_inactive = assets.Sprites.instance.button_inactive
        
        self.outer_holder = self.widget.widget
        self.outer_holder.buffer_display = 0
        self.outer_holder.scroll = False
        self.outer_holder.spacing = 0#self.icon_y - self.start_y
        self.holder = ui.WidgetHolder(buffer_display=0,
                                      scroll=False,
                                      spacing=0)
        self.holder.base_offset.y = self.start_y
        self.preview = ui.Label(bg=None, 
                                bg_rect=[(1440 - self.icon_size) / 2,
                                         1080,
                                         self.icon_size,
                                         self.icon_size])
        self.outer_holder.widgets += [self.holder, self.preview]
        self.callbacks_on_push.append(ChatPromptState.reset_on_push)
        self.chat_box_label = ui.Label(bg=self.bg_sprite,
                bg_rect=[0, 0, self.width, self.height],
                text_rect=[
                self.text_padding, self.text_padding,
                self.width - self.text_padding * 2,
                self.height - self.text_padding * 2],
                text_color=[0, 0, 0, 1],
                font=ui.default_font,
                scale=inventory_state.InventoryBaseScreen.text_scale,
                alignment=text.LEFT_TOP
            )
        self.chat_box_button = ui.TwoLabelButton(
            active=self.chat_box_label, inactive=self.chat_box_label,
            command=ChatPromptState.progress)
        self.choice_menu = ui.WidgetHolder(
            horizontal=True, spacing = self.button_width + self.menu_margins)
        self.menu_up: bool = False
    
    def reset_on_push(self) -> None:
        """Reset state before pushing the state"""
        self.update_chatbox()
        self.rise_up()
    
    def update_chatbox(self) -> None:
        """Update the catbox and icon to the current chat"""
        self.chat_box_button.enabled = True
        self.holder.widgets.clear()
        self.holder.widgets.append(self.chat_box_button)
        if self.chat.icon is not None:
            self.preview.bg = self.chat.icon
            self.preview.bg_rect[1] = 0
        else:
            self.preview.bg_rect[1] = 1080
        self.holder.selection = 0
        self.chat_box_label.text = self.chat.message
        self.menu_up = False
        for action in self.chat.actions:
            action.perform_action(self)
    
    def progress(self) -> None:
        """Called when the user makes a selection"""
        if self.chat.menu_choices is not None and not self.menu_up:
            """This is reached when the menu needs to be displayed"""
            self.switch_to_menu()
            return
        for predicate, prompt in (self.chat.next_prompts or ()):
            if not predicate.is_fulfilled(self):
                continue
            """A predicate for the next option that has been met"""
            if prompt is None:
                self._trigger_pop()
                return
            def _event(state, event):
                self.fall_down()
                while state.locked():
                    yield True
                self.chat = prompt
                self.update_chatbox()
                self.rise_up()
                while state.locked():
                    yield True
                yield False
            self.queue_event(event_manager.Event(_event))
            return
        self._trigger_pop()
    
    def switch_to_menu(self) -> None:
        """Bring up the current menu"""
        assert self.chat.menu_choices is not None
        self.choice_menu.widgets.clear()
        for i, choice in enumerate(self.chat.menu_choices):
            choice_button = ui.build_button_widget(
                txt=choice,
                rect=[0, 0, self.button_width, self.menu_height],
                scale=inventory_state.InventoryBaseScreen.text_scale,
                margins=(self.text_padding, self.text_padding),
                command=lambda _, i=i: self.made_menu_choice(i), # type: ignore
                alignment=text.CENTER_CENTER,
                active_bg_sprite=self.bg_button_active,
                inactive_bg_sprite=self.bg_button_inactive)
            self.choice_menu.widgets.append(choice_button)
        self.choice_menu.base_offset.y = 1080
        if len(self.chat.menu_choices) >= self.scroll_threshold:
            self.choice_menu.scroll = True
            self.choice_menu.buffer_display = 1
            self.choice_menu.zero_point = self.scroll_zero_point
        else:
            self.choice_menu.scroll = False
            self.choice_menu.buffer_display = 0
            self.choice_menu.zero_point = 0
        self.choice_menu.selection = 0
        self.holder.selection = 1 # Select the submenu
        self.holder.widgets.append(self.choice_menu)
        self.menu_up = True
        anim = tween.Animation([
            (0, tween.Tween(self.choice_menu.base_offset,
                        'y',
                        1080,
                        - self.menu_height,
                        .25))
        ])
        anim.attach(self)
        self.begin_animation(anim)
    
    def made_menu_choice(self, index: int) -> None:
        self.choice_menu.base_offset.y = 1080
        self.progress()
    
    def rise_up(self) -> None:
        self.outer_holder.base_offset.y = 1080
        anim = tween.Animation([
            (0,
             tween.Tween(self.outer_holder.base_offset,
                         'y',
                         1080,
                         0,#self.start_y,
                         .25))
        ])
        anim.attach(self)
        self.begin_animation(anim)
    
    def fall_down(self) -> None:
        self.outer_holder.base_offset.y = 0#self.start_y
        anim = tween.Animation([
            (0,
             tween.Tween(self.outer_holder.base_offset,
                         'y',
                         0,#self.start_y,
                         1080,
                         .25))
        ])
        anim.attach(self)
        self.begin_animation(anim)
    
    def _trigger_pop(self):
        self.fall_down()
        def _event(state, event):
            while state.locked():
                yield True
            self.die()
            yield False
        self.queue_event(event_manager.Event(_event))

class NPCEntity(entity.Entity):
    """Base class for entities that give dialog
    """
    interactable = True
    
    def __init__(self, *args, **kwargs):
        self.initial_prompt: ChatPrompt = kwargs.pop('chat')
        if 'anim' in kwargs:
            self.class_anim = kwargs.pop('anim')
        super().__init__(*args, passable=False, **kwargs)
        self.anim.speed = 0
    
    def interact(self,
                 current_state: 'GameState',
                 player: 'PlayerEntity') -> None:
        if self.anim is not None:
            if player.dungeon_pos[0] < self.dungeon_pos[0]:
                self.anim.direction = sprite.AnimDir.LEFT
            elif player.dungeon_pos[0] > self.dungeon_pos[0]:
                self.anim.direction = sprite.AnimDir.RIGHT
            elif player.dungeon_pos[1] < self.dungeon_pos[1]:
                self.anim.direction = sprite.AnimDir.UP
            elif player.dungeon_pos[1] > self.dungeon_pos[1]:
                self.anim.direction = sprite.AnimDir.DOWN
        new_state = ChatPromptState(chat=self.initial_prompt, player=player)
        def _event(state, event):
            while state.locked():
                yield True
            state.manager.push_state(new_state)
            yield False
        current_state.queue_event(event_manager.Event(_event))

chats: Dict[str, ChatPrompt] = {}

def init_chats() -> None:
    """Initializes chats"""
    source: Dict[str, Dict[str, Any]] = assets.residuals['chats']
    for name, value in source.items():
        msg = cast(str, value['message'])
        choices = cast(Optional[Sequence[str]],
                       value.get('choices', None))
        icon: Optional[sprite.Sprite] = None
        icon_name = cast(Optional[str], value.get('icon', None))
        if icon_name is not None:
            icon = assets.Sprites.instance.sprites[icon_name]
        action_list = cast(List[Dict[str, Any]], value.get('actions', []))
        # actions: List[ChatAction] = []
        # for action_dict in action_list:
            # actions.append(parse_action(action))
        actions: List[ChatAction] = list(map(parse_action, action_list))
        chat = ChatPrompt(message=msg,
                          menu_choices=choices,
                          next_prompts=[],
                          icon=icon,
                          actions=actions)
        chats[name] = chat
    # Load predicates and references
    for name, value in source.items():
        chat = chats[name]
        n_list = cast(Optional[Iterable[Dict[str, Any]]],
                      value.get('next', None))
        if n_list is None:
            continue
        prompt_list = chat.next_prompts
        for prompt in n_list:
            next_name = cast(Optional[str], prompt.get('name', None))
            if next_name == '':
                next_name = None
            if next_name is None:
                next_chat = None
            else:
                next_chat = chats[next_name]
            p_dict = cast(Dict[str, Any], prompt['predicate'])
            predicate = parse_predicate(p_dict)
            prompt_list.append((predicate, next_chat))