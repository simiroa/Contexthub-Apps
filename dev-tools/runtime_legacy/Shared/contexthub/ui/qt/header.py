from __future__ import annotations

from pathlib import Path

from .manual import open_manual_dialog
from .support import apply_app_icon, resolve_manual_path
from .theme import qt_t
from .widgets import ElidedLabel

try:
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout, QWidget
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt shell runtime.") from exc


class HeaderSurface(QFrame):
    def __init__(self, _window: QWidget, title: str, subtitle: str, app_root: Path, show_webui: bool = False):
        super().__init__()
        self._window = _window
        self.app_root = Path(app_root)
        self._drag_offset: QPoint | None = None
        self._manual_drag_active = False
        self.setObjectName("card")
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(14, 12, 14, 12)
        self._root_layout.setSpacing(0)

        self.top_row = QHBoxLayout()
        self.top_row.setContentsMargins(0, 0, 0, 0)
        self.top_row.setSpacing(10)
        self.title_col = QVBoxLayout()
        self.title_col.setContentsMargins(0, 0, 0, 0)
        self.title_col.setSpacing(0)
        self.title_label = ElidedLabel(title)
        self.title_label.setObjectName("sectionTitle")
        self.subtitle_label = ElidedLabel(subtitle)
        self.subtitle_label.setObjectName("summaryText")
        self.title_col.addWidget(self.title_label)
        self.top_row.addLayout(self.title_col, 1)

        self.chrome_row = QHBoxLayout()
        self.chrome_row.setContentsMargins(0, 0, 0, 0)
        self.chrome_row.setSpacing(6)
        self.header_action_btn = QToolButton()
        self.header_action_btn.setObjectName("windowChrome")
        self.chrome_row.addWidget(self.header_action_btn)
        self.minimize_btn = QToolButton()
        self.minimize_btn.setObjectName("windowChrome")
        self.minimize_btn.setText("–")
        self.minimize_btn.clicked.connect(self._window.showMinimized)
        self.chrome_row.addWidget(self.minimize_btn)
        self.min_btn = self.minimize_btn
        self.maximize_btn = QToolButton()
        self.maximize_btn.setObjectName("windowChrome")
        self.maximize_btn.setText("□")
        self.maximize_btn.clicked.connect(self._toggle_maximize)
        self.chrome_row.addWidget(self.maximize_btn)
        self.max_btn = self.maximize_btn
        self.close_btn = QToolButton()
        self.close_btn.setObjectName("windowChrome")
        self.close_btn.setText("×")
        self.close_btn.clicked.connect(self._window.close)
        self.chrome_row.addWidget(self.close_btn)
        self.badge_box = QWidget()
        self.badge_col = QVBoxLayout(self.badge_box)
        self.badge_col.setContentsMargins(0, 0, 0, 0)
        self.badge_col.setSpacing(6)
        self.asset_count_badge = QLabel("0")
        self.asset_count_badge.setObjectName("eyebrow")
        self.runtime_status_badge = QLabel("Ready")
        self.runtime_status_badge.setObjectName("eyebrow")
        self.badge_col.addWidget(self.asset_count_badge, 0, Qt.AlignRight)
        self.badge_col.addWidget(self.runtime_status_badge, 0, Qt.AlignRight)
        self.top_row.addLayout(self.chrome_row, 0)
        self._root_layout.addLayout(self.top_row)

        self.open_webui_btn = QPushButton("Open")
        self.open_webui_btn.setVisible(False)
        self.manual_btn = self.header_action_btn
        self._manual_title = qt_t("comfyui.qt_shell.manual_title", "App Manual")
        self.header_action_btn.setText("?")
        self.header_action_btn.setToolTip(self._manual_title)
        self.header_action_btn.clicked.connect(self._open_manual)
        self._manual_visible = resolve_manual_path(self.app_root) is not None

        self._install_drag_targets()
        apply_app_icon(self, self.app_root)
        self.set_header_visibility(
            show_subtitle=False,
            show_asset_count=False,
            show_runtime_status=False,
        )
        self._update_manual_visibility()

    def _toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
            self.maximize_btn.setText("□")
        else:
            self._window.showMaximized()
            self.maximize_btn.setText("❐")

    def set_asset_count(self, count: int) -> None:
        self.asset_count_badge.setText(f"{count} item{'s' if count != 1 else ''}")

    def set_loading(self, loading: bool) -> None:
        self.runtime_status_badge.setText("Working" if loading else "Ready")

    def set_subtitle_visible(self, visible: bool) -> None:
        self.subtitle_label.setVisible(visible)

    def set_asset_count_visible(self, visible: bool) -> None:
        self.asset_count_badge.setVisible(visible)
        self._update_badge_layout()

    def set_runtime_status_visible(self, visible: bool) -> None:
        self.runtime_status_badge.setVisible(visible)
        self._update_badge_layout()

    def set_header_visibility(
        self,
        *,
        show_subtitle: bool | None = None,
        show_asset_count: bool | None = None,
        show_runtime_status: bool | None = None,
    ) -> None:
        if show_subtitle is not None:
            self.set_subtitle_visible(show_subtitle)
        if show_asset_count is not None:
            self.set_asset_count_visible(show_asset_count)
        if show_runtime_status is not None:
            self.set_runtime_status_visible(show_runtime_status)

    def set_manual_visible(self, visible: bool) -> None:
        self._manual_visible = visible
        self._update_manual_visibility()

    def _update_badge_layout(self) -> None:
        self.badge_box.setVisible(self.asset_count_badge.isVisible() or self.runtime_status_badge.isVisible())

    def _update_manual_visibility(self) -> None:
        self.header_action_btn.setVisible(self._manual_visible and resolve_manual_path(self.app_root) is not None)

    def _open_manual(self) -> None:
        open_manual_dialog(self._window, self.app_root, self._manual_title)

    def _install_drag_targets(self) -> None:
        for widget in (
            self.title_label,
            self.subtitle_label,
            self.asset_count_badge,
            self.runtime_status_badge,
        ):
            widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and not self._window.isMaximized():
            handle = self._window.windowHandle()
            if handle is not None and hasattr(handle, "startSystemMove") and handle.startSystemMove():
                event.accept()
                return
            global_pos = event.globalPosition().toPoint()
            self._drag_offset = global_pos - self._window.frameGeometry().topLeft()
            self._manual_drag_active = True
            self.grabMouse()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._manual_drag_active and self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._manual_drag_active and event.button() == Qt.LeftButton:
            self._manual_drag_active = False
            self._drag_offset = None
            self.releaseMouse()
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)
