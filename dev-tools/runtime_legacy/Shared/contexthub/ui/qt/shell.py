from __future__ import annotations

from .header import HeaderSurface
from .manual import ManualDialog, open_manual_dialog
from .support import (
    apply_app_icon,
    refresh_runtime_preferences,
    resolve_app_icon,
    resolve_manual_path,
    runtime_settings_signature,
)
from .theme import (
    ShellMetrics,
    ShellPalette,
    ToneSpec,
    build_shell_stylesheet,
    get_shell_accent_cycle,
    get_shell_metrics,
    get_shell_palette,
    get_tone_spec,
    qt_t,
    set_badge_role,
    set_button_role,
    set_surface_role,
    set_transparent_surface,
)
from .widgets import CollapsibleSection, DropListWidget, ElidedLabel, VisibleSizeGrip

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt shell runtime.") from exc


def build_size_grip() -> QWidget:
    return VisibleSizeGrip(None)


def attach_size_grip(shell_layout: QVBoxLayout, shell_parent: QWidget) -> QWidget:
    grip_row = QHBoxLayout()
    grip_row.setContentsMargins(0, 0, 2, 0)
    grip_row.addStretch(1)
    grip = build_size_grip()
    grip.setParent(shell_parent)
    grip_row.addWidget(grip, 0, Qt.AlignRight | Qt.AlignBottom)
    shell_layout.addLayout(grip_row)
    return grip
