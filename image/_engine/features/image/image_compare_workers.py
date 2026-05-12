from PySide6.QtCore import QObject, QRunnable, Signal
from pathlib import Path
from typing import Optional
from PIL import Image


class ImageLoadWorkerSignals(QObject):
    """Signals for image loading worker."""
    finished = Signal(tuple)  # (path, pil_image, channel, task_type)
    error = Signal(str)


class ImageLoadWorker(QRunnable):
    """Load single image asynchronously in thread pool."""

    def __init__(self, service, path: Path, channel: str = "RGB", task_type: str = "load"):
        super().__init__()
        self.service = service
        self.path = path
        self.channel = channel
        self.task_type = task_type
        self.signals = ImageLoadWorkerSignals()

    def run(self):
        try:
            if self.task_type == "load":
                pil = self.service.get_pil_image(str(self.path), self.channel)
                self.signals.finished.emit((self.path, pil, self.channel, "load"))
            elif self.task_type == "thumbnail":
                pil = self.service.get_pil_image(str(self.path), self.channel)
                if pil:
                    thumb = pil.copy()
                    thumb.thumbnail((200, 200))
                    pil = thumb
                self.signals.finished.emit((self.path, pil, self.channel, "thumbnail"))
            elif self.task_type == "metrics":
                if hasattr(self, 'path_b') and self.path_b:
                    ssim, diff = self.service.compute_metrics(str(self.path), str(self.path_b), self.channel)
                    self.signals.finished.emit(((self.path, self.path_b), (ssim, diff), "metrics"))
        except Exception as e:
            self.signals.error.emit(f"Failed to process {self.path}: {str(e)}")


class DiffVisualizationWorker(QRunnable):
    """Compute difference visualization asynchronously."""

    def __init__(self, service, path_a: Path, path_b: Path, channel: str = "RGB"):
        super().__init__()
        self.service = service
        self.path_a = path_a
        self.path_b = path_b
        self.channel = channel
        self.signals = ImageLoadWorkerSignals()

    def run(self):
        try:
            diff_img = self.service.get_diff_visualization(str(self.path_a), str(self.path_b), self.channel)
            self.signals.finished.emit((self.path_a, diff_img, self.channel, "diff"))
        except Exception as e:
            self.signals.error.emit(f"Failed to compute diff: {str(e)}")
