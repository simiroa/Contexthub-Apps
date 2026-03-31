from __future__ import annotations

from .export_panel_base import ExportPanelBase
from .theme_style_helpers import qt_t
from shared._engine.components.icon_button import build_icon_button

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt panel runtime.") from exc


class ExportFoldoutPanel(ExportPanelBase):
    run_requested = Signal()
    reveal_requested = Signal()
    export_requested = Signal()
    cancel_requested = Signal()
    toggled = Signal(bool)
    toggle_requested = Signal()

    def __init__(self, title: str = "Export"):
        super().__init__(title)
        self.root_layout.setSpacing(8)

        self.root_layout.addWidget(self.title_label)
        self.root_layout.addWidget(self.summary_label)
        self.browse_btn = self.build_export_grid(include_browse_button=True)
        self.export_session_json = self.export_session_checkbox
        self.progress_bar.setTextVisible(False)
        self.details_layout.addWidget(self.progress_bar)
        self.details_layout.addWidget(self.status_label)
        self.details_layout.addWidget(self.progress_label)
        self.root_layout.addWidget(self.details)

        footer = QHBoxLayout()
        footer.setSpacing(6)
        self.reveal_btn = build_icon_button(qt_t("shared.open", "Open"), icon_name="folder", role="secondary")
        self.cancel_btn = build_icon_button(qt_t("shared.cancel", "Cancel"), icon_name="x", role="ghost")
        self.export_btn = build_icon_button(qt_t("shared.export", "Export"), icon_name="download", role="secondary")
        self.run_btn = build_icon_button(title, icon_name="play", role="primary")
        self.run_button = self.run_btn
        self.toggle_btn = build_icon_button("", icon_name="chevron-down", role="subtle")
        self.toggle_btn.setCheckable(True)
        footer.addWidget(self.reveal_btn, 0)
        footer.addWidget(self.cancel_btn, 0)
        footer.addWidget(self.export_btn, 0)
        footer.addWidget(self.run_btn, 1)
        footer.addWidget(self.toggle_btn, 0)
        self.root_layout.addLayout(footer)

        self.reveal_btn.clicked.connect(self.reveal_requested.emit)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        self.export_btn.clicked.connect(self.export_requested.emit)
        self.run_btn.clicked.connect(self.run_requested.emit)
        self.toggle_btn.clicked.connect(self.toggle_requested.emit)
        self.set_expanded(False)

    def set_expanded(self, expanded: bool) -> None:
        self.toggle_btn.blockSignals(True)
        self.toggle_btn.setChecked(expanded)
        self.toggle_btn.blockSignals(False)
        from shared._engine.components.icon_utils import get_icon

        self.toggle_btn.setIcon(get_icon("chevron-up" if expanded else "chevron-down", color="primary"))
        self.details.setVisible(expanded)
        self.toggled.emit(expanded)

    def retranslate(self, title: str) -> None:
        self.title_label.setText(title)
        self.run_btn.setText(title)
