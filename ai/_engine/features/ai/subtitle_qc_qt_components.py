from __future__ import annotations

from pathlib import Path
from typing import Any

from contexthub.ui.qt.shell import (
    build_shell_stylesheet,
    get_shell_metrics,
    qt_t,
    resolve_app_icon,
    set_button_role,
)

try:
    from PySide6.QtCore import QPoint, Qt, Signal
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QDialog,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for subtitle_qc components.") from exc


class ServiceBridge(QWidget):
    updated = Signal(dict)


class MediaPreviewHost(QFrame):
    def __init__(self, video_widget: QWidget | None = None) -> None:
        super().__init__()
        self.setObjectName("subtlePanel")
        self._video_widget = video_widget
        if self._video_widget is not None:
            self._video_widget.setParent(self)
            self._video_widget.hide()
        self.placeholder = QLabel(qt_t("meeting_notes.no_media", "Select a meeting file"), self)
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setWordWrap(True)

    def set_video_mode(self, enabled: bool) -> None:
        has_video = enabled and self._video_widget is not None
        if self._video_widget is not None:
            self._video_widget.setVisible(has_video)
        self.placeholder.setVisible(not has_video)

    def set_placeholder_text(self, text: str) -> None:
        self.placeholder.setText(text)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        rect = self.rect()
        if self._video_widget is not None:
            self._video_widget.setGeometry(rect)
        self.placeholder.setGeometry(rect)


class QueueDialog(QDialog):
    def __init__(self, parent: QWidget, service: Any, app_title: str) -> None:
        super().__init__(parent)
        self.service = service
        self.app_title = app_title
        self._drag_offset: QPoint | None = None
        self.setWindowTitle("Meeting Queue")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.resize(560, 620)
        self.setObjectName("queueDialog")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet(build_shell_stylesheet())

        app_root = Path(parent.app_root) if hasattr(parent, "app_root") else None
        icon_path = resolve_app_icon(app_root) if app_root else None
        icon = QIcon(str(icon_path)) if icon_path else QIcon()
        if not icon.isNull():
            self.setWindowIcon(icon)

        m = get_shell_metrics()
        shell = QFrame()
        shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(m.card_padding, m.header_padding_y_top, m.card_padding, m.card_padding)
        shell_layout.setSpacing(max(8, m.section_gap - 4))

        title_bar = QFrame()
        title_bar.setObjectName("panelTopBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        icon_label = QLabel()
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(m.header_icon_size, m.header_icon_size))
        title_layout.addWidget(icon_label)

        window_title = QLabel("Meeting Queue")
        window_title.setObjectName("windowTitle")
        title_layout.addWidget(window_title)
        title_layout.addStretch(1)

        self.min_btn = QPushButton("−")
        self.min_btn.setObjectName("titleBtn")
        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn = QPushButton("□")
        self.max_btn.setObjectName("titleBtn")
        self.max_btn.clicked.connect(self._toggle_maximize)
        self.title_close_btn = QPushButton("×")
        self.title_close_btn.setObjectName("titleBtnClose")
        self.title_close_btn.clicked.connect(self.reject)
        title_layout.addWidget(self.min_btn)
        title_layout.addWidget(self.max_btn)
        title_layout.addWidget(self.title_close_btn)
        shell_layout.addWidget(title_bar)

        body = QFrame()
        body.setObjectName("card")
        root = QVBoxLayout(body)
        root.setContentsMargins(m.card_padding, m.card_padding, m.card_padding, m.card_padding)
        root.setSpacing(m.section_gap)

        title = QLabel("Meeting Queue")
        title.setObjectName("sectionTitle")
        hint = QLabel("Select recordings for batch transcription or switch the current meeting.")
        hint.setObjectName("summaryText")
        hint.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        root.addWidget(self.list_widget, 1)

        buttons = QHBoxLayout()
        self.add_btn = QPushButton("Import")
        self.remove_btn = QPushButton("Remove")
        self.action_close_btn = QPushButton("Close")
        set_button_role(self.add_btn, "secondary")
        set_button_role(self.remove_btn, "secondary")
        set_button_role(self.action_close_btn, "primary")
        buttons.addWidget(self.add_btn)
        buttons.addWidget(self.remove_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.action_close_btn)
        root.addLayout(buttons)

        self.add_btn.clicked.connect(self._add_files)
        self.remove_btn.clicked.connect(self._remove_selected)
        self.list_widget.itemSelectionChanged.connect(self._apply_selection)
        self.action_close_btn.clicked.connect(self.accept)
        self.refresh()

        shell_layout.addWidget(body)

        dialog_root = QVBoxLayout(self)
        dialog_root.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        dialog_root.addWidget(shell)

    def refresh(self) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        selected = self.service.state.selected_asset
        selected_row = -1
        for index, asset in enumerate(self.service.state.queued_assets):
            item = QListWidgetItem(f"{asset.path.name}\n{asset.status.upper()} · {asset.confidence_summary}")
            item.setToolTip(str(asset.path))
            self.list_widget.addItem(item)
            if selected is not None and asset.path == selected:
                selected_row = index
        if selected_row >= 0:
            self.list_widget.setCurrentRow(selected_row)
        self.list_widget.blockSignals(False)

    def _apply_selection(self) -> None:
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.service.state.queued_assets):
            self.service.set_selected_asset(self.service.state.queued_assets[row].path)

    def _add_files(self) -> None:
        filters = "Media Files (*.mp4 *.mov *.avi *.mkv *.webm *.mp3 *.wav *.m4a *.flac *.ogg)"
        paths, _ = QFileDialog.getOpenFileNames(self, self.app_title, str(Path.home()), filters)
        if paths:
            self.service.add_inputs([Path(path) for path in paths])
            self.refresh()

    def _remove_selected(self) -> None:
        row = self.list_widget.currentRow()
        if row >= 0:
            self.service.remove_input_at(row)
            self.refresh()

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setText("□")
        else:
            self.showMaximized()
            self.max_btn.setText("❐")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)
