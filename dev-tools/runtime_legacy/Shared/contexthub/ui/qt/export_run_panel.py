from __future__ import annotations

from .export_panel_base import ExportPanelBase
from .theme_style_helpers import qt_t
from shared._engine.components.icon_button import build_icon_button

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QHBoxLayout
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt panel runtime.") from exc


class ExportRunPanel(ExportPanelBase):
    run_requested = Signal()
    reveal_requested = Signal()
    export_requested = Signal()
    toggle_requested = Signal()

    def __init__(self, title: str = "Execution"):
        super().__init__(title)
        self.root_layout.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(self.title_label)
        header.addStretch(1)
        self.toggle_btn = build_icon_button(qt_t("shared.details", "Details"), icon_name="chevron-down", role="subtle")
        self.toggle_btn.clicked.connect(self.toggle_requested.emit)
        header.addWidget(self.toggle_btn)
        self.root_layout.addLayout(header)
        self.root_layout.addWidget(self.summary_label)
        self.build_export_grid()
        self.root_layout.addWidget(self.details)
        self.root_layout.addWidget(self.progress_bar)

        footer = QHBoxLayout()
        footer.addWidget(self.status_label, 1)

        self.reveal_btn = build_icon_button(qt_t("shared.open_folder", "Open Folder"), icon_name="folder", role="secondary")
        self.reveal_btn.clicked.connect(self.reveal_requested.emit)
        footer.addWidget(self.reveal_btn)

        self.export_btn = build_icon_button(qt_t("shared.export", "Export"), icon_name="download", role="secondary")
        self.export_btn.clicked.connect(self.export_requested.emit)
        footer.addWidget(self.export_btn)

        self.run_button = build_icon_button(title, icon_name="play", role="primary")
        self.run_button.clicked.connect(self.run_requested.emit)
        self.run_btn = self.run_button
        footer.addWidget(self.run_button)
        self.root_layout.addLayout(footer)

    def set_expanded(self, expanded: bool) -> None:
        self.details.setVisible(expanded)
