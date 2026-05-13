from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from contexthub.ui.qt.shell import qt_t

try:
    from PySide6.QtCore import Qt, QThreadPool
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QScrollArea,
        QVBoxLayout,
        QWidget,
        QListWidget
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for image_resizer.") from exc

from shared._engine.runtime.base_window import BaseAppWindow
from shared._engine.runtime.media_runtime import MediaRuntime
from shared._engine.runtime.file_input_mixin import MultiFileInputMixin
from shared._engine.components.batch_list_card import build_batch_list_card

from features.image.image_resizer_service import ImageResizerService
from features.image.image_resizer_preview_panel import ImageResizerPreviewPanel
from features.image.image_resizer_control_panel import ImageResizerControlPanel

from shared._engine.components.shell_frame import build_shell_window, finish_shell_window

APP_ID = "image_resizer"
APP_TITLE = qt_t("image_resizer.title", "Image Resizer")
APP_SUBTITLE = qt_t("image_resizer.subtitle", "Versatile Scaling Utility")


class ImageResizerWindow(BaseAppWindow, MultiFileInputMixin):
    APP_ID = "image_resizer"

    def __init__(self, service: ImageResizerService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__(app_root)
        self.service = service

        self.setWindowTitle(APP_TITLE)

        # Spacious UI: 380px Width, 810px Height (+160 for comfort)
        self.setFixedWidth(380)
        self.setMinimumHeight(810)

        self.runtime = MediaRuntime.instance()
        self.thread_pool = self.runtime.thread_pool
        
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
        
        # Batch List
        self.batch_ui = build_batch_list_card(qt_t("image_resizer.batch_items", "Items to Resize"))
        self.batch_ui["list_widget"].setMinimumHeight(150)
        self.batch_ui["list_widget"].setMaximumHeight(300)
        
        self.control_panel = ImageResizerControlPanel(self.service)

        self.content_layout.addWidget(self.preview_panel)
        self.content_layout.addWidget(self.batch_ui["card"])
        self.content_layout.addWidget(self.control_panel)
        self.content_layout.addStretch(1)
        
        self.scroll.setWidget(self.content_widget)
        self.shell_layout.addWidget(self.scroll, 1)
        
        finish_shell_window(self.shell_layout, self.shell, use_size_grip=True)
        
        # Setup Mixin
        self.setup_file_inputs(
            self.batch_ui["add_btn"], 
            self.batch_ui["clear_btn"], 
            self.batch_ui["list_widget"], 
            self.service.state
        )

    def _bind_actions(self) -> None:
        # Connecting Panels
        self.control_panel.request_live_preview.connect(self.preview_panel.refresh_live)
        self.control_panel.request_save.connect(self._run_workflow)
        self.batch_ui["list_widget"].currentRowChanged.connect(self._on_item_changed)
        self.batch_ui["remove_btn"].clicked.connect(self._on_remove_clicked)

    def _on_item_changed(self, row: int):
        if 0 <= row < len(self.state.files):
            self.service.set_preview_from_index(row)
            self.preview_panel.refresh()

    def _on_remove_clicked(self):
        row = self.batch_ui["list_widget"].currentRow()
        if 0 <= row < len(self.state.files):
            self.service.remove_input_at(row)
            self.batch_ui["list_widget"].takeItem(row)
            self.preview_panel.refresh()

    def on_files_added(self, paths):
        # Synchronize preview if it was empty
        if self.service.state.preview_path is None and self.state.files:
            self.service.set_preview_from_index(0)
            self.preview_panel.refresh()
            
    def get_file_filters(self):
        return "Images (*.png *.jpg *.jpeg *.exr *.hdr *.tiff *.tga)"

    def _run_workflow(self) -> None:
        self.control_panel.update_run_status(True, "Processing...")
        ok, msg, _ = self.service.run_workflow()
        self.control_panel.update_run_status(False, "Done" if ok else f"Error: {msg}")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if files:
            self._add_files([Path(f) for f in files])
            self.preview_panel.refresh()

def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    from shared._engine.runtime.single_instance import SingleInstance
    si = SingleInstance(APP_ID)
    if si.is_already_running():
        if targets: si.send_to_primary(targets)
        return 0

    app_root = Path(__file__).resolve().parents[3] / APP_ID
    try:
        from shared._engine.runtime.splash import show_splash, finish_splash
        splash = show_splash(app_root)
    except Exception:
        splash, finish_splash = None, lambda *_: None  # type: ignore[assignment]

    window = ImageResizerWindow(ImageResizerService(), app_root, targets)

    si.start_server()
    si.message_received.connect(window.handle_external_targets)
    window._si = si # Keep alive

    window.show()
    finish_splash(splash, window)
    return app.exec()
