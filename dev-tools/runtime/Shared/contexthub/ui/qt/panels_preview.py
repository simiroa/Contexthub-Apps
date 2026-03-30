from __future__ import annotations

from pathlib import Path

from .shell import DropListWidget, get_shell_metrics, set_surface_role

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtWidgets import (
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidgetItem,
        QPushButton,
        QVBoxLayout,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt panel runtime.") from exc


class PreviewListPanel(QFrame):
    add_requested = Signal()
    preview_requested = Signal()
    remove_requested = Signal()
    clear_requested = Signal()
    selection_changed = Signal(int)
    files_dropped = Signal(list)

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
        self.preview_label.setMinimumHeight(m.preview_min_height)
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

        self.input_list = DropListWidget()
        self.input_list.currentRowChanged.connect(self.selection_changed.emit)
        self.input_list.files_dropped.connect(self.files_dropped.emit)
        layout.addWidget(self.input_list, 1)
        self._comparative_mode = "single"

        actions = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.preview_btn = QPushButton("Preview")
        self.remove_btn = QPushButton("Remove")
        self.clear_btn = QPushButton("Clear")
        self.add_btn.clicked.connect(self.add_requested.emit)
        self.preview_btn.clicked.connect(self.preview_requested.emit)
        self.remove_btn.clicked.connect(self.remove_requested.emit)
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        actions.addWidget(self.add_btn)
        actions.addWidget(self.preview_btn)
        actions.addWidget(self.remove_btn)
        actions.addWidget(self.clear_btn)
        layout.addLayout(actions)
        self.add_inputs_btn = self.add_btn
        self.set_preview_btn = self.preview_btn
        self.clear_input_btn = self.clear_btn

    def set_items(self, items: list[tuple[str, str]]) -> None:
        self.input_list.clear()
        for title, path in items:
            item = QListWidgetItem(title)
            item.setToolTip(path)
            self.input_list.addItem(item)

    def set_inputs(self, items: list[object]) -> None:
        self.input_list.clear()
        for entry in items:
            path = getattr(entry, "path", entry)
            kind = getattr(entry, "kind", "")
            title = Path(path).name if path else ""
            item = QListWidgetItem(title)
            tooltip = str(path)
            if kind:
                tooltip = f"{tooltip}\n{kind}"
            item.setToolTip(tooltip)
            self.input_list.addItem(item)

    def set_preview(self, title: object, meta: str = "") -> None:
        if meta:
            self.preview_label.setText(str(title))
            self.preview_meta.setText(meta)
            return

        path = Path(str(title))
        self.preview_label.setText(path.name or str(title))
        self.preview_meta.setText(str(title))

    def current_row(self) -> int:
        return self.input_list.currentRow()

    def retranslate(self, preview_title: str, list_title: str, list_hint: str = "") -> None:
        self.preview_title_label.setText(preview_title)
        self.list_title_label.setText(list_title)
        self.list_hint_label.setText(list_hint)
        self.add_btn.setText("Add")
        self.preview_btn.setText("Preview")
        self.remove_btn.setText("Remove")
        self.clear_btn.setText("Clear")

    def set_comparative_mode(self, mode: str) -> None:
        self._comparative_mode = mode


class AssetWorkspacePanel(PreviewListPanel):
    def __init__(self, title: str = "Assets", list_title: str = "Items", list_hint: str = ""):
        super().__init__(preview_title=title, list_title=list_title, list_hint=list_hint)


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
