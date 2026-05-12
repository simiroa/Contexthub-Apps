from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple, Dict, TYPE_CHECKING
from PySide6.QtCore import QObject, QThread, Signal

if TYPE_CHECKING:
    import numpy as np
    from PIL import Image

# Heavy imports (numpy, PIL, compare_core) are deferred to first use so the
# window can paint without paying for them up front.
compare_core = None  # type: ignore[assignment]


def _ensure_compare_core():
    global compare_core
    if compare_core is not None:
        return compare_core
    try:
        import features.image.compare_core as _cc
    except ImportError:
        try:
            import compare_core as _cc  # type: ignore[no-redef]
        except ImportError:
            from . import compare_core as _cc  # type: ignore[no-redef]
    compare_core = _cc
    return compare_core

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
        self.image_cache: Dict[str, "np.ndarray"] = {}
        self.pil_cache: Dict[str, "Image.Image"] = {}
        self.cache_order: List[str] = []  # Track insertion order for LRU eviction

    def load_image(self, path: str, channel: str = "RGB"):
        cache_key = f"{path}_{channel}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        cc = _ensure_compare_core()
        arr = cc.load_image(path, channel)
        if arr is not None:
            self.image_cache[cache_key] = arr
            if cache_key not in self.cache_order:
                self.cache_order.append(cache_key)
            self._evict_cache()
        return arr

    def get_pil_image(self, path: str, channel: str = "RGB"):
        cache_key = f"{path}_{channel}"
        if cache_key in self.pil_cache:
            return self.pil_cache[cache_key]
        arr = self.load_image(path, channel)
        if arr is not None:
            cc = _ensure_compare_core()
            pil = cc.array_to_pil(arr)
            self.pil_cache[cache_key] = pil
            return pil
        return None

    def get_exr_channels(self, path: str) -> List[str]:
        if Path(path).suffix.lower() == ".exr":
            cc = _ensure_compare_core()
            return cc.get_exr_channels(path)
        return []

    def compute_metrics(self, path_a: str, path_b: str, channel: str) -> Tuple[Optional[float], Optional[int]]:
        img_a = self.load_image(path_a, channel)
        img_b = self.load_image(path_b, channel)
        if img_a is not None and img_b is not None:
            cc = _ensure_compare_core()
            ssim = cc.compute_ssim(img_a, img_b)
            _, diff_count = cc.compute_diff(img_a, img_b)
            return ssim, diff_count
        return None, None

    def get_diff_visualization(self, path_a: str, path_b: str, channel: str):
        """Compute and return diff visualization as PIL Image."""
        img_a = self.load_image(path_a, channel)
        img_b = self.load_image(path_b, channel)
        if img_a is not None and img_b is not None:
            cc = _ensure_compare_core()
            diff_arr, _ = cc.compute_diff(img_a, img_b)
            return cc.array_to_pil(diff_arr)
        return None

    def _evict_cache(self):
        """FIFO eviction: keep 20 most recently inserted, drop oldest."""
        MAX_CACHE_SIZE = 20
        if len(self.image_cache) > MAX_CACHE_SIZE:
            # Remove oldest items until under limit
            items_to_remove = self.cache_order[:-MAX_CACHE_SIZE]
            for key in items_to_remove:
                if key in self.image_cache:
                    del self.image_cache[key]
                if key in self.pil_cache:
                    del self.pil_cache[key]
            self.cache_order = self.cache_order[-MAX_CACHE_SIZE:]
