from collections import OrderedDict
from PySide6.QtCore import QThreadPool, QObject, QMutex, QMutexLocker

class MediaRuntime:
    """
    Singleton class managing a global thread pool and LRU cache for media (images, etc).
    This ensures that multiple apps running in the same process do not duplicate caches or thread pools.
    """
    _instance = None
    _mutex = QMutex()

    def __new__(cls):
        with QMutexLocker(cls._mutex):
            if cls._instance is None:
                cls._instance = super(MediaRuntime, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    @classmethod
    def instance(cls):
        return cls()

    def _init(self):
        self.thread_pool = QThreadPool.globalInstance()
        self._cache_mutex = QMutex()
        self._cache = OrderedDict()
        self.max_cache_size = 100

    def get_cache(self, key):
        with QMutexLocker(self._cache_mutex):
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def put_cache(self, key, value):
        with QMutexLocker(self._cache_mutex):
            self._cache[key] = value
            self._cache.move_to_end(key)
            if len(self._cache) > self.max_cache_size:
                self._cache.popitem(last=False)

    def clear_cache(self):
        with QMutexLocker(self._cache_mutex):
            self._cache.clear()
