from __future__ import annotations

from typing import Optional, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from contexthub.ui.qt.shell import get_shell_metrics, get_shell_palette
from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.icon_utils import get_icon


class ExportFoldoutCard(QFrame):
    """
    Standardized, high-quality Export Foldout Card for Contexthub-Apps.
    Supports a collapsible settings area, progress tracking, and unified 26px action footer.
    """
    
    run_clicked = Signal()
    reveal_clicked = Signal()
    export_clicked = Signal()
    format_changed = Signal(str)
    source_changed = Signal(str)

    def __init__(self, title: str = "Export", parent: Optional[QWidget] = None):
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

        # 1. Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        self.layout.addLayout(header_layout)

        # 2. Collapsible Details
        self.details = QWidget()
        self.details_layout = QVBoxLayout(self.details)
        self.details_layout.setContentsMargins(0, 4, 0, 4)
        self.details_layout.setSpacing(10)

        source_row = QHBoxLayout()
        source_row.setSpacing(6)
        self.source_btn = build_icon_button("Source", icon_name="folder", role="segment")
        self.task_btn = build_icon_button("Task", icon_name="layers", role="segment")
        self.custom_btn = build_icon_button("Custom", icon_name="edit-3", role="segment")
        
        for btn in [self.source_btn, self.task_btn, self.custom_btn]:
            btn.setCheckable(True)
            source_row.addWidget(btn, 1)
        
        self.source_btn.setChecked(True)
        self.details_layout.addLayout(source_row)

        self.out_combo = QComboBox()
        self.out_combo.setObjectName("compactField")
        self.details_layout.addWidget(self.out_combo)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Output file name...")
        self.name_edit.setObjectName("compactField")
        self.details_layout.addWidget(self.name_edit)

        opts_row = QHBoxLayout()
        self.cb_open = QCheckBox("Open folder")
        self.cb_meta = QCheckBox("Metadata")
        self.cb_open.setChecked(True)
        self.cb_meta.setChecked(True)
        opts_row.addWidget(self.cb_open)
        opts_row.addWidget(self.cb_meta)
        opts_row.addStretch(1)
        self.details_layout.addLayout(opts_row)

        self.layout.addWidget(self.details)

        # 3. Progress Section
        self.progress_container = QWidget()
        progress_vbox = QVBoxLayout(self.progress_container)
        progress_vbox.setContentsMargins(0, 0, 0, 0)
        progress_vbox.setSpacing(2)

        progress_header = QHBoxLayout()
        progress_header.addStretch(1)
        self.progress_percent = QLabel("0%")
        self.progress_percent.setObjectName("mutedSmall")
        progress_header.addWidget(self.progress_percent)
        
        self.progress_line_bg = QFrame()
        self.progress_line_bg.setStyleSheet(f"background: {self.p.surface_subtle_ghost}; height: 2px; border-radius: 1px;")
        self.progress_line_bg.setFixedHeight(2)
        
        self.progress_line_fg = QFrame(self.progress_line_bg)
        self.progress_line_fg.setStyleSheet(f"background: {self.p.accent}; height: 2px; border-radius: 1px;")
        self.progress_line_fg.setFixedWidth(0)
        
        progress_vbox.addLayout(progress_header)
        progress_vbox.addWidget(self.progress_line_bg)
        self.layout.addWidget(self.progress_container)

        # 4. Footer Action Row
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)

        self.toggle_btn = build_icon_button("", icon_name="chevron-down", role="icon")
        self.toggle_btn.setCheckable(True)
        
        self.reveal_btn = build_icon_button("", icon_name="folder-open", role="icon")
        self.cancel_btn = build_icon_button("Cancel", icon_name="x", role="ghost")
        self.cancel_btn.setVisible(False)
        
        self.out_format_combo = QComboBox()
        self.out_format_combo.setObjectName("compactField")
        self.out_format_combo.setFixedWidth(60)
        self.out_format_combo.setVisible(False) # Hide by default if no formats
        
        self.run_btn = build_icon_button(title, icon_name="play", role="primary")

        footer_layout.addWidget(self.toggle_btn)
        footer_layout.addWidget(self.reveal_btn)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self.out_format_combo)
        footer_layout.addSpacing(4)
        footer_layout.addWidget(self.cancel_btn)
        footer_layout.addWidget(self.run_btn, 1)
        
        self.layout.addLayout(footer_layout)

        self.toggle_btn.clicked.connect(self._handle_toggle)
        self.run_btn.clicked.connect(self.run_clicked.emit)
        self.reveal_btn.clicked.connect(self.reveal_clicked.emit)
        self.cancel_btn.clicked.connect(self.export_clicked.emit)
        self.out_format_combo.currentTextChanged.connect(self.format_changed.emit)

    def _handle_toggle(self):
        self.set_expanded(self.toggle_btn.isChecked())

    def set_expanded(self, expanded: bool):
        self.toggle_btn.setChecked(expanded)
        self.toggle_btn.setIcon(get_icon("chevron-up" if expanded else "chevron-down", color="#94a3b8"))
        self.details.setVisible(expanded)

    def set_progress(self, percentage: int, text: Optional[str] = None):
        percentage = max(0, min(100, percentage))
        self.progress_percent.setText(f"{percentage}%" if text is None else text)
        full_width = self.progress_line_bg.width()
        fg_width = int(full_width * (percentage / 100.0))
        self.progress_line_fg.setFixedWidth(fg_width)

    def set_formats(self, formats: List[str]):
        self.out_format_combo.clear()
        if not formats:
            self.out_format_combo.setVisible(False)
            return
        self.out_format_combo.addItems([f.upper() for f in formats])
        self.out_format_combo.setVisible(True)

    def set_running(self, running: bool):
        self.run_btn.setEnabled(not running)
        self.out_format_combo.setEnabled(not running)
        self.cancel_btn.setVisible(running)
        self.run_btn.setIcon(get_icon("loader" if running else "play", color="white"))
        if not running:
            self.set_progress(0, "Ready")


def build_export_foldout_card(title: str = "Export", *, expanded: bool = False) -> dict[str, object]:
    card_obj = ExportFoldoutCard(title)
    card_obj.set_expanded(expanded)
    return {
        "card": card_obj,
        "title_label": card_obj.title_label,
        "toggle_btn": card_obj.toggle_btn,
        "details": card_obj.details,
        "details_layout": card_obj.details_layout,
        "out_format_combo": card_obj.out_format_combo,
        "run_btn": card_obj.run_btn,
        "reveal_btn": card_obj.reveal_btn,
        "cancel_btn": card_obj.cancel_btn,
        "progress_percent": card_obj.progress_percent,
        "name_edit": card_obj.name_edit,
        "cb_open": card_obj.cb_open,
        "cb_meta": card_obj.cb_meta,
    }
