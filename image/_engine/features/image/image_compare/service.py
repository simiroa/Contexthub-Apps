from pathlib import Path
from typing import List, Optional, Tuple, Dict
import numpy as np
from PIL import Image

# Import core logic from existing compare_core
import features.image.compare_core as compare_core
try:
    from core.logger import setup_logger
except ModuleNotFoundError:
    try:
        from contexthub.core.logger import setup_logger
    except ModuleNotFoundError:
        import logging

        def setup_logger(name: str):
            logger = logging.getLogger(name)
            if not logger.handlers:
                logging.basicConfig(level=logging.INFO)
            return logger

logger = setup_logger("image_compare_service")

class ImageCompareService:
    def __init__(self):
        self.image_cache: Dict[str, np.ndarray] = {}
        self.pil_cache: Dict[str, Image.Image] = {}

    def load_image(self, path: str, channel: str = "RGB") -> Optional[np.ndarray]:
        cache_key = f"{path}_{channel}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        
        arr = compare_core.load_image(path, channel)
        if arr is not None:
            self.image_cache[cache_key] = arr
        return arr

    def get_pil_image(self, path: str, channel: str = "RGB") -> Optional[Image.Image]:
        cache_key = f"{path}_{channel}"
        if cache_key in self.pil_cache:
            return self.pil_cache[cache_key]
        
        arr = self.load_image(path, channel)
        if arr is not None:
            pil = compare_core.array_to_pil(arr)
            self.pil_cache[cache_key] = pil
            return pil
        return None

    def get_exr_channels(self, path: str) -> List[str]:
        if Path(path).suffix.lower() == ".exr":
            return compare_core.get_exr_channels(path)
        return []

    def compute_metrics(self, path_a: str, path_b: str, channel: str) -> Tuple[Optional[float], Optional[int]]:
        img_a = self.load_image(path_a, channel)
        img_b = self.load_image(path_b, channel)
        
        if img_a is not None and img_b is not None:
            ssim = compare_core.compute_ssim(img_a, img_b)
            _, diff_count = compare_core.compute_diff(img_a, img_b)
            return ssim, diff_count
        return None, None

    def get_diff_image(self, path_a: str, path_b: str, channel: str) -> Optional[Image.Image]:
        img_a = self.load_image(path_a, channel)
        img_b = self.load_image(path_b, channel)
        
        if img_a is not None and img_b is not None:
            diff_vis, _ = compare_core.compute_diff(img_a, img_b)
            return compare_core.array_to_pil(diff_vis)
        return None
