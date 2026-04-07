from __future__ import annotations

from .theme_metrics import get_shell_metrics
from .theme_style_helpers import qt_t, set_surface_role
from shared._engine.components.icon_button import build_icon_button

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QVBoxLayout
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt panel runtime.") from exc


class QueueManagerPanel(QFrame):
    add_requested = Signal()
    remove_requested = Signal()
    clear_requested = Signal()
    retry_requested = Signal()
    pause_requested = Signal()

    def __init__(self, title: str = "Queue"):
        super().__init__()
        self.setObjectName("card")
        m = get_shell_metrics()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        self.count_label = QLabel("0")
        self.count_label.setObjectName("summaryText")
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.count_label)
        layout.addLayout(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.pause_btn = build_icon_button(qt_t("shared.pause", "Pause"), icon_name="pause", role="secondary")
        self.retry_btn = build_icon_button(qt_t("shared.retry", "Retry Failed"), icon_name="refresh-cw", role="secondary")
        self.remove_btn = build_icon_button(qt_t("shared.remove_selected", "Remove Selected"), icon_name="trash-2", role="ghost")
        toolbar.addWidget(self.pause_btn)
        toolbar.addWidget(self.retry_btn)
        toolbar.addWidget(self.remove_btn)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.summary_panel = QFrame()
        set_surface_role(self.summary_panel, "subtle")
        summary_layout = QHBoxLayout(self.summary_panel)
        summary_layout.setContentsMargins(max(8, m.panel_padding - 4), max(8, m.panel_padding - 4), max(8, m.panel_padding - 4), max(8, m.panel_padding - 4))
        summary_layout.setSpacing(12)
        self.active_label = QLabel("Active: 0")
        self.active_label.setObjectName("summaryText")
        self.failed_label = QLabel("Failed: 0")
        self.failed_label.setObjectName("summaryText")
        self.completed_label = QLabel("Done: 0")
        self.completed_label.setObjectName("summaryText")
        summary_layout.addWidget(self.active_label)
        summary_layout.addWidget(self.failed_label)
        summary_layout.addWidget(self.completed_label)
        summary_layout.addStretch(1)
        layout.addWidget(self.summary_panel)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        self.pause_btn.clicked.connect(self.pause_requested.emit)
        self.retry_btn.clicked.connect(self.retry_requested.emit)
        self.remove_btn.clicked.connect(self.remove_requested.emit)
