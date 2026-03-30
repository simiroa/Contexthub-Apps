from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QDoubleValidator, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from contexthub.ui.qt.shell import (
    build_shell_stylesheet,
    get_shell_metrics,
    open_manual_dialog,
    qt_t,
    resolve_app_icon,
    resolve_manual_path,
)


DEFAULT_RADIUS = 2.0
SLIDER_SCALE = 10
SLIDER_MIN = 0
SLIDER_MAX = 100


@dataclass(frozen=True)
class BlurGray32DialogRequest:
    app_root: str | Path
    title: str
    subtitle: str
    item_count: int
    item_label: str
    output_rule: str
    confirm_label: str = "Run"
    default_radius: float = DEFAULT_RADIUS


class BlurGray32Dialog(QDialog):
    def __init__(self, request: BlurGray32DialogRequest) -> None:
        super().__init__()
        self.request = request
        self.selected_radius = request.default_radius
        self._drag_offset: QPoint | None = None
        self.setWindowTitle(request.title)
        self.setModal(True)
        self.setMinimumWidth(460)
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

        subtitle_label = QLabel(request.subtitle)
        subtitle_label.setObjectName("body")
        subtitle_label.setWordWrap(True)
        body_layout.addWidget(subtitle_label)

        chips = QHBoxLayout()
        chips.setSpacing(max(8, m.section_gap - 4))
        chips.addStretch(1)
        count_chip = QLabel(f"{request.item_count} {request.item_label}")
        count_chip.setObjectName("chip")
        count_chip.setAlignment(Qt.AlignCenter)
        count_chip.setFixedHeight(m.header_badge_height)
        count_chip.setMinimumWidth(120)
        chips.addWidget(count_chip)
        chips.addStretch(1)
        body_layout.addLayout(chips)

        output_label = QLabel(request.output_rule)
        output_label.setObjectName("eyebrow")
        output_label.setWordWrap(True)
        body_layout.addWidget(output_label)

        radius_block = QFrame()
        radius_block.setObjectName("subtlePanel")
        radius_layout = QVBoxLayout(radius_block)
        radius_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        radius_layout.setSpacing(6)

        radius_label = QLabel("Blur Radius")
        radius_label.setObjectName("eyebrow")
        radius_layout.addWidget(radius_label)

        radius_input = QLineEdit(f"{request.default_radius:g}")
        radius_input.setPlaceholderText("2.0")
        validator = QDoubleValidator(0.0, 9999.0, 3, radius_input)
        validator.setNotation(QDoubleValidator.StandardNotation)
        radius_input.setValidator(validator)
        radius_input.textChanged.connect(self._on_radius_changed)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(SLIDER_MIN, SLIDER_MAX)
        slider.setSingleStep(1)
        slider.setPageStep(5)
        slider.setValue(self._radius_to_slider(request.default_radius))
        slider.valueChanged.connect(self._on_slider_changed)
        self.radius_slider = slider
        radius_layout.addWidget(slider)
        radius_layout.addWidget(radius_input)
        self.radius_input = radius_input

        helper_label = QLabel("Use a number greater than or equal to 0. Example: 0, 1.5, 4")
        helper_label.setObjectName("body")
        helper_label.setWordWrap(True)
        radius_layout.addWidget(helper_label)

        body_layout.addWidget(radius_block)

        actions = QHBoxLayout()
        actions.setSpacing(max(8, m.section_gap - 4))

        cancel_btn = QPushButton(qt_t("common.cancel", "Cancel"))
        cancel_btn.setObjectName("pillBtn")
        cancel_btn.clicked.connect(self.reject)

        run_btn = QPushButton(request.confirm_label)
        run_btn.setObjectName("primary")
        run_btn.setMinimumHeight(m.primary_button_height)
        run_btn.clicked.connect(self._accept_if_valid)
        run_btn.setEnabled(request.item_count > 0)
        self.run_btn = run_btn

        actions.addWidget(cancel_btn)
        actions.addWidget(run_btn, 1)
        body_layout.addLayout(actions)

        shell_layout.addWidget(body)

        root = QVBoxLayout(self)
        root.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        root.addWidget(shell)

    def _on_radius_changed(self, text: str) -> None:
        value = self._parse_radius(text)
        if value is not None:
            slider_value = self._radius_to_slider(value)
            if self.radius_slider.value() != slider_value:
                self.radius_slider.blockSignals(True)
                self.radius_slider.setValue(slider_value)
                self.radius_slider.blockSignals(False)
        self.run_btn.setEnabled(self.request.item_count > 0 and value is not None)

    def _on_slider_changed(self, slider_value: int) -> None:
        value = self._slider_to_radius(slider_value)
        text = f"{value:.1f}".rstrip("0").rstrip(".")
        if self.radius_input.text() != text:
            self.radius_input.blockSignals(True)
            self.radius_input.setText(text)
            self.radius_input.blockSignals(False)
        self.run_btn.setEnabled(self.request.item_count > 0)

    def _parse_radius(self, text: str) -> float | None:
        stripped = text.strip()
        if not stripped:
            return None
        try:
            value = float(stripped)
        except ValueError:
            return None
        if value < 0:
            return None
        return value

    def _radius_to_slider(self, value: float) -> int:
        clamped = min(max(value, SLIDER_MIN / SLIDER_SCALE), SLIDER_MAX / SLIDER_SCALE)
        return int(round(clamped * SLIDER_SCALE))

    def _slider_to_radius(self, value: int) -> float:
        return value / SLIDER_SCALE

    def _accept_if_valid(self) -> None:
        value = self._parse_radius(self.radius_input.text())
        if value is None:
            QMessageBox.warning(self, self.request.title, "Blur radius must be a number greater than or equal to 0.")
            self.radius_input.setFocus()
            self.radius_input.selectAll()
            return
        self.selected_radius = value
        self.accept()

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


def run_blur_gray32_dialog(request: BlurGray32DialogRequest) -> dict[str, float] | None:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    app.setStyleSheet(build_shell_stylesheet())
    dialog = BlurGray32Dialog(request)
    if os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1":
        QTimer.singleShot(2500, dialog.accept)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        if owns_app:
            app.quit()
        return None
    result = {"radius": dialog.selected_radius}
    if owns_app:
        app.quit()
    return result
