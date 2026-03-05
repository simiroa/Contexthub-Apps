"""
Gemini Image Tools - History Manager Module
Manages undo/redo history for image editing.
"""
import cv2
import numpy as np
from pathlib import Path
import time

from .core import imread_unicode


class HistoryManager:
    """Manages undo/redo history by saving images to a cache directory."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.history = []  # List of image paths
        self.current_index = -1
        
    def add(self, image: np.ndarray):
        """Add a new image state to history."""
        # Save to cache
        timestamp = int(time.time() * 1000)
        filename = f"history_{timestamp}.png"
        path = self.cache_dir / filename
        cv2.imwrite(str(path), image)
        
        # If we are in the middle of history, truncate future
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]
            
        self.history.append(path)
        self.current_index = len(self.history) - 1
        
    def undo(self):
        """Undo to previous state. Returns the image or None."""
        if self.can_undo():
            self.current_index -= 1
            return self._load_current()
        return None
        
    def redo(self):
        """Redo to next state. Returns the image or None."""
        if self.can_redo():
            self.current_index += 1
            return self._load_current()
        return None
        
    def _load_current(self):
        """Load the current history image."""
        if 0 <= self.current_index < len(self.history):
            path = self.history[self.current_index]
            if path.exists():
                return imread_unicode(str(path))
        return None
        
    def can_undo(self):
        """Check if undo is available."""
        return self.current_index > 0
    
    def can_redo(self):
        """Check if redo is available."""
        return self.current_index < len(self.history) - 1
    
    def clear(self):
        """Clear all history and delete cached files."""
        for path in self.history:
            try:
                if path.exists():
                    path.unlink()
            except:
                pass
        self.history = []
        self.current_index = -1
