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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_events = []
        self.event_queue = deque()
    
    def start_event(self, event: 'Event') -> None:
        """Add an event to currently active events.
        It will start processing immediately if called from an event"""
        self.active_events.append(event)
        
    def queue_event(self, event: 'Event') -> None:
        """Queue an event to run once the active_events have run out"""
        self.event_queue.append(event)
    
    def dispatch(self, state: 'GameState') -> None:
        """Step all active events and remove those that are done"""
        if len(self.active_events) == 0 and len(self.event_queue) != 0:
            self.active_events.append(self.event_queue.popleft())
        results = []
        while len(results) < len(self.active_events):
            results.append(self.active_events[len(results)].step(state))
        self.active_events[:] = [e for i, e in enumerate(self.active_events)
                                 if results[i]]
    
    def events_left(self) -> int:
        """Number of incomplete events"""
        return len(self.active_events) + len(self.event_queue)

@dataclass
class Event(AwaiterMixin, AwaitableMixin):
    """
    Each command contains a function that returns a generator when provided
    the gamestate and event itself. The generator is then called each frame
    until it yields False, at which point it is considered complete
    """
    generator: Callable[[EventManagerMixin, 'Event'],
                        Generator[bool, None, None]]
    data: Dict[str, Any] = field(default_factory=dict)
    _generator: Generator[bool, None, None] = field(init=False, default=None)
    
    def __post_init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def step(self, state: 'GameState') -> bool:
        """executes the next step if this event is ready to continue
        Returns True iff the event has not yet concluded"""
        if self._generator is None:
            self._generator = self.generator(state, self)
        continuing = next(self._generator)
        if not continuing:
            self.conclude()
            return False
        return True
    