from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

import os

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .manual import open_manual_dialog
from .support import resolve_app_icon, resolve_manual_path
from .theme_metrics import get_shell_metrics
from .theme_style_helpers import qt_t
from .theme_stylesheet import build_shell_stylesheet


@dataclass(frozen=True)
class ConfirmChoice:
    value: str
    label: str


@dataclass(frozen=True)
class ConfirmRequest:
    app_root: str | Path
    title: str
    subtitle: str
    item_count: int
    item_label: str
    output_rule: str = ""
    option_label: str = ""
    option_choices: tuple[ConfirmChoice, ...] = field(default_factory=tuple)
    option_value: str = ""
    confirm_label: str = "Run"


class ConfirmDialog(QDialog):
    def __init__(self, request: ConfirmRequest) -> None:
        super().__init__()
        self.request = request
        self.selected_value = request.option_value
        self._drag_offset: QPoint | None = None
        self.setWindowTitle(request.title)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setObjectName("confirmDialog")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        icon_path = resolve_app_icon(Path(request.app_root))
        icon = QIcon(str(icon_path)) if icon_path else QIcon()
        if not icon.isNull():
            self.setWindowIcon(icon)

        m = get_shell_metrics()
        shell = QFrame()
        shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(m.card_padding, m.header_padding_y_top, m.card_padding, m.card_padding)
        shell_layout.setSpacing(max(8, m.section_gap - 4))

        title_bar = QFrame()
        title_bar.setObjectName("panelTopBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        icon_label = QLabel()
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(m.header_icon_size, m.header_icon_size))
        title_layout.addWidget(icon_label)

        window_title = QLabel(request.title)
        window_title.setObjectName("windowTitle")
        title_layout.addWidget(window_title)
        title_layout.addStretch(1)

        self.manual_btn = QPushButton("?")
        self.manual_btn.setObjectName("titleBtn")
        self.manual_btn.setToolTip(qt_t("comfyui.qt_shell.manual_title", "App Manual"))
        self.manual_btn.clicked.connect(self._show_manual)
        self.manual_btn.setVisible(resolve_manual_path(Path(request.app_root)) is not None)
        title_layout.addWidget(self.manual_btn)

        self.min_btn = QPushButton("−")
        self.min_btn.setObjectName("titleBtn")
        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn = QPushButton("□")
        self.max_btn.setObjectName("titleBtn")
        self.max_btn.clicked.connect(self._toggle_maximize)
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("titleBtnClose")
        self.close_btn.clicked.connect(self.reject)
        title_layout.addWidget(self.min_btn)
        title_layout.addWidget(self.max_btn)
        title_layout.addWidget(self.close_btn)
        shell_layout.addWidget(title_bar)

        body = QFrame()
        body.setObjectName("card")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(m.card_padding, m.card_padding, m.card_padding, m.card_padding)
        body_layout.setSpacing(m.section_gap)

        chips = QHBoxLayout()
        chips.setSpacing(max(8, m.section_gap - 4))
        chips.addStretch(1)
        count_chip = QLabel(f"{request.item_count} {request.item_label}")
        count_chip.setObjectName("chip")
        count_chip.setAlignment(Qt.AlignCenter)
        count_chip.setFixedHeight(m.header_badge_height)
        count_chip.setMinimumWidth(104)
        chips.addWidget(count_chip)
        chips.addStretch(1)
        body_layout.addLayout(chips)

        self.option_combo: QComboBox | None = None
        if request.option_choices:
            option_block = QFrame()
            option_block.setObjectName("subtlePanel")
            option_layout = QVBoxLayout(option_block)
            option_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
            option_layout.setSpacing(6)

            label = QLabel(request.option_label)
            label.setObjectName("eyebrow")
            option_layout.addWidget(label)

            combo = QComboBox()
            combo.setObjectName("presetCombo")
            for choice in request.option_choices:
                combo.addItem(choice.label, choice.value)
            current_index = max(0, combo.findData(request.option_value))
            combo.setCurrentIndex(current_index)
            combo.currentIndexChanged.connect(self._sync_option)
            option_layout.addWidget(combo)
            self.option_combo = combo
            body_layout.addWidget(option_block)

        actions = QHBoxLayout()
        actions.setSpacing(max(8, m.section_gap - 4))

        cancel_btn = QPushButton(qt_t("common.cancel", "Cancel"))
        cancel_btn.setProperty("buttonRole", "pill")
        cancel_btn.clicked.connect(self.reject)

        run_btn = QPushButton(request.confirm_label)
        run_btn.setProperty("buttonRole", "primary")
        run_btn.clicked.connect(self.accept)
        run_btn.setEnabled(request.item_count > 0)

        actions.addWidget(cancel_btn)
        actions.addWidget(run_btn, 1)
        body_layout.addLayout(actions)

        shell_layout.addWidget(body)

        root = QVBoxLayout(self)
        root.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        root.addWidget(shell)

    def _sync_option(self) -> None:
        if self.option_combo is None:
            return
        self.selected_value = str(self.option_combo.currentData())

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setText("□")
        else:
            self.showMaximized()
            self.max_btn.setText("❐")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def _show_manual(self) -> None:
        open_manual_dialog(
            self,
            Path(self.request.app_root),
            qt_t("comfyui.qt_shell.manual_title", "App Manual"),
        )


def run_confirm_dialog(request: ConfirmRequest) -> dict[str, str] | None:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    app.setStyleSheet(build_shell_stylesheet())
    dialog = ConfirmDialog(request)
    if os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1":
        QTimer.singleShot(2500, dialog.accept)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        if owns_app:
            app.quit()
        return None
    result = {"option": dialog.selected_value}
    if owns_app:
        app.quit()
    return result
