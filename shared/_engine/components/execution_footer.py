from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.icon_utils import get_icon


class ExecutionFooter(QWidget):
    def __init__(
        self,
        title: str,
        *,
        include_format: bool = True,
        include_cancel: bool = True,
        cancel_text: str = "Cancel",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._include_format = include_format
        self._include_cancel = include_cancel
        self._build_ui(title, cancel_text)

    def _build_ui(self, title: str, cancel_text: str) -> None:
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

        self.status_label = QLabel("Ready")
        self.status_label.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)

        self.format_combo = QComboBox()
        self.format_combo.setObjectName("compactField")
        self.format_combo.addItems(["Original", "PNG", "JPG"])
        self.format_combo.setFixedHeight(32)
        self.format_combo.setVisible(self._include_format)

        self.cancel_btn = build_icon_button(cancel_text, icon_name="x", role="ghost", is_icon_only=not bool(cancel_text))
        self.cancel_btn.setVisible(False)

        self.run_btn = build_icon_button(title, icon_name="play", role="primary")
        self.run_btn.setFixedHeight(32)

        if self._include_format:
            self.layout.addWidget(self.format_combo, 1)
        if self._include_cancel:
            self.layout.addWidget(self.cancel_btn)
        self.layout.addWidget(self.run_btn, 1)

    def set_status(self, status: str, progress: Optional[str] = None) -> None:
        self.status_label.setText(status)
        if progress is not None:
            self.progress_label.setText(progress)

    def set_running(self, running: bool) -> None:
        self.run_btn.setEnabled(not running)
        if self._include_format:
            self.format_combo.setEnabled(not running)
        if self._include_cancel:
            self.cancel_btn.setVisible(running)
        self.run_btn.setIcon(get_icon("refresh-cw" if running else "play", color="white"))
        if not running:
            self.set_status("Ready", "")
