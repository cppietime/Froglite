from collections import defaultdict
from dataclasses import (
    dataclass,
    field
)
from enum import Enum
import pygame as pg
from typing import (
    Dict,
    List,
    Tuple
)

class KeyState(Enum):
    PRESSED = 0
    DOWN = 1
    UP = 2

MOUSEFOCUS = 0
INPUTFOCUS = 1
APPACTIVE = 2

@dataclass
class InputState:
    keys: Dict[int, Dict[KeyState, bool]] = field(default_factory=lambda:\
        defaultdict(lambda:\
            defaultdict(lambda: False)))
    buttons: Dict[int, Dict[KeyState, bool]] = field(default_factory=lambda:\
        defaultdict(lambda:\
            defaultdict(lambda: False)))
    focus: Dict[int, Dict[KeyState, bool]] = field(default_factory=lambda:\
        defaultdict(lambda:\
            defaultdict(lambda: False)))
    mouse_pos: Tuple[int, int] = (0, 0)
    mouse_delta: Tuple[int, int] = (0, 0)
    mouse_focus: bool = True
    input_focus: bool = True
    app_active: bool = True
    
    def reset_input(self):
        for state in self.keys.values():
            state[KeyState.UP] = state[KeyState.DOWN] = False
        for state in self.buttons.values():
            state[KeyState.UP] = state[KeyState.DOWN] = False
        for state in self.focus.values():
            state[KeyState.UP] = state[KeyState.DOWN] = False
    
    def process_event(self, event):
        if event.type == pg.ACTIVEEVENT and 'state' in event.dict:
            if event.gain == 0:
                self.focus[event.state][KeyState.PRESSED] = False
                self.focus[event.state][KeyState.UP] = True
            else:
                self.focus[event.state][KeyState.PRESSED] = True
                self.focus[event.state][KeyState.DOWN] = True
        elif event.type == pg.MOUSEBUTTONUP:
            self.buttons[event.button][KeyState.PRESSED] = False
            self.buttons[event.button][KeyState.UP] = True
        elif event.type == pg.MOUSEBUTTONDOWN:
            self.buttons[event.button][KeyState.PRESSED] = True
            self.buttons[event.button][KeyState.DOWN] = True
        elif event.type == pg.KEYUP:
            self.keys[event.key][KeyState.PRESSED] = False
            self.keys[event.key][KeyState.UP] = True
        elif event.type == pg.KEYDOWN:
            self.keys[event.key][KeyState.PRESSED] = True
            self.keys[event.key][KeyState.DOWN] = True

    def record_mouse(self):
        self.mouse_pos = pg.mouse.get_pos()
        self.mouse_delta = pg.mouse.get_rel()
        # print(self.keys)
        # print(self.buttons)