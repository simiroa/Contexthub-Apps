from __future__ import annotations

from .theme_metrics import get_shell_metrics
from .theme_style_helpers import set_transparent_surface

try:
    from PySide6.QtWidgets import QCheckBox, QFrame, QGridLayout, QLabel, QLineEdit, QProgressBar, QVBoxLayout, QWidget
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt panel runtime.") from exc


class ExportPanelBase(QFrame):
    def __init__(self, title: str = "Export"):
        super().__init__()
        self.setObjectName("card")
        self._metrics = get_shell_metrics()

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(
            self._metrics.panel_padding,
            self._metrics.panel_padding,
            self._metrics.panel_padding,
            self._metrics.panel_padding,
        )
        self.root_layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryText")
        self.summary_label.setWordWrap(True)

        self.details = QWidget()
        set_transparent_surface(self.details)
        self.details_layout = QVBoxLayout(self.details)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        self.details_layout.setSpacing(8)

        self.form_grid = QGridLayout()
        self.form_grid.setContentsMargins(0, 0, 0, 0)
        self.form_grid.setHorizontalSpacing(8)
        self.form_grid.setVerticalSpacing(8)
        self.details_layout.addLayout(self.form_grid)

        self.output_dir_label = QLabel("Output Folder")
        self.output_dir_edit = QLineEdit()
        self.output_prefix_label = QLabel("File Name")
        self.output_prefix_edit = QLineEdit()
        self.open_folder_checkbox = QCheckBox("Open folder when done")
        self.export_session_checkbox = QCheckBox("Export session metadata")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("summaryText")

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("summaryText")

    def build_export_grid(self, *, include_browse_button: bool = False):
        browse_btn = None
        self.form_grid.addWidget(self.output_dir_label, 0, 0)
        self.form_grid.addWidget(self.output_dir_edit, 0, 1)
        if include_browse_button:
            from shared._engine.components.icon_button import build_icon_button

            browse_btn = build_icon_button("", icon_name="folder-open", role="subtle")
            browse_btn.setToolTip("Browse...")
            self.form_grid.addWidget(browse_btn, 0, 2)
        self.form_grid.addWidget(self.output_prefix_label, 1, 0)
        self.form_grid.addWidget(self.output_prefix_edit, 1, 1)
        self.form_grid.addWidget(self.open_folder_checkbox, 2, 0, 1, 2)
        self.form_grid.addWidget(self.export_session_checkbox, 3, 0, 1, 2)
        return browse_btn

    def refresh_summary(self) -> None:
        self.summary_label.setText(self._build_summary_text())

    def _build_summary_text(self) -> str:
        parts = [self.output_dir_edit.text().strip(), self.output_prefix_edit.text().strip()]
        return " / ".join(part for part in parts if part)

    def set_values(self, output_dir: str, prefix: str, open_folder: bool, export_session: bool) -> None:
        self.output_dir_edit.setText(output_dir)
        self.output_prefix_edit.setText(prefix)
        self.open_folder_checkbox.setChecked(open_folder)
        self.export_session_checkbox.setChecked(export_session)
        self.refresh_summary()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{int(value)}%")

