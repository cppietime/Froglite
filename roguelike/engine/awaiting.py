"""
awaiting.py
Some mixins for awaitable types
"""

class AwaiterMixin:
    """Something that can wait on something else"""
    def __init__(self):
        super().__init__()
        self.locks = 0
    
    def lock(self):
        """Make this wait"""
        self.locks += 1
    
    def unlock(self):
        """Release its wait"""
        self.locks -= 1
    
    def locked(self):
        """Returns True if this is waiting"""
        return self.locks > 0

class AwaitableMixin:
    """Something that can be awaited"""
    def __init__(self):
        super().__init__()
        self.awaiters = []
    
    def attach(self, awaiter):
        """Attach an awaiter to await this"""
        self.awaiters.append(awaiter)
        awaiter.lock()
    
    def conclude(self):
        """Unlock all awaiters awaiting this"""
        for awaiter in self.awaiters:
            awaiter.unlock()