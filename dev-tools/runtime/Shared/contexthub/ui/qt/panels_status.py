from __future__ import annotations

from .shell import get_shell_metrics, set_button_role, set_surface_role

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import (
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QPlainTextEdit,
        QPushButton,
        QVBoxLayout,
    )
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
        self.pause_btn = QPushButton("Pause")
        set_button_role(self.pause_btn, "secondary")
        self.retry_btn = QPushButton("Retry Failed")
        set_button_role(self.retry_btn, "secondary")
        self.remove_btn = QPushButton("Remove Selected")
        set_button_role(self.remove_btn, "ghost")
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


class ResultInspectorPanel(QFrame):
    def __init__(self, title: str = "Result Inspector"):
        super().__init__()
        self.setObjectName("card")
        m = get_shell_metrics()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        layout.addWidget(self.title_label)

        body = QHBoxLayout()
        body.setSpacing(10)
        self.key_list = QListWidget()
        self.key_list.setMinimumWidth(180)
        set_surface_role(self.key_list.viewport(), "subtle")
        body.addWidget(self.key_list, 0)

        self.detail_panel = QFrame()
        set_surface_role(self.detail_panel, "subtle")
        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(max(8, m.panel_padding - 4), max(8, m.panel_padding - 4), max(8, m.panel_padding - 4), max(8, m.panel_padding - 4))
        detail_layout.setSpacing(8)
        self.summary_label = QLabel("Select a result field to inspect details.")
        self.summary_label.setObjectName("summaryText")
        self.summary_label.setWordWrap(True)
        self.detail_text = QPlainTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("Inspector details")
        detail_layout.addWidget(self.summary_label)
        detail_layout.addWidget(self.detail_text, 1)
        body.addWidget(self.detail_panel, 1)
        layout.addLayout(body)
