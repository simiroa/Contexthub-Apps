from PySide6.QtCore import QObject, Signal, QRunnable

class PreviewWorkerSignals(QObject):
    result = Signal(object, str)

class ProcessLivePreviewWorker(QRunnable):
    def __init__(self, service, path, params):
        super().__init__()
        self.service = service
        self.path = path
        self.params = params
        self.signals = PreviewWorkerSignals()

    def run(self):
        try:
            res_pil = self.service.get_processed_preview_pil(self.path, self.params)
            nw, nh = res_pil.size
            self.signals.result.emit(res_pil, f"→ {nw}x{nh}")
        except Exception as e:
            print(f"Live preview worker error: {e}")
