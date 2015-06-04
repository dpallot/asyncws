__all__ = ['ClosedException', 'ProtocolError']

class ProtocolError(Exception):
    pass

class ClosedException(Exception):
    
    status = None
    reason = None
    
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason
    
    def __str__(self):
        return self.reason