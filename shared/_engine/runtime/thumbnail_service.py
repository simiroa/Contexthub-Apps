from pathlib import Path
from PySide6.QtCore import QObject, Signal, QRunnable

from .media_runtime import MediaRuntime

class ThumbnailWorkerSignals(QObject):
    finished = Signal(object, object)  # path, PIL.Image
    error = Signal(object, str)        # path, error message

class ThumbnailWorker(QRunnable):
    def __init__(self, path, load_func):
        super().__init__()
        self.path = path
        self.load_func = load_func
        self.signals = ThumbnailWorkerSignals()
        
    def run(self):
        try:
            runtime = MediaRuntime()
            cache_key = f"thumb_{self.path}"
            
            # Check cache
            media_obj = runtime.get_cache(cache_key)
            if not media_obj:
                # Load using the provided app-specific loader
                media_obj = self.load_func(self.path)
                if media_obj:
                    runtime.put_cache(cache_key, media_obj)
                    
            self.signals.finished.emit(self.path, media_obj)
        except Exception as e:
            self.signals.error.emit(self.path, str(e))

def request_thumbnail(path, load_func, callback):
    """
    Requests a thumbnail asynchronously using the global thread pool and cache.
    :param path: The file path (str or Path)
    :param load_func: A callable that takes a path and returns a PIL.Image (or None).
                      MUST NOT create Qt GUI objects (QPixmap etc.) — runs on a worker thread.
    :param callback: A callable(path, pil_image) called on the main thread after load completes.
                     Convert PIL → QPixmap inside the callback (main thread only).
    """
    runtime = MediaRuntime()
    cache_key = f"thumb_{path}"
    
    # Fast path: already in cache
    media_obj = runtime.get_cache(cache_key)
    if media_obj:
        callback(path, media_obj)
        return
        
    worker = ThumbnailWorker(path, load_func)
    worker.signals.finished.connect(lambda p, obj: callback(p, obj))
    # We could optionally connect the error signal here if needed.
    runtime.thread_pool.start(worker)
