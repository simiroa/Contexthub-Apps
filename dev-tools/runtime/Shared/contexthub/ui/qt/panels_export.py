from __future__ import annotations

from .shell import get_shell_metrics, set_button_role, set_transparent_surface

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import (
        QCheckBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QProgressBar,
        QPushButton,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt panel runtime.") from exc


class ExportRunPanel(QFrame):
    run_requested = Signal()
    reveal_requested = Signal()
    export_requested = Signal()
    toggle_requested = Signal()

    def __init__(self, title: str = "Execution"):
        super().__init__()
        self.setObjectName("card")
        m = get_shell_metrics()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        header.addWidget(self.title_label)
        header.addStretch(1)
        self.toggle_btn = QToolButton()
        self.toggle_btn.setText("Details")
        self.toggle_btn.clicked.connect(self.toggle_requested.emit)
        header.addWidget(self.toggle_btn)
        layout.addLayout(header)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryText")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.details = QWidget()
        set_transparent_surface(self.details)
        details_layout = QGridLayout(self.details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setHorizontalSpacing(8)
        details_layout.setVerticalSpacing(8)

        self.output_dir_label = QLabel("Output Folder")
        self.output_dir_edit = QLineEdit()
        self.output_prefix_label = QLabel("File Name")
        self.output_prefix_edit = QLineEdit()
        self.open_folder_checkbox = QCheckBox("Open folder when done")
        self.export_session_checkbox = QCheckBox("Export session metadata")

        details_layout.addWidget(self.output_dir_label, 0, 0)
        details_layout.addWidget(self.output_dir_edit, 0, 1)
        details_layout.addWidget(self.output_prefix_label, 1, 0)
        details_layout.addWidget(self.output_prefix_edit, 1, 1)
        details_layout.addWidget(self.open_folder_checkbox, 2, 0, 1, 2)
        details_layout.addWidget(self.export_session_checkbox, 3, 0, 1, 2)
        layout.addWidget(self.details)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        footer = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("summaryText")
        footer.addWidget(self.status_label, 1)

        self.reveal_btn = QPushButton("Open Folder")
        self.reveal_btn.clicked.connect(self.reveal_requested.emit)
        footer.addWidget(self.reveal_btn)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_requested.emit)
        footer.addWidget(self.export_btn)

        self.run_button = QPushButton(title)
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self.run_requested.emit)
        self.run_btn = self.run_button
        footer.addWidget(self.run_button)
        layout.addLayout(footer)

    def set_values(self, output_dir: str, prefix: str, open_folder: bool, export_session: bool) -> None:
        self.output_dir_edit.setText(output_dir)
        self.output_prefix_edit.setText(prefix)
        self.open_folder_checkbox.setChecked(open_folder)
        self.export_session_checkbox.setChecked(export_session)
        self.refresh_summary()

    def set_expanded(self, expanded: bool) -> None:
        self.details.setVisible(expanded)

    def refresh_summary(self) -> None:
        self.summary_label.setText(f"{self.output_dir_edit.text()} / {self.output_prefix_edit.text()}")

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)


class ExportFoldoutPanel(QFrame):
    run_requested = Signal()
    reveal_requested = Signal()
    export_requested = Signal()
    cancel_requested = Signal()
    toggled = Signal(bool)
    toggle_requested = Signal()

    def __init__(self, title: str = "Export"):
        super().__init__()
        self.setObjectName("card")
        m = get_shell_metrics()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        layout.addWidget(self.title_label)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryText")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.details = QWidget()
        set_transparent_surface(self.details)
        self.details_layout = QVBoxLayout(self.details)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        self.details_layout.setSpacing(8)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        self.output_dir_label = QLabel("Output Folder")
        self.output_dir_edit = QLineEdit()
        self.output_prefix_label = QLabel("File Name")
        self.output_prefix_edit = QLineEdit()
        self.open_folder_checkbox = QCheckBox("Open folder when done")
        self.export_session_checkbox = QCheckBox("Export session metadata")
        self.export_session_json = self.export_session_checkbox
        grid.addWidget(self.output_dir_label, 0, 0)
        grid.addWidget(self.output_dir_edit, 0, 1)
        grid.addWidget(self.output_prefix_label, 1, 0)
        grid.addWidget(self.output_prefix_edit, 1, 1)
        grid.addWidget(self.open_folder_checkbox, 2, 0, 1, 2)
        grid.addWidget(self.export_session_checkbox, 3, 0, 1, 2)
        self.details_layout.addLayout(grid)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.details_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("summaryText")
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("summaryText")
        self.details_layout.addWidget(self.status_label)
        self.details_layout.addWidget(self.progress_label)
        layout.addWidget(self.details)

        footer = QHBoxLayout()
        footer.setSpacing(6)
        self.reveal_btn = QPushButton("Open")
        set_button_role(self.reveal_btn, "secondary")
        self.cancel_btn = QPushButton("Cancel")
        set_button_role(self.cancel_btn, "ghost")
        self.export_btn = QPushButton("Export")
        set_button_role(self.export_btn, "secondary")
        self.run_btn = QPushButton(title)
        set_button_role(self.run_btn, "primary")
        self.run_button = self.run_btn
        self.toggle_btn = QToolButton()
        self.toggle_btn.setObjectName("iconBtn")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setText("v")
        footer.addWidget(self.reveal_btn, 0)
        footer.addWidget(self.cancel_btn, 0)
        footer.addWidget(self.export_btn, 0)
        footer.addWidget(self.run_btn, 1)
        footer.addWidget(self.toggle_btn, 0)
        layout.addLayout(footer)

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
        self.toggle_btn.setText("^" if expanded else "v")
        self.details.setVisible(expanded)
        self.toggled.emit(expanded)

    def set_values(self, output_dir: str, prefix: str, open_folder: bool, export_session: bool) -> None:
        self.output_dir_edit.setText(output_dir)
        self.output_prefix_edit.setText(prefix)
        self.open_folder_checkbox.setChecked(open_folder)
        self.export_session_checkbox.setChecked(export_session)
        self.refresh_summary()

    def refresh_summary(self) -> None:
        summary = self.output_dir_edit.text().strip()
        prefix = self.output_prefix_edit.text().strip()
        if prefix:
            summary = f"{summary} / {prefix}" if summary else prefix
        self.summary_label.setText(summary)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{int(value)}%")

    def retranslate(self, title: str) -> None:
        self.title_label.setText(title)
        self.run_btn.setText(title)
