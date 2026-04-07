from pathlib import Path
from typing import List, Optional, Tuple, Dict
import numpy as np
from PIL import Image
from PySide6.QtCore import QObject, QThread, Signal

# Import core logic from relative or absolute features.image
try:
    import features.image.compare_core as compare_core
except ImportError:
    try:
        import compare_core
    except ImportError:
        from . import compare_core

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

class ImageLoadWorker(QObject):
    finished = Signal(tuple)  # (path, pil_image, type)
    error = Signal(str)

    def __init__(self, service, path, channel="RGB", task_type="load"):
        super().__init__()
        self.service = service
        self.path = path
        self.channel = channel
        self.task_type = task_type
        self.path_b = None

    def run(self):
        try:
            if self.task_type == "load":
                pil = self.service.get_pil_image(self.path, self.channel)
                self.finished.emit((self.path, pil, "load"))
            elif self.task_type == "metrics":
                ssim, diff = self.service.compute_metrics(self.path, self.path_b, self.channel)
                self.finished.emit(((self.path, self.path_b), (ssim, diff), "metrics"))
        except Exception as e:
            self.error.emit(str(e))

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
