"""
event_manager.py
Event queue and management
"""

from collections import deque
from dataclasses import (
    dataclass,
    field
)
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Protocol,
    Sequence,
    Tuple
)

from .awaiting import *

class EventManagerMixin:
    """A mixin for types that can manage events, such as a game state"""
    def __init__(self):
        super().__init__()
        self.active_events = []
        self.event_queue = deque()
    
    def start_event(self, event):
        """Add an event to currently active events.
        It will start processing immediately if called from an event"""
        self.active_events.append(event)
        
    def queue_event(self, event):
        """Queue an event to run once the active_events have run out"""
        self.event_queue.append(event)
    
    def dispatch(self, state):
        """Step all active events and remove those that are done"""
        if len(self.active_events) == 0 and len(self.event_queue) != 0:
            self.active_events.append(self.event_queue.popleft())
        results = []
        while len(results) < len(self.active_events):
            results.append(self.active_events[len(results)].step(state))
            # results.append(next(self.active_events[len(results)]))
        self.active_events[:] = [e for i, e in enumerate(self.active_events) if results[i]]
    
    def events_left(self):
        """Number of incomplete events"""
        return len(self.active_events) + len(self.event_queue)

@dataclass
class Event(AwaiterMixin, AwaitableMixin):
    """
    Each command in the event's sequence contains a function that receives a gamestate, the event
    itself then any other parameters, which are contained in the extra tuple
    """
    # commands: Sequence[Tuple[Callable, Tuple]]
    generator: Callable[[EventManagerMixin, 'Event'], Generator[bool, None, None]]
    data: Dict[str, Any] = field(default_factory=dict)
    _generator: Generator[bool, None, None] = field(init=False, default=None)
    # index: int = 0
    
    def __post_init__(self):
        super().__init__()
    
    def step(self, state):
        """executes the next step if this event is ready to continue
        Returns True iff the event has not yet concluded"""
        # # if self.locked():
            # # return True
        # while not self.locked() and self.index < len(self.commands):
            # command = self.commands[self.index]
            # func, params = command
            # func(state, self, *params)
            # self.index += 1
        # # This will be reached only if the event is locked or it has completed
        # if self.locked():
            # return True
        # self.conclude()
        # return False
        if self._generator is None:
            self._generator = self.generator(state, self)
        continuing = next(self._generator)
        if not continuing:
            self.conclude()
            return False
        return True
    