from __future__ import annotations

from pathlib import Path

from contexthub.ui.qt.shell import (
    HeaderSurface,
    apply_app_icon,
    attach_size_grip,
    build_shell_stylesheet,
    get_shell_metrics,
)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QMainWindow, QVBoxLayout, QWidget


def build_shell_window(
    window: QMainWindow,
    app_root: Path,
    title: str,
    subtitle: str,
    *,
    use_size_grip: bool,
) -> tuple[QWidget, QFrame, QVBoxLayout]:
    m = get_shell_metrics()
    central = QWidget()
    window.setCentralWidget(central)
    root = QVBoxLayout(central)
    root.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)

    shell = QFrame()
    shell.setObjectName("windowShell")
    shell_layout = QVBoxLayout(shell)
    shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
    shell_layout.setSpacing(m.section_gap)

    header = HeaderSurface(window, title, subtitle, app_root)
    header.set_header_visibility(show_subtitle=False, show_asset_count=False, show_runtime_status=False)
    shell_layout.addWidget(header)

    root.addWidget(shell)
    apply_app_icon(window, app_root)
    window.setStyleSheet(build_shell_stylesheet())
    return central, shell, shell_layout


def finish_shell_window(shell_layout: QVBoxLayout, shell: QFrame, *, use_size_grip: bool) -> None:
    if use_size_grip:
        attach_size_grip(shell_layout, shell)
