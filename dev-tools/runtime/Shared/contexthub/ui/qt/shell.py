from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QIcon, QColor, QPainter, QPixmap
    from PySide6.QtWidgets import (
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QPushButton,
        QSizeGrip,
        QToolButton,
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
    shell_margin: int = 18
    section_gap: int = 14
    panel_padding: int = 14
    field_radius: int = 14


@dataclass
class ShellPalette:
    accent: str = "#3D8BFF"
    accent_soft: str = "rgba(61, 139, 255, 0.18)"
    accent_text: str = "#F5F8FF"
    text: str = "#F2F5F8"
    text_muted: str = "#A7B0BA"
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
        QLabel#sectionTitle {{
            font-size: 16px;
            font-weight: 700;
        }}
        QLabel#summaryText, QLabel#muted, QLabel#mutedSmall {{
            color: {p.text_muted};
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


class HeaderSurface(QFrame):
    def __init__(self, _window: QWidget, title: str, subtitle: str, app_root: Path, show_webui: bool = False):
        super().__init__()
        self._window = _window
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

        apply_app_icon(self, app_root)

    def set_asset_count(self, count: int) -> None:
        self.asset_count_badge.setText(f"{count} item{'s' if count != 1 else ''}")

    def set_loading(self, loading: bool) -> None:
        self.runtime_status_badge.setText("Working" if loading else "Ready")


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
