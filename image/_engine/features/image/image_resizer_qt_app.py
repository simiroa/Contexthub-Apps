from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from contexthub.ui.qt.shell import qt_t

try:
    from PySide6.QtCore import QSettings, Qt, QThreadPool
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QMainWindow,
        QScrollArea,
        QVBoxLayout,
        QWidget
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for image_resizer.") from exc

from features.image.image_resizer_service import ImageResizerService
from features.image.image_resizer_preview_panel import ImageResizerPreviewPanel
from features.image.image_resizer_control_panel import ImageResizerControlPanel

from shared._engine.components.shell_frame import build_shell_window, finish_shell_window

APP_ID = "image_resizer"
APP_TITLE = qt_t("image_resizer.title", "Image Resizer")
APP_SUBTITLE = qt_t("image_resizer.subtitle", "Versatile Scaling Utility")


class ImageResizerWindow(QMainWindow):
    def __init__(self, service: ImageResizerService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Spacious UI: 380px Width, 810px Height (+160 for comfort)
        self.setFixedWidth(380)
        self.setMinimumHeight(810)
        
        # Enable Drag and Drop
        self.setAcceptDrops(True)
        self.thread_pool = QThreadPool.globalInstance()
        
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        if targets:
            self.service.add_inputs(targets)
        
        self.control_panel.refresh()
        self.preview_panel.refresh()

    def _build_ui(self) -> None:
        # 1. Base Shell
        self.central, self.shell, self.shell_layout = build_shell_window(
            self, self.app_root, APP_TITLE, "", use_size_grip=True
        )
        self.shell_layout.setContentsMargins(8, 8, 8, 8)

        # 2. Scrollable Content Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(12)
        
        # 3. Create independent panels
        self.preview_panel = ImageResizerPreviewPanel(self.service, self.thread_pool)
        self.control_panel = ImageResizerControlPanel(self.service)

        self.content_layout.addWidget(self.preview_panel)
        self.content_layout.addWidget(self.control_panel)
        self.content_layout.addStretch(1)
        
        self.scroll.setWidget(self.content_widget)
        self.shell_layout.addWidget(self.scroll, 1)
        
        finish_shell_window(self.shell_layout, self.shell, use_size_grip=True)

    def _bind_actions(self) -> None:
        # Connecting Panels
        self.control_panel.request_live_preview.connect(self.preview_panel.refresh_live)
        self.control_panel.request_save.connect(self._run_workflow)

    def _run_workflow(self) -> None:
        self.control_panel.update_run_status(True, "Processing...")
        ok, msg, _ = self.service.run_workflow()
        self.control_panel.update_run_status(False, "Done" if ok else f"Error: {msg}")

    def _restore_window_state(self) -> None:
        geo = self._settings.value("geometry")
        if geo: self.restoreGeometry(geo)

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if files:
            self.service.add_inputs(files)
            self.preview_panel.refresh()

def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = ImageResizerWindow(ImageResizerService(), Path(__file__).resolve().parents[3] / APP_ID, targets)
    window.show()
    return app.exec()
