import os
import threading
import time
from pathlib import Path
from tkinter import messagebox

# Suppress Pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

try:
    import pygame
except ImportError:
    pygame = None

class AudioPlayer:
    """Utility class to handle audio playback using pygame with fallback to system player."""
    
    def __init__(self):
        self.is_playing = False
        self._current_path = None
        self._monitor_thread = None
        self._on_stop_callback = None

    @property
    def has_pygame(self):
        return pygame is not None

    def play(self, file_path, on_stop_callback=None):
        """Play audio file. If pygame is missing, opens with system default player."""
        if not file_path or not Path(file_path).exists():
            return False
            
        self._current_path = str(file_path)
        self._on_stop_callback = on_stop_callback

        if not self.has_pygame:
            # Fallback to system player
            try:
                os.startfile(self._current_path)
                return True
            except Exception as e:
                messagebox.showerror("Playback Error", f"Failed to open system player: {e}")
                return False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            
            pygame.mixer.music.load(self._current_path)
            pygame.mixer.music.play()
            self.is_playing = True
            
            # Start monitor thread
            self._monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
            self._monitor_thread.start()
            return True
        except Exception as e:
            # If pygame fails, try fallback
            print(f"Pygame playback failed: {e}. Trying system player...")
            try:
                os.startfile(self._current_path)
                return True
            except:
                messagebox.showerror("Playback Error", f"Failed to play audio: {e}")
                return False

    def stop(self):
        """Stop current playback."""
        if self.has_pygame and pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.is_playing = False

    def _monitor_playback(self):
        """Monitors when music reaches the end."""
        while self.is_playing:
            if self.has_pygame and pygame.mixer.get_init():
                if not pygame.mixer.music.get_busy():
                    break
            else:
                break
            time.sleep(0.2)
        
        self.is_playing = False
        if self._on_stop_callback:
            try:
                self._on_stop_callback()
            except:
                pass

def get_player():
    """Singleton instance helper if needed, but instance per window is also fine."""
    return AudioPlayer()
