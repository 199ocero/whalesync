"""
Logging utility for TUI
Redirects print/logging to a queue that the TUI can consume
"""

import asyncio
from typing import Callable, Optional
from collections import deque
import time

class TUILogger:
    _instance = None
    _log_queue: asyncio.Queue = asyncio.Queue()
    _callback: Optional[Callable[[str], None]] = None
    _paused: bool = False
    _error_timestamps: deque = deque(maxlen=10)  # Track last 10 errors
    _error_threshold: int = 5  # Max errors per second
    _suppressed_count: int = 0

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def log(self, message: str):
        """Log a message to the TUI (and print as backup)"""
        # If paused, don't log
        if self._paused:
            return
        
        # Check if this is an error message
        is_error = "Error" in message or "error" in message
        
        if is_error:
            current_time = time.time()
            self._error_timestamps.append(current_time)
            
            # Check error rate (errors in last second)
            recent_errors = sum(1 for t in self._error_timestamps if current_time - t < 1.0)
            
            if recent_errors > self._error_threshold:
                self._suppressed_count += 1
                if self._suppressed_count == 1:
                    # Log once that we're suppressing
                    if self._callback:
                        self._callback("⚠️  Too many errors - suppressing further error messages. Press 'p' to pause feed.")
                return
        else:
            # Reset suppression counter on non-error messages
            if self._suppressed_count > 0:
                if self._callback:
                    self._callback(f"ℹ️  Suppressed {self._suppressed_count} error messages")
                self._suppressed_count = 0
        
        # If callback is registered (TUI running), send to it
        if self._callback:
            self._callback(message)

    def set_callback(self, callback: Callable[[str], None]):
        self._callback = callback
    
    def pause(self):
        """Pause logging"""
        self._paused = True
    
    def resume(self):
        """Resume logging"""
        self._paused = False
        self._suppressed_count = 0
    
    def is_paused(self) -> bool:
        """Check if logging is paused"""
        return self._paused

# Global logger
logger = TUILogger.get_instance()

def tui_print(message: str):
    """Helper to replace print() in strategies"""
    logger.log(message)
