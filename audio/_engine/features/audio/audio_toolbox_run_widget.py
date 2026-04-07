from __future__ import annotations

from contexthub.ui.qt.shell import get_shell_metrics, get_shell_palette

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for audio_toolbox run widget.") from exc


class AudioRunWidget(QFrame):
    toggle_requested = Signal()
    browse_requested = Signal()
    source_requested = Signal()
    task_folder_requested = Signal()
    custom_requested = Signal()
    run_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._expanded = False
        self.setObjectName("card")
        m = get_shell_metrics()
        p = get_shell_palette()
        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        root = QVBoxLayout(self)
        root.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        root.setSpacing(8)

        self.expanded_body = QWidget()
        expanded = QVBoxLayout(self.expanded_body)
        expanded.setContentsMargins(0, 0, 0, 0)
        expanded.setSpacing(8)

        dir_row = QHBoxLayout()
        dir_row.setContentsMargins(0, 0, 0, 0)
        dir_row.setSpacing(6)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Custom output folder")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("iconBtn")
        self.browse_btn.clicked.connect(self.browse_requested.emit)
        dir_row.addWidget(self.output_dir_edit, 1)
        dir_row.addWidget(self.browse_btn, 0)
        expanded.addLayout(dir_row)

        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.setSpacing(6)
        self.source_btn = QPushButton("Source")
        self.source_btn.setCheckable(True)
        self.source_btn.setObjectName("segmentBtn")
        self.task_folder_btn = QPushButton("Task Folder")
        self.task_folder_btn.setCheckable(True)
        self.task_folder_btn.setObjectName("segmentBtn")
        self.custom_btn = QPushButton("Custom")
        self.custom_btn.setCheckable(True)
        self.custom_btn.setObjectName("segmentBtn")
        self.source_btn.clicked.connect(self.source_requested.emit)
        self.task_folder_btn.clicked.connect(self.task_folder_requested.emit)
        self.custom_btn.clicked.connect(self.custom_requested.emit)
        mode_row.addWidget(self.source_btn, 1)
        mode_row.addWidget(self.task_folder_btn, 1)
        mode_row.addWidget(self.custom_btn, 1)
        expanded.addLayout(mode_row)

        self.trim_check = QCheckBox("Trim selection")
        expanded.addWidget(self.trim_check)

        trim_row = QHBoxLayout()
        trim_row.setContentsMargins(0, 0, 0, 0)
        trim_row.setSpacing(6)
        self.trim_start_edit = QLineEdit()
        self.trim_start_edit.setPlaceholderText("Start 0:00")
        self.trim_end_edit = QLineEdit()
        self.trim_end_edit.setPlaceholderText("End 0:30")
        trim_row.addWidget(self.trim_start_edit, 1)
        trim_row.addWidget(self.trim_end_edit, 1)
        expanded.addLayout(trim_row)

        self.trim_hint = QLabel("Leave blank for start or end. Example: 0:12.5 or 1:02:03")
        self.trim_hint.setObjectName("mutedSmall")
        self.trim_hint.setWordWrap(True)
        expanded.addWidget(self.trim_hint)
        root.addWidget(self.expanded_body)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)

        status_col = QVBoxLayout()
        status_col.setContentsMargins(0, 0, 0, 0)
        status_col.setSpacing(0)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("sectionTitle")
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setObjectName("muted")
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("summaryText")
        self.detail_label.setWordWrap(True)
        self.detail_label.hide()
        status_col.addWidget(self.status_label)
        status_col.addWidget(self.progress_label)
        status_col.addWidget(self.detail_label)
        footer.addLayout(status_col, 1)

        self.export_format_combo = QComboBox()
        self.export_format_combo.setMinimumWidth(120)
        self.export_format_combo.setObjectName("compactField")
        self.toggle_btn = QPushButton("⋯")
        self.toggle_btn.setObjectName("iconBtn")
        self.toggle_btn.clicked.connect(self.toggle_requested.emit)
        self.run_btn = QPushButton("Run Task")
        self.run_btn.setProperty("buttonRole", "primary")
        self.run_btn.setMinimumWidth(220)
        self.run_btn.clicked.connect(self.run_requested.emit)
        footer.addWidget(self.export_format_combo, 0)
        footer.addWidget(self.toggle_btn, 0)
        footer.addWidget(self.run_btn, 0)
        root.addLayout(footer)

        self.set_expanded(False)
        self.set_trim_enabled(False)

    def set_expanded(self, visible: bool) -> None:
        self._expanded = visible
        self.expanded_body.setVisible(visible)
        self.export_format_combo.setVisible(self.export_format_combo.count() > 0)
        self.detail_label.setVisible(visible and bool(self.detail_label.text().strip()))
        self.toggle_btn.setText("⌃" if visible else "⋯")
        self.layout().activate()
        self.setMaximumHeight(16777215 if visible else self.minimumSizeHint().height())
        self.updateGeometry()

    def set_trim_enabled(self, enabled: bool) -> None:
        self.trim_check.setChecked(enabled)
        self.trim_start_edit.setEnabled(enabled)
        self.trim_end_edit.setEnabled(enabled)
        self.trim_hint.setVisible(enabled)
