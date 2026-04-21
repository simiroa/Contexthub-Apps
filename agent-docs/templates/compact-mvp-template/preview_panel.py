from PySide6.QtCore import QTimer, QThreadPool
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from .workers import __APP_CLASS_NAME__ProcessWorker

class __APP_CLASS_NAME__PreviewPanel(QWidget):
    def __init__(self, service, thread_pool=None):
        super().__init__()
        self.service = service
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(300)
        self._preview_timer.timeout.connect(self._run_live_processing)
        
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.placeholder = QLabel("Drop files to start")
        self.placeholder.setStyleSheet("border: 2px dashed #444; color: #888;")
        self.placeholder.setMinimumHeight(200)
        layout.addWidget(self.placeholder)

    def refresh(self):
        """Full refresh when new files added"""
        path = self.service.state.preview_path
        if path:
            self.placeholder.setText(f"Previewing: {path.name}")
            self.refresh_live()

    def refresh_live(self):
        """Live refresh when params change"""
        self._preview_timer.start()

    def _run_live_processing(self):
        path = self.service.state.preview_path
        if not path: return
        
        params = self.service.state.parameter_values
        worker = __APP_CLASS_NAME__ProcessWorker(self.service, path, params)
        worker.signals.result.connect(self._on_preview_ready)
        self.thread_pool.start(worker)

    def _on_preview_ready(self, result_data, info):
        # Update UI with processed result
        self.placeholder.setText(f"Done: {info}")
