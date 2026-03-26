from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from PySide6.QtCore import QPoint, Qt, Signal
    from PySide6.QtGui import QIcon, QColor, QPainter, QPixmap
    from PySide6.QtWidgets import (
        QDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QPushButton,
        QSizeGrip,
        QToolButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt shell runtime.") from exc


def qt_t(_key: str, default: str, **kwargs) -> str:
    try:
        return default.format(**kwargs)
    except Exception:
        return default


@dataclass
class ShellMetrics:
    window_radius: int = 18
    card_radius: int = 16
    panel_radius: int = 14
    shell_margin: int = 18
    card_padding: int = 16
    section_gap: int = 14
    panel_padding: int = 14
    field_radius: int = 14
    header_padding_x: int = 16
    header_padding_y_top: int = 12
    header_padding_y_bottom: int = 12
    header_row_gap: int = 10
    header_icon_size: int = 24
    header_badge_height: int = 42
    preview_min_height: int = 300
    primary_button_height: int = 46
    manual_dialog_width: int = 760
    manual_dialog_height: int = 780
    control_size: int = 42
    title_btn_size: int = 40
    title_btn_radius: int = 12
    input_padding_y: int = 10
    input_padding_x: int = 12
    button_padding_y: int = 8
    button_padding_x: int = 12
    group_title_offset_left: int = 14
    group_title_offset_top: int = 8
    asset_list_min_height: int = 260
    utility_button_size: int = 46
    summary_row_gap: int = 10
    collapsible_padding: int = 10
    collapsible_gap: int = 8
    collapsible_toggle_size: int = 28
    collapsible_body_gap: int = 10
    manual_body_padding: int = 22


@dataclass
class ShellPalette:
    app_bg: str = "#111723"
    surface_bg: str = "#171f2d"
    surface_subtle: str = "#141b28"
    field_bg: str = "#0f1114"
    border: str = "#2c3749"
    accent: str = "#3D8BFF"
    accent_soft: str = "rgba(61, 139, 255, 0.18)"
    accent_text: str = "#F5F8FF"
    text: str = "#F2F5F8"
    text_muted: str = "#A7B0BA"
    muted: str = "#A7B0BA"
    accent_hover: str = "#4c96ff"
    success: str = "#5e9777"
    warning: str = "#b49563"
    error: str = "#b87379"
    control_bg: str = "#1a2230"
    control_border: str = "rgba(255,255,255,0.10)"


def get_shell_metrics() -> ShellMetrics:
    return ShellMetrics()


def get_shell_palette() -> ShellPalette:
    return ShellPalette()


def build_shell_stylesheet() -> str:
    p = get_shell_palette()
    m = get_shell_metrics()
    return f"""
        QWidget {{
            color: {p.text};
            font-size: 13px;
        }}
        QFrame#windowShell {{
            background: #171A1F;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
        }}
        QFrame#card, QFrame#panelCard, QFrame#subtlePanel {{
            background: #1E232A;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
        }}
        QFrame#statusCard {{
            background: #1E232A;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
        }}
        QFrame#statusPanel {{
            background: #141b28;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 14px;
        }}
        QLabel#sectionTitle {{
            font-size: 16px;
            font-weight: 700;
        }}
        QLabel#summaryText, QLabel#muted, QLabel#mutedSmall {{
            color: {p.text_muted};
        }}
        QLabel#statusKey {{
            color: {p.text_muted};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.08em;
        }}
        QLabel#statusValue {{
            color: {p.text};
            font-size: 18px;
            font-weight: 700;
        }}
        QLabel#statusValueRunning {{
            color: {p.success};
            font-size: 18px;
            font-weight: 700;
        }}
        QLabel#statusValueStopped {{
            color: {p.error};
            font-size: 18px;
            font-weight: 700;
        }}
        QLabel#eyebrow {{
            color: {p.text_muted};
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        QPushButton, QToolButton, QComboBox, QLineEdit, QListWidget {{
            border-radius: {m.field_radius}px;
        }}
        QToolButton#windowChrome {{
            min-width: 30px;
            min-height: 30px;
            max-width: 30px;
            max-height: 30px;
            border-radius: 15px;
            background: rgba(255,255,255,0.05);
            border: 1px solid {p.control_border};
            font-size: 14px;
            font-weight: 700;
        }}
        QToolButton#windowChrome:hover {{
            background: rgba(255,255,255,0.12);
        }}
        QPushButton {{
            background: rgba(255,255,255,0.06);
            border: 1px solid {p.control_border};
            padding: 8px 12px;
        }}
        QPushButton:hover {{
            background: rgba(255,255,255,0.10);
        }}
        QPushButton#primary {{
            background: {p.accent};
            color: {p.accent_text};
        }}
        QLineEdit, QComboBox, QListWidget {{
            background: rgba(8, 10, 14, 0.45);
            border: 1px solid {p.control_border};
            padding: 8px 10px;
        }}
    """


def runtime_settings_signature() -> str:
    return "default"


def refresh_runtime_preferences() -> None:
    return None


def apply_app_icon(widget: QWidget, app_root: Path) -> None:
    for name in ("icon.png", "icon.ico"):
        icon_path = app_root / name
        if icon_path.exists():
            widget.setWindowIcon(QIcon(str(icon_path)))
            return


def build_size_grip() -> QSizeGrip:
    grip = QSizeGrip(None)
    grip.setStyleSheet("background: transparent;")
    return grip


class CollapsibleSection(QFrame):
    def __init__(self, title: str, expanded: bool = True):
        super().__init__()
        self.setObjectName("card")
        self._expanded = expanded
        self._body_visible = expanded

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        header.addWidget(self.title_label, 1)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setObjectName("windowChrome")
        self.toggle_btn.clicked.connect(self._toggle_expanded)
        header.addWidget(self.toggle_btn, 0, Qt.AlignRight)
        layout.addLayout(header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(8)
        layout.addWidget(self.body)

        self.set_expanded(expanded)

    def _toggle_expanded(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._body_visible = expanded
        self.body.setVisible(expanded)
        self.toggle_btn.setText("−" if expanded else "+")

    def add_widget(self, widget: QWidget) -> None:
        self.body_layout.addWidget(widget)

    def finish(self) -> None:
        self.set_expanded(self._expanded)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)


def resolve_app_icon(app_root: Path) -> Path | None:
    for name in ("icon.png", "icon.ico"):
        icon_path = app_root / name
        if icon_path.exists():
            return icon_path
    return None


def resolve_manual_path(app_root: Path) -> Path | None:
    manual_path = app_root / "manual.md"
    if manual_path.exists():
        return manual_path
    return None


class ManualDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, manual_path: Path):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        layout = QVBoxLayout(self)
        viewer = QTextEdit()
        viewer.setReadOnly(True)
        try:
            viewer.setPlainText(manual_path.read_text(encoding="utf-8"))
        except Exception:
            viewer.setPlainText(str(manual_path))
        layout.addWidget(viewer)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class HeaderSurface(QFrame):
    def __init__(self, _window: QWidget, title: str, subtitle: str, app_root: Path, show_webui: bool = False):
        super().__init__()
        self._window = _window
        self._drag_offset: QPoint | None = None
        self._manual_drag_active = False
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        title_col = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("summaryText")
        self.subtitle_label.setWordWrap(True)
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        top.addLayout(title_col, 1)

        right_col = QVBoxLayout()
        chrome_row = QHBoxLayout()
        chrome_row.setSpacing(6)
        chrome_row.addStretch(1)
        self.minimize_btn = QToolButton()
        self.minimize_btn.setObjectName("windowChrome")
        self.minimize_btn.setText("–")
        self.minimize_btn.clicked.connect(self._window.showMinimized)
        chrome_row.addWidget(self.minimize_btn)
        self.min_btn = self.minimize_btn
        self.maximize_btn = QToolButton()
        self.maximize_btn.setObjectName("windowChrome")
        self.maximize_btn.setText("□")
        self.maximize_btn.clicked.connect(self._toggle_maximize)
        chrome_row.addWidget(self.maximize_btn)
        self.max_btn = self.maximize_btn
        self.close_btn = QToolButton()
        self.close_btn.setObjectName("windowChrome")
        self.close_btn.setText("×")
        self.close_btn.clicked.connect(self._window.close)
        chrome_row.addWidget(self.close_btn)
        right_col.addLayout(chrome_row)

        badge_col = QVBoxLayout()
        badge_col.setSpacing(6)
        self.asset_count_badge = QLabel("0")
        self.asset_count_badge.setObjectName("eyebrow")
        self.runtime_status_badge = QLabel("Ready")
        self.runtime_status_badge.setObjectName("eyebrow")
        badge_col.addWidget(self.asset_count_badge, 0, Qt.AlignRight)
        badge_col.addWidget(self.runtime_status_badge, 0, Qt.AlignRight)
        right_col.addLayout(badge_col)
        top.addLayout(right_col)
        layout.addLayout(top)

        self.open_webui_btn = QPushButton("Open")
        self.open_webui_btn.setVisible(show_webui)
        layout.addWidget(self.open_webui_btn, 0, Qt.AlignRight)
        self.manual_btn = self.open_webui_btn

        self._install_drag_targets()
        apply_app_icon(self, app_root)

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


class DropListWidget(QListWidget):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)
