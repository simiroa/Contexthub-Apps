from __future__ import annotations

from .theme_metrics import get_shell_metrics
from .theme_style_helpers import set_surface_role

try:
    from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QPlainTextEdit, QVBoxLayout
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt panel runtime.") from exc


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
