from __future__ import annotations

from pathlib import Path

from .shell import DropListWidget, get_shell_metrics

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QPixmap, QPainter
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QProgressBar,
        QPushButton,
        QTextEdit,
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


class FixedParameterPanel(QFrame):
    def __init__(self, title: str, description: str = "", preset_label: str = "Preset"):
        super().__init__()
        self.setObjectName("card")
        m = get_shell_metrics()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        self.description_label = QLabel(description)
        self.description_label.setObjectName("summaryText")
        self.description_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label)

        preset_row = QHBoxLayout()
        self.preset_label = QLabel(preset_label)
        self.preset_combo = QComboBox()
        preset_row.addWidget(self.preset_label)
        preset_row.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_row)

        self.fields_container = QWidget()
        self.fields_layout = QVBoxLayout(self.fields_container)
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        self.fields_layout.setSpacing(8)
        layout.addWidget(self.fields_container, 1)

    def clear_fields(self) -> None:
        while self.fields_layout.count():
            item = self.fields_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_field(self, label: str, widget: QWidget) -> None:
        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)
        title = QLabel(label)
        title.setObjectName("eyebrow")
        row_layout.addWidget(title)
        row_layout.addWidget(widget)
        self.fields_layout.addWidget(row)


class PreviewListPanel(QFrame):
    add_requested = Signal()
    remove_requested = Signal()
    clear_requested = Signal()
    selection_changed = Signal()

    def __init__(self, preview_title: str = "Preview", list_title: str = "Items", list_hint: str = ""):
        super().__init__()
        self.setObjectName("card")
        m = get_shell_metrics()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        self.preview_title_label = QLabel(preview_title)
        self.preview_title_label.setObjectName("sectionTitle")
        layout.addWidget(self.preview_title_label)

        self.preview_label = QLabel("")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(180)
        self.preview_label.setWordWrap(True)
        self.preview_label.setObjectName("subtlePanel")
        layout.addWidget(self.preview_label)

        self.preview_meta = QLabel("")
        self.preview_meta.setObjectName("summaryText")
        self.preview_meta.setWordWrap(True)
        layout.addWidget(self.preview_meta)

        self.list_title_label = QLabel(list_title)
        self.list_title_label.setObjectName("sectionTitle")
        layout.addWidget(self.list_title_label)

        self.list_hint_label = QLabel(list_hint)
        self.list_hint_label.setObjectName("summaryText")
        self.list_hint_label.setWordWrap(True)
        layout.addWidget(self.list_hint_label)

        self.input_list = QListWidget()
        self.input_list.currentRowChanged.connect(self.selection_changed.emit)
        layout.addWidget(self.input_list, 1)

        actions = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.remove_btn = QPushButton("Remove")
        self.clear_btn = QPushButton("Clear")
        self.add_btn.clicked.connect(self.add_requested.emit)
        self.remove_btn.clicked.connect(self.remove_requested.emit)
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        actions.addWidget(self.add_btn)
        actions.addWidget(self.remove_btn)
        actions.addWidget(self.clear_btn)
        layout.addLayout(actions)

    def set_items(self, items: list[tuple[str, str]]) -> None:
        self.input_list.clear()
        for title, path in items:
            item = QListWidgetItem(title)
            item.setToolTip(path)
            self.input_list.addItem(item)

    def set_preview(self, title: str, meta: str) -> None:
        self.preview_label.setText(title)
        self.preview_meta.setText(meta)

    def current_row(self) -> int:
        return self.input_list.currentRow()


class ComparativePreviewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.left_pixmap = QPixmap()
        self.right_pixmap = QPixmap()
        self.mode = "single"
        self.split_ratio = 0.5
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(220)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.update()

    def set_pixmaps(self, left: QPixmap, right: QPixmap) -> None:
        self.left_pixmap = left
        self.right_pixmap = right
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.left_pixmap.isNull():
            return
        painter = QPainter(self)
        target = self.rect()
        pixmap = self.left_pixmap.scaled(target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (target.width() - pixmap.width()) // 2
        y = (target.height() - pixmap.height()) // 2
        painter.drawPixmap(x, y, pixmap)
        painter.end()
