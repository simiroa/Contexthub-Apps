from PySide6.QtCore import QObject, QRunnable, Signal
from pathlib import Path

class __APP_CLASS_NAME__WorkerSignals(QObject):
    result = Signal(object, str) # result_data, info_text
    error = Signal(str)

class __APP_CLASS_NAME__ProcessWorker(QRunnable):
    def __init__(self, service, path: Path, params: dict):
        super().__init__()
        self.service = service
        self.path = path
        self.params = params
        self.signals = __APP_CLASS_NAME__WorkerSignals()

    def run(self):
        try:
            # Perform background processing (e.g., Image/Audio processing)
            # res = self.service.do_something(self.path, self.params)
            # self.signals.result.emit(res, "Success")
            pass
        except Exception as e:
            self.signals.error.emit(str(e))
