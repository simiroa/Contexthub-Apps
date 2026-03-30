from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

try:
    from PySide6.QtCore import QPoint, Qt, Signal
    from PySide6.QtGui import QFontMetrics, QIcon, QColor, QPainter, QPixmap
    from PySide6.QtWidgets import (
        QDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QPushButton,
        QSizeGrip,
        QTextBrowser,
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
    manual_header_padding: int = 18
    manual_section_spacing: int = 16


@dataclass
class ShellPalette:
    app_bg: str = "#12161b"
    surface_bg: str = "#181d24"
    surface_subtle: str = "#161b21"
    content_bg: str = "#181d24"
    field_bg: str = "#14191f"
    border: str = "#2a3440"
    accent: str = "#4B8DFF"
    accent_soft: str = "rgba(75, 141, 255, 0.18)"
    accent_text: str = "#F5F8FF"
    text: str = "#F2F5F8"
    text_muted: str = "#A7B0BA"
    muted: str = "#A7B0BA"
    accent_hover: str = "#66a0ff"
    success: str = "#5e9777"
    warning: str = "#b49563"
    error: str = "#b87379"
    control_bg: str = "#1d242d"
    control_border: str = "rgba(255,255,255,0.11)"
    window_shell_bg: str = "#141920"
    card_bg: str = "#1a2028"
    status_card_bg: str = "#1c232c"
    status_panel_bg: str = "#161b21"
    button_bg: str = "rgba(255,255,255,0.05)"
    button_hover: str = "rgba(255,255,255,0.09)"
    button_pressed: str = "rgba(255,255,255,0.12)"
    chrome_bg: str = "rgba(255,255,255,0.05)"
    chrome_hover: str = "rgba(255,255,255,0.12)"
    chip_bg: str = "rgba(75, 141, 255, 0.14)"
    chip_border: str = "rgba(75, 141, 255, 0.30)"
    chip_text: str = "#DCE8FF"


@dataclass(frozen=True)
class ToneSpec:
    base: str
    fill: str
    border: str
    text: str


def get_shell_metrics() -> ShellMetrics:
    return ShellMetrics()


def get_shell_palette() -> ShellPalette:
    return ShellPalette()


def _rgba(hex_color: str, alpha: int) -> str:
    color = QColor(hex_color)
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"


def _lift_color(hex_color: str, factor: int) -> str:
    return QColor(hex_color).lighter(factor).name()


def get_shell_accent_cycle(palette: ShellPalette | None = None) -> list[str]:
    p = palette or get_shell_palette()
    return [
        p.text_muted,
        p.success,
        p.warning,
        p.accent,
        p.error,
        _lift_color(p.accent, 130),
        _lift_color(p.warning, 125),
        _lift_color(p.success, 120),
    ]


def get_tone_spec(tone: str = "default", palette: ShellPalette | None = None) -> ToneSpec:
    p = palette or get_shell_palette()
    base_map = {
        "default": p.accent,
        "accent": p.accent,
        "success": p.success,
        "warning": p.warning,
        "error": p.error,
        "muted": p.text_muted,
    }
    text_map = {
        "default": p.text,
        "accent": p.chip_text,
        "success": p.text,
        "warning": p.text,
        "error": p.text,
        "muted": p.text_muted,
    }
    base = base_map.get(tone, p.accent)
    return ToneSpec(
        base=base,
        fill=_rgba(base, 34 if tone in {"default", "muted"} else 42),
        border=_rgba(base, 82 if tone in {"default", "muted"} else 118),
        text=text_map.get(tone, p.text),
    )


def _refresh_widget_style(widget: QWidget) -> None:
    style = widget.style()
    if style is None:
        return
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def set_surface_role(widget: QWidget, role: str = "card", tone: str = "default") -> None:
    widget.setProperty("surfaceRole", role)
    widget.setProperty("tone", tone)
    _refresh_widget_style(widget)


def set_button_role(widget: QWidget, role: str = "secondary", tone: str = "default") -> None:
    widget.setProperty("buttonRole", role)
    widget.setProperty("tone", tone)
    _refresh_widget_style(widget)


def set_badge_role(widget: QWidget, role: str = "chip", tone: str = "accent") -> None:
    widget.setProperty("badgeRole", role)
    widget.setProperty("tone", tone)
    _refresh_widget_style(widget)


def set_transparent_surface(widget: QWidget) -> None:
    widget.setAttribute(Qt.WA_StyledBackground, True)
    widget.setProperty("transparentSurface", True)
    _refresh_widget_style(widget)


def build_shell_stylesheet() -> str:
    p = get_shell_palette()
    m = get_shell_metrics()
    combo_arrow = (Path(__file__).resolve().parent / "assets" / "combo_chevron_down.svg").as_posix()
    accent = get_tone_spec("accent", p)
    success = get_tone_spec("success", p)
    warning = get_tone_spec("warning", p)
    error = get_tone_spec("error", p)
    muted = get_tone_spec("muted", p)
    return f"""
        QWidget {{
            color: {p.text};
            font-size: 13px;
        }}
        QFrame#windowShell {{
            background: {p.window_shell_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.window_radius}px;
        }}
        QFrame#card, QFrame#panelCard {{
            background: {p.card_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.card_radius}px;
        }}
        QFrame#subtlePanel {{
            background: {p.surface_subtle};
            border: 1px solid {p.control_border};
            border-radius: {m.panel_radius}px;
        }}
        QFrame#statusCard {{
            background: {p.status_card_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.card_radius}px;
        }}
        QFrame#statusPanel {{
            background: {p.status_panel_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.panel_radius}px;
        }}
        QFrame[surfaceRole="card"], QWidget[surfaceRole="card"] {{
            background: {p.card_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.card_radius}px;
        }}
        QFrame[surfaceRole="panel"], QWidget[surfaceRole="panel"] {{
            background: {p.surface_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.panel_radius}px;
        }}
        QFrame[surfaceRole="subtle"], QWidget[surfaceRole="subtle"] {{
            background: {p.surface_subtle};
            border: 1px solid {p.control_border};
            border-radius: {m.panel_radius}px;
        }}
        QFrame[surfaceRole="content"], QWidget[surfaceRole="content"] {{
            background: {p.content_bg};
            border: none;
            border-radius: 0;
        }}
        QFrame[surfaceRole="status"], QWidget[surfaceRole="status"] {{
            background: {p.status_panel_bg};
            border: 1px solid {p.control_border};
            border-radius: {m.panel_radius}px;
        }}
        QFrame[surfaceRole="card"][tone="accent"], QWidget[surfaceRole="card"][tone="accent"],
        QFrame[surfaceRole="panel"][tone="accent"], QWidget[surfaceRole="panel"][tone="accent"],
        QFrame[surfaceRole="subtle"][tone="accent"], QWidget[surfaceRole="subtle"][tone="accent"],
        QFrame[surfaceRole="status"][tone="accent"], QWidget[surfaceRole="status"][tone="accent"] {{
            background: {accent.fill};
            border: 1px solid {accent.border};
        }}
        QFrame[surfaceRole="card"][tone="success"], QWidget[surfaceRole="card"][tone="success"],
        QFrame[surfaceRole="panel"][tone="success"], QWidget[surfaceRole="panel"][tone="success"],
        QFrame[surfaceRole="subtle"][tone="success"], QWidget[surfaceRole="subtle"][tone="success"],
        QFrame[surfaceRole="status"][tone="success"], QWidget[surfaceRole="status"][tone="success"] {{
            background: {success.fill};
            border: 1px solid {success.border};
        }}
        QFrame[surfaceRole="card"][tone="warning"], QWidget[surfaceRole="card"][tone="warning"],
        QFrame[surfaceRole="panel"][tone="warning"], QWidget[surfaceRole="panel"][tone="warning"],
        QFrame[surfaceRole="subtle"][tone="warning"], QWidget[surfaceRole="subtle"][tone="warning"],
        QFrame[surfaceRole="status"][tone="warning"], QWidget[surfaceRole="status"][tone="warning"] {{
            background: {warning.fill};
            border: 1px solid {warning.border};
        }}
        QFrame[surfaceRole="card"][tone="error"], QWidget[surfaceRole="card"][tone="error"],
        QFrame[surfaceRole="panel"][tone="error"], QWidget[surfaceRole="panel"][tone="error"],
        QFrame[surfaceRole="subtle"][tone="error"], QWidget[surfaceRole="subtle"][tone="error"],
        QFrame[surfaceRole="status"][tone="error"], QWidget[surfaceRole="status"][tone="error"] {{
            background: {error.fill};
            border: 1px solid {error.border};
        }}
        QWidget[transparentSurface="true"], QFrame[transparentSurface="true"] {{
            background: transparent;
            border: none;
        }}
        QLabel#sectionTitle {{
            font-size: 16px;
            font-weight: 700;
        }}
        QLabel#title {{
            color: {p.text};
            font-size: 14px;
            font-weight: 700;
        }}
        QLabel#summaryText, QLabel#muted, QLabel#mutedSmall {{
            color: {p.text_muted};
        }}
        QLabel#mutedSmall {{
            font-size: 11px;
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
        QLabel#chip {{
            color: {p.chip_text};
            background: {p.chip_bg};
            border: 1px solid {p.chip_border};
            border-radius: 12px;
            padding: 6px 10px;
            font-size: 11px;
            font-weight: 700;
        }}
        QLabel[badgeRole="chip"],
        QLabel[badgeRole="status"] {{
            border-radius: 12px;
            padding: 6px 10px;
            font-size: 11px;
            font-weight: 700;
            color: {accent.text};
            background: {accent.fill};
            border: 1px solid {accent.border};
        }}
        QLabel[badgeRole="chip"][tone="success"],
        QLabel[badgeRole="status"][tone="success"] {{
            color: {success.text};
            background: {success.fill};
            border: 1px solid {success.border};
        }}
        QLabel[badgeRole="chip"][tone="warning"],
        QLabel[badgeRole="status"][tone="warning"] {{
            color: {warning.text};
            background: {warning.fill};
            border: 1px solid {warning.border};
        }}
        QLabel[badgeRole="chip"][tone="error"],
        QLabel[badgeRole="status"][tone="error"] {{
            color: {error.text};
            background: {error.fill};
            border: 1px solid {error.border};
        }}
        QLabel[badgeRole="chip"][tone="muted"],
        QLabel[badgeRole="status"][tone="muted"] {{
            color: {muted.text};
            background: {muted.fill};
            border: 1px solid {muted.border};
        }}
        QPushButton, QToolButton, QComboBox, QLineEdit, QListWidget, QTextEdit {{
            border-radius: {m.field_radius}px;
        }}
        QToolButton#windowChrome {{
            min-width: 30px;
            min-height: 30px;
            max-width: 30px;
            max-height: 30px;
            border-radius: 15px;
            background: {p.chrome_bg};
            border: 1px solid {p.control_border};
            font-size: 14px;
            font-weight: 700;
        }}
        QToolButton#windowChrome:hover {{
            background: {p.chrome_hover};
        }}
        QPushButton {{
            background: {p.button_bg};
            border: 1px solid {p.control_border};
            padding: {m.button_padding_y}px {m.button_padding_x}px;
        }}
        QPushButton:hover {{
            background: {p.button_hover};
        }}
        QPushButton:pressed {{
            background: {p.button_pressed};
        }}
        QPushButton#primary {{
            background: {p.accent};
            color: {p.accent_text};
        }}
        QPushButton[buttonRole="primary"], QToolButton[buttonRole="primary"] {{
            background: {p.accent};
            color: {p.accent_text};
        }}
        QPushButton[buttonRole="secondary"], QToolButton[buttonRole="secondary"] {{
            background: {p.button_bg};
            color: {p.text};
            border: 1px solid {p.control_border};
        }}
        QPushButton[buttonRole="ghost"], QToolButton[buttonRole="ghost"] {{
            background: transparent;
            color: {p.text_muted};
            border: 1px solid transparent;
        }}
        QPushButton[buttonRole="pill"], QToolButton[buttonRole="pill"] {{
            background: {p.control_bg};
            color: {p.text};
            border-radius: 14px;
            padding: 8px 14px;
        }}
        QPushButton[buttonRole="icon"], QToolButton[buttonRole="icon"] {{
            background: {p.control_bg};
            color: {p.text};
            border-radius: 12px;
            padding: 8px 10px;
        }}
        QPushButton[buttonRole="primary"][tone="success"], QToolButton[buttonRole="primary"][tone="success"] {{
            background: {p.success};
            color: {p.text};
        }}
        QPushButton[buttonRole="primary"][tone="warning"], QToolButton[buttonRole="primary"][tone="warning"] {{
            background: {p.warning};
            color: {p.text};
        }}
        QPushButton[buttonRole="primary"][tone="error"], QToolButton[buttonRole="primary"][tone="error"] {{
            background: {p.error};
            color: {p.text};
        }}
        QPushButton#pillBtn {{
            background: {p.control_bg};
            color: {p.text};
            border-radius: 14px;
            padding: 8px 14px;
        }}
        QPushButton#pillBtn:hover,
        QPushButton[buttonRole="pill"]:hover,
        QToolButton[buttonRole="pill"]:hover,
        QPushButton[buttonRole="secondary"]:hover,
        QToolButton[buttonRole="secondary"]:hover,
        QPushButton[buttonRole="icon"]:hover,
        QToolButton[buttonRole="icon"]:hover {{
            background: {p.button_hover};
        }}
        QPushButton#iconBtn {{
            background: {p.control_bg};
            color: {p.text};
            border-radius: 12px;
            padding: 8px 10px;
        }}
        QPushButton[buttonRole="ghost"]:hover,
        QToolButton[buttonRole="ghost"]:hover {{
            color: {p.text};
            background: {p.chrome_bg};
        }}
        QLineEdit, QComboBox, QListWidget, QTextEdit {{
            background: {p.field_bg};
            border: 1px solid {p.control_border};
            padding: {m.input_padding_y}px {m.input_padding_x}px;
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QSplitter {{
            background: transparent;
        }}
        QSplitter::handle {{
            background: {p.content_bg};
            border: none;
        }}
        QSplitter::handle:horizontal {{
            width: 8px;
            margin: 0;
        }}
        QSplitter::handle:vertical {{
            height: 8px;
            margin: 0;
        }}
        QComboBox {{
            padding-right: 24px;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 16px;
            margin: 0 8px 0 0;
            background: transparent;
            border: none;
            border-radius: 0;
            padding: 0;
        }}
        QComboBox::down-arrow {{
            image: url("{combo_arrow}");
            width: 10px;
            height: 6px;
            margin: 0;
            border: none;
            background: transparent;
        }}
        QComboBox:on {{
            border-color: {_rgba(p.accent, 140)};
        }}
        QComboBox QAbstractItemView {{
            background: {p.field_bg};
            color: {p.text};
            border: 1px solid {p.control_border};
            border-radius: {m.field_radius}px;
            padding: 4px;
            selection-background-color: {p.accent};
            selection-color: {p.accent_text};
            outline: 0;
        }}
        QProgressBar {{
            background: {p.surface_subtle};
            border: 1px solid {p.control_border};
            border-radius: 10px;
            min-height: 12px;
            text-align: center;
            color: {p.text_muted};
        }}
        QProgressBar::chunk {{
            background: {p.accent};
            border-radius: 9px;
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
    grip = VisibleSizeGrip(None)
    return grip


def attach_size_grip(shell_layout: QVBoxLayout, shell_parent: QWidget) -> QSizeGrip:
    grip_row = QHBoxLayout()
    grip_row.setContentsMargins(0, 0, 2, 0)
    grip_row.addStretch(1)
    grip = build_size_grip()
    grip.setParent(shell_parent)
    grip_row.addWidget(grip, 0, Qt.AlignRight | Qt.AlignBottom)
    shell_layout.addLayout(grip_row)
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


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setWordWrap(False)
        self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802
        self._full_text = text or ""
        super().setText(self._full_text)
        self.setToolTip(self._full_text if self._full_text else "")
        self._apply_elision()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_elision()

    def full_text(self) -> str:
        return self._full_text

    def _apply_elision(self) -> None:
        if not self._full_text:
            super().setText("")
            return
        width = max(0, self.contentsRect().width())
        if width <= 0:
            super().setText(self._full_text)
            return
        metrics = QFontMetrics(self.font())
        super().setText(metrics.elidedText(self._full_text, Qt.ElideRight, width))


class VisibleSizeGrip(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.SizeFDiagCursor)
        self._grip = QSizeGrip(self)
        self._grip.setStyleSheet("background: transparent;")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._grip.setGeometry(self.rect())

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        color = QColor(get_shell_palette().text_muted)
        color.setAlpha(140)
        painter.setPen(color)
        edge = self.width() - 3
        painter.drawLine(edge - 8, edge, edge, edge - 8)
        painter.drawLine(edge - 12, edge, edge, edge - 12)
        painter.drawLine(edge - 16, edge, edge, edge - 16)
        painter.end()


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


def _manual_fallback_html(text: str) -> str:
    lines = text.splitlines()
    parts: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            parts.append(f"<p>{escape(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    def flush_code() -> None:
        nonlocal in_code, code_lines
        if in_code:
            parts.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
            in_code = False
            code_lines = []

    for line in lines:
        stripped = line.rstrip()
        bare = stripped.strip()
        if bare.startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code:
                flush_code()
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(stripped)
            continue
        if not bare:
            flush_paragraph()
            flush_list()
            continue
        if bare.startswith("#"):
            flush_paragraph()
            flush_list()
            level = min(6, len(bare) - len(bare.lstrip("#")))
            parts.append(f"<h{level}>{escape(bare[level:].strip())}</h{level}>")
            continue
        if bare.startswith(("- ", "* ")):
            flush_paragraph()
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{escape(bare[2:].strip())}</li>")
            continue
        paragraph.append(bare)

    flush_paragraph()
    flush_list()
    flush_code()
    return "".join(parts) or f"<p>{escape(text)}</p>"


def _load_manual_html(manual_path: Path) -> str:
    try:
        text = manual_path.read_text(encoding="utf-8")
    except Exception:
        return f"<p>{escape(str(manual_path))}</p>"
    return text


def open_manual_dialog(parent: QWidget | None, app_root: Path, title: str = "App Manual") -> ManualDialog | None:
    manual_path = resolve_manual_path(Path(app_root))
    if not manual_path:
        return None
    host = parent if parent is not None else QWidget()
    dialog = getattr(host, "_contexthub_manual_dialog", None)
    cached_path = getattr(host, "_contexthub_manual_path", None)
    if not isinstance(dialog, ManualDialog) or cached_path != manual_path:
        dialog = ManualDialog(parent, title, manual_path)
        dialog.setStyleSheet(build_shell_stylesheet())
        setattr(host, "_contexthub_manual_dialog", dialog)
        setattr(host, "_contexthub_manual_path", manual_path)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog


class ManualDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, manual_path: Path):
        super().__init__(parent)
        self.manual_path = Path(manual_path)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setObjectName("manualDialog")
        self.resize(get_shell_metrics().manual_dialog_width, get_shell_metrics().manual_dialog_height)

        m = get_shell_metrics()
        p = get_shell_palette()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.manual_body_padding, m.manual_body_padding, m.manual_body_padding, m.manual_body_padding)
        layout.setSpacing(m.manual_section_spacing)

        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(m.manual_header_padding, m.manual_header_padding, m.manual_header_padding, m.manual_header_padding)
        header_layout.setSpacing(6)

        eyebrow = QLabel("Manual")
        eyebrow.setObjectName("eyebrow")
        header_layout.addWidget(eyebrow)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        header_layout.addWidget(title_label)

        meta = QLabel(self.manual_path.name)
        meta.setObjectName("summaryText")
        header_layout.addWidget(meta)
        layout.addWidget(header_card)

        viewer_card = QFrame()
        viewer_card.setObjectName("card")
        viewer_layout = QVBoxLayout(viewer_card)
        viewer_layout.setContentsMargins(8, 8, 8, 8)
        viewer_layout.setSpacing(0)

        viewer = QTextBrowser()
        viewer.setObjectName("manualViewer")
        viewer.setOpenExternalLinks(True)
        viewer.setFrameShape(QFrame.NoFrame)
        viewer.setReadOnly(True)
        viewer.document().setDocumentMargin(m.manual_body_padding - 4)
        viewer.document().setDefaultStyleSheet(
            f"""
            body {{ color: {p.text}; font-size: 13px; line-height: 1.55; }}
            h1, h2, h3, h4 {{ color: {p.text}; font-weight: 700; margin-top: 16px; margin-bottom: 8px; }}
            h1 {{ font-size: 24px; }}
            h2 {{ font-size: 19px; }}
            h3 {{ font-size: 16px; }}
            p {{ margin: 0 0 10px 0; }}
            ul, ol {{ margin: 0 0 12px 18px; }}
            li {{ margin-bottom: 6px; }}
            code {{ background: rgba(255,255,255,0.06); color: {p.accent_text}; padding: 2px 6px; border-radius: 6px; }}
            pre {{
                background: rgba(8, 10, 14, 0.55);
                border: 1px solid {p.control_border};
                border-radius: 12px;
                padding: 12px;
                margin: 10px 0 14px 0;
                color: {p.text};
                white-space: pre-wrap;
            }}
            blockquote {{
                margin: 10px 0;
                padding: 8px 12px;
                border-left: 3px solid {p.accent};
                background: rgba(61, 139, 255, 0.08);
                color: {p.text_muted};
            }}
            a {{ color: {p.accent_hover}; text-decoration: none; }}
            """
        )
        viewer.setStyleSheet(
            f"""
            QTextBrowser#manualViewer {{
                background: transparent;
                border: none;
                selection-background-color: rgba(61, 139, 255, 0.26);
            }}
            QTextBrowser#manualViewer QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 8px 0;
            }}
            QTextBrowser#manualViewer QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.14);
                border-radius: 5px;
                min-height: 24px;
            }}
            QTextBrowser#manualViewer QScrollBar::handle:vertical:hover {{
                background: rgba(255,255,255,0.24);
            }}
            QTextBrowser#manualViewer QScrollBar::add-line:vertical,
            QTextBrowser#manualViewer QScrollBar::sub-line:vertical,
            QTextBrowser#manualViewer QScrollBar::add-page:vertical,
            QTextBrowser#manualViewer QScrollBar::sub-page:vertical {{
                background: transparent;
                height: 0px;
            }}
            """
        )
        manual_body = _load_manual_html(self.manual_path)
        try:
            viewer.setMarkdown(manual_body)
        except Exception:
            viewer.setHtml(_manual_fallback_html(manual_body))
        self.viewer = viewer
        viewer_layout.addWidget(viewer)
        layout.addWidget(viewer_card, 1)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(m.primary_button_height)
        close_btn.clicked.connect(self.accept)
        action_row.addWidget(close_btn)
        layout.addLayout(action_row)


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
        self.subtitle_label.setVisible(False)

    def set_asset_count_visible(self, visible: bool) -> None:
        self.asset_count_badge.setVisible(False)
        self._update_badge_layout()

    def set_runtime_status_visible(self, visible: bool) -> None:
        self.runtime_status_badge.setVisible(False)
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
        self.badge_box.setVisible(False)

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
