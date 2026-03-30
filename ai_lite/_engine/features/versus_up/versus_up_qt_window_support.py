from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from contexthub.ui.qt.shell import build_shell_stylesheet
from features.versus_up.versus_up_qt_panels import (
    CompareSummaryPanel,
    CriterionDetailPanel,
    HistoryPanel,
    ServerStatusPanel,
    VisionProcessingPanel,
)

try:
    from PySide6.QtCore import QSettings, qInstallMessageHandler
    from PySide6.QtGui import QFontInfo
    from PySide6.QtWidgets import QDialog, QFrame, QVBoxLayout, QWidget
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for versus_up.") from exc

_PREVIOUS_QT_MESSAGE_HANDLER = None


class PanelDialog(QDialog):
    def __init__(
        self,
        title: str,
        panel: QWidget,
        settings: QSettings,
        settings_key: str,
        *,
        parent: QWidget | None = None,
        size: tuple[int, int] = (520, 720),
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._settings_key = settings_key
        self._restored_geometry = False
        self.panel = panel
        self.setWindowTitle(title)
        self.setModal(False)
        self.resize(*size)
        self.setStyleSheet(build_shell_stylesheet())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        layout.addWidget(self.panel)
        outer.addWidget(card)
        self._restore_geometry()

    def _restore_geometry(self) -> None:
        geometry = self._settings.value(f"{self._settings_key}_geometry")
        if geometry:
            self.restoreGeometry(geometry)
            self._restored_geometry = True

    def closeEvent(self, event) -> None:
        self._settings.setValue(f"{self._settings_key}_geometry", self.saveGeometry())
        super().closeEvent(event)


@dataclass(slots=True)
class WindowDialogs:
    history_dialog: PanelDialog
    detail_dialog: PanelDialog
    radar_dialog: PanelDialog
    server_dialog: PanelDialog
    vision_dialog: PanelDialog
    history_panel: HistoryPanel
    detail_panel: CriterionDetailPanel
    compare_panel: CompareSummaryPanel
    server_panel: ServerStatusPanel
    vision_panel: VisionProcessingPanel

    def all(self) -> list[PanelDialog]:
        return [self.history_dialog, self.detail_dialog, self.radar_dialog, self.server_dialog, self.vision_dialog]


def install_qt_warning_probe() -> None:
    global _PREVIOUS_QT_MESSAGE_HANDLER
    if _PREVIOUS_QT_MESSAGE_HANDLER is not None:
        return

    def _handler(msg_type, context, message) -> None:
        text = str(message)
        if "QFont::setPointSize" in text:
            return
        if _PREVIOUS_QT_MESSAGE_HANDLER is not None:
            _PREVIOUS_QT_MESSAGE_HANDLER(msg_type, context, message)

    _PREVIOUS_QT_MESSAGE_HANDLER = qInstallMessageHandler(_handler)


def build_window_dialogs(parent: QWidget, settings: QSettings) -> WindowDialogs:
    history_dialog = PanelDialog("History", HistoryPanel(), settings, "history_dialog", parent=parent, size=(420, 720))
    detail_dialog = PanelDialog("Cell Detail", CriterionDetailPanel(), settings, "detail_dialog", parent=parent, size=(520, 760))
    radar_dialog = PanelDialog("Radar Compare", CompareSummaryPanel(), settings, "radar_dialog", parent=parent, size=(760, 620))
    server_dialog = PanelDialog("Server Status", ServerStatusPanel(), settings, "server_dialog", parent=parent, size=(540, 420))
    vision_dialog = PanelDialog("Vision Processing", VisionProcessingPanel(), settings, "vision_dialog", parent=parent, size=(560, 520))
    return WindowDialogs(
        history_dialog=history_dialog,
        detail_dialog=detail_dialog,
        radar_dialog=radar_dialog,
        server_dialog=server_dialog,
        vision_dialog=vision_dialog,
        history_panel=history_dialog.panel,
        detail_panel=detail_dialog.panel,
        compare_panel=radar_dialog.panel,
        server_panel=server_dialog.panel,
        vision_panel=vision_dialog.panel,
    )


def apply_explicit_base_font(widget: QWidget) -> None:
    font = widget.font()
    resolved_size = QFontInfo(font).pointSize()
    if resolved_size <= 0:
        resolved_size = 11
    font.setPointSize(resolved_size)
    widget.setFont(font)


def normalize_font_tree(root: QWidget) -> None:
    widgets = [root, *root.findChildren(QWidget)]
    for widget in widgets:
        font = widget.font()
        if font.pointSize() > 0:
            continue
        resolved_size = QFontInfo(font).pointSize()
        if resolved_size <= 0:
            resolved_size = 11
        font.setPointSize(resolved_size)
        widget.setFont(font)


def selection_summary(window) -> str:
    product = window._selected_product()
    criterion = window._selected_criterion()
    if window._detail_mode == "product" and product is not None:
        return f"Selection: product {product.name}"
    if criterion is not None:
        return f"Selection: criterion {criterion.label}"
    if product is not None:
        return f"Selection: product {product.name}"
    return "Selection: nothing selected"


def open_panel_dialog(parent: QWidget, dialog: PanelDialog, refresh_callback: Callable[[], None] | None = None) -> None:
    if refresh_callback is not None:
        refresh_callback()
    if not dialog.isVisible():
        geometry = parent.frameGeometry()
        center = geometry.center()
        if not dialog._restored_geometry:
            dialog_rect = dialog.frameGeometry()
            dialog_rect.moveCenter(center)
            dialog.move(dialog_rect.topLeft())
            dialog._restored_geometry = True
        dialog.show()
    dialog.raise_()
    dialog.activateWindow()
