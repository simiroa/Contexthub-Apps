from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from contexthub.ui.qt.shell import get_shell_metrics, get_shell_palette
from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.icon_utils import get_icon


class CollapsibleSection(QFrame):
    """
    Standardized Collapsible Section for Contexthub-Apps.
    Features a clean 26px header, dynamic SVG chevron, and proper state management.
    """
    
    toggled = Signal(bool)

    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.m = get_shell_metrics()
        self.p = get_shell_palette()
        self.setObjectName("card")
        self._init_ui(title)
        self.set_expanded(False)

    def _init_ui(self, title: str):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(self.m.panel_padding, self.m.panel_padding, self.m.panel_padding, self.m.panel_padding)
        self.layout.setSpacing(self.m.section_gap)

        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        
        self.toggle_btn = build_icon_button("", icon_name="chevron-down", role="icon")
        self.toggle_btn.setCheckable(True)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.toggle_btn)
        self.layout.addLayout(header_layout)

        # Summary / State Label (Visible when collapsed)
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryText")
        self.summary_label.setWordWrap(True)
        self.layout.addWidget(self.summary_label)

        # Content Area
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(self.m.section_gap)
        self.layout.addWidget(self.content)

        # Connections
        self.toggle_btn.clicked.connect(self._handle_toggle)

    def _handle_toggle(self):
        self.set_expanded(self.toggle_btn.isChecked())
        self.toggled.emit(self.toggle_btn.isChecked())

    def set_expanded(self, expanded: bool):
        self.toggle_btn.setChecked(expanded)
        self.toggle_btn.setIcon(get_icon("chevron-up" if expanded else "chevron-down", color="#94a3b8"))
        self.content.setVisible(expanded)
        self.summary_label.setVisible(not expanded)

    def set_summary(self, text: str):
        self.summary_label.setText(text)


def build_collapsible_section(title: str, *, expanded: bool = False) -> dict[str, object]:
    section = CollapsibleSection(title)
    section.set_expanded(expanded)
    
    return {
        "card": section,
        "toggle_btn": section.toggle_btn,
        "title_label": section.title_label,
        "summary_label": section.summary_label,
        "content": section.content,
        "content_layout": section.content_layout,
    }
