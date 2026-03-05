import customtkinter as ctk
from PIL import Image
from pathlib import Path
import os

class IconManager:
    _cache = {}

    @staticmethod
    def load_icon(path_str: str, size=(20, 20), fallback_text="?"):
        """
        Robustly load an icon from a path string.
        Handles relative paths (relative to Project Root), absolute paths, and missing files.
        Returns: ctk.CTkImage or None
        """
        if not path_str:
            return None
            
        # Check cache
        cache_key = (path_str, size)
        if cache_key in IconManager._cache:
            return IconManager._cache[cache_key]
            
        try:
            path = Path(path_str)
            
            # If absolute, use as is
            if not path.is_absolute():
                # Resolve relative to project root
                # structure: src/manager/helpers/icons.py -> ../../../root
                root_dir = Path(__file__).resolve().parent.parent.parent.parent
                path = root_dir / path_str
            
            # 2. Check existence
            if not path.exists():
                return None
                
            # 3. Open
            pil_img = Image.open(path)
            
            # Optimization: Resize source image using high-quality filter
            # This reduces memory usage if the source is huge (e.g. 4K wallpaper used as icon)
            # and improves visual quality compared to simple scaling.
            pil_img = pil_img.resize(size, Image.Resampling.LANCZOS)
            
            # Create CTkImage (size is display size, but we match it for 1:1 crispness)
            img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
            
            # Cache it
            IconManager._cache[cache_key] = img
            return img
            
        except Exception:
            return None

    @staticmethod
    def get_category_icon(cat_name: str, settings: dict):
        # Implementation for default icons later
        return None
