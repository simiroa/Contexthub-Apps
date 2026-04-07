from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.panels import ExportFoldoutPanel
from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    set_surface_role,
    qt_t,
)
from shared._engine.components.icon_button import build_icon_button
from features.image.merge_to_exr.service import ExrMergeService

try:
    from PySide6.QtCore import QEvent, Qt, QTimer
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for merge_to_exr.") from exc

APP_TITLE = qt_t("merge_to_exr.title", "Merge to EXR")
APP_SUBTITLE = qt_t("merge_to_exr.subtitle", "Build a multilayer EXR from ordered image layers.")


class LayerRowWidget(QFrame):
    def __init__(self, index: int, channel, on_select, on_update):
        super().__init__()
        self._index = index
        self._on_select = on_select
        self._on_update = on_update
        self.setObjectName("subtlePanel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(channel.enabled)
        self.enabled_check.setToolTip("Enabled")
        layout.addWidget(self.enabled_check, 0)

        self.name_edit = QLineEdit(channel.target_name)
        self.name_edit.setPlaceholderText("Layer")
        self.name_edit.setMinimumWidth(180)
        layout.addWidget(self.name_edit, 2)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["RGB", "RGBA", "L", "R", "G", "B", "A"])
        self.mode_combo.setCurrentText(channel.mode)
        self.mode_combo.setMinimumWidth(88)
        layout.addWidget(self.mode_combo, 0)

        self.depth_combo = QComboBox()
        self.depth_combo.addItems(["HALF", "FLOAT", "UINT"])
        self.depth_combo.setCurrentText(channel.depth)
        self.depth_combo.setMinimumWidth(92)
        layout.addWidget(self.depth_combo, 0)

        self.invert_check = QCheckBox("Inv")
        self.invert_check.setChecked(channel.invert)
        self.invert_check.setToolTip("Invert")
        layout.addWidget(self.invert_check, 0)

        self.linear_check = QCheckBox("Lin")
        self.linear_check.setChecked(channel.linear)
        self.linear_check.setToolTip("Linearize")
        layout.addWidget(self.linear_check, 0)

        self.meta_label = QLabel(Path(channel.source_file or "-").name)
        self.meta_label.setObjectName("summaryText")
        self.meta_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.meta_label.setToolTip(channel.source_file or "-")
        layout.addWidget(self.meta_label, 1)

        self.enabled_check.toggled.connect(lambda checked: self._on_update(self._index, enabled=checked))
        self.name_edit.textChanged.connect(lambda text: self._on_update(self._index, target_name=text))
        self.mode_combo.currentTextChanged.connect(lambda text: self._on_update(self._index, mode=text))
        self.depth_combo.currentTextChanged.connect(lambda text: self._on_update(self._index, depth=text))
        self.invert_check.toggled.connect(lambda checked: self._on_update(self._index, invert=checked))
        self.linear_check.toggled.connect(lambda checked: self._on_update(self._index, linear=checked))

    def mousePressEvent(self, event):
        self._on_select(self._index)
        super().mousePressEvent(event)


class MergeToExrWindow(QMainWindow):
    def __init__(self, service: ExrMergeService, app_root: Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = app_root
        self._drop_targets: list[QWidget] = []

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(940, 760)
        self.setMinimumSize(760, 620)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._bind_actions()
        self._install_drop_targets()

        if targets:
            self.service.add_inputs(targets)
        self._sync_export_values()
        self._refresh_all()

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)
        root.setSpacing(m.section_gap)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
        self.header_surface.set_header_visibility(show_subtitle=True, show_asset_count=True, show_runtime_status=True)
        self.header_surface.open_webui_btn.hide()
        shell_layout.addWidget(self.header_surface)

        self.layer_card = QFrame()
        self.layer_card.setObjectName("card")
        layer_layout = QVBoxLayout(self.layer_card)
        layer_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layer_layout.setSpacing(10)

        title = QLabel(qt_t("merge_to_exr.layer_stack", "Layer Stack"))
        title.setObjectName("sectionTitle")
        layer_layout.addWidget(title)

        hint = QLabel(qt_t("merge_to_exr.hint", "Rename, map, depth-set, invert, and linearize directly in the layer rows."))
        hint.setObjectName("summaryText")
        hint.setWordWrap(True)
        layer_layout.addWidget(hint)

        toolbar = QHBoxLayout()
        self.add_btn = build_icon_button(qt_t("merge_to_exr.add", "Add Images"), icon_name="plus", role="secondary")
        self.remove_btn = build_icon_button(qt_t("merge_to_exr.remove", "Remove"), icon_name="minus", role="ghost")
        self.up_btn = build_icon_button(qt_t("merge_to_exr.up", "Move Up"), icon_name="chevron-up", role="ghost")
        self.down_btn = build_icon_button(qt_t("merge_to_exr.down", "Move Down"), icon_name="chevron-down", role="ghost")
        self.clear_btn = build_icon_button(qt_t("merge_to_exr.clear", "Clear"), icon_name="trash-2", role="ghost")
        for button in (self.add_btn, self.remove_btn, self.up_btn, self.down_btn, self.clear_btn):
            toolbar.addWidget(button)
        layer_layout.addLayout(toolbar)

        self.header_row = QFrame()
        self.header_row.setObjectName("subtlePanel")
        header_row_layout = QHBoxLayout(self.header_row)
        header_row_layout.setContentsMargins(10, 6, 10, 6)
        header_row_layout.setSpacing(8)
        for text, stretch, align in [
            ("On", 0, Qt.AlignCenter),
            ("Layer", 2, Qt.AlignLeft),
            ("Type", 0, Qt.AlignLeft),
            ("Depth", 0, Qt.AlignLeft),
            ("Inv", 0, Qt.AlignCenter),
            ("Lin", 0, Qt.AlignCenter),
            ("Source", 1, Qt.AlignRight),
        ]:
            label = QLabel(text)
            label.setObjectName("eyebrow")
            label.setAlignment(align | Qt.AlignVCenter)
            header_row_layout.addWidget(label, stretch)
        layer_layout.addWidget(self.header_row)

        self.layer_list = QListWidget()
        self.layer_list.setMinimumHeight(260)
        layer_layout.addWidget(self.layer_list, 1)

        self.drop_hint = QLabel(qt_t("merge_to_exr.drop_hint", "Drop image files anywhere in this window to append new EXR layers."))
        self.drop_hint.setObjectName("summaryText")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setWordWrap(True)
        layer_layout.addWidget(self.drop_hint)

        shell_layout.addWidget(self.layer_card, 1)

        self.export_panel = ExportFoldoutPanel(qt_t("merge_to_exr.run", "Export EXR"))
        self.export_panel.export_btn.hide()
        self.export_panel.export_session_checkbox.hide()
        self.export_panel.set_expanded(False)
        shell_layout.addWidget(self.export_panel, 0)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)
        self._set_drop_highlight(False)

    def _bind_actions(self) -> None:
        self.add_btn.clicked.connect(self._pick_inputs)
        self.remove_btn.clicked.connect(self._remove_selected)
        self.up_btn.clicked.connect(self._move_up)
        self.down_btn.clicked.connect(self._move_down)
        self.clear_btn.clicked.connect(self._clear_inputs)
        self.layer_list.currentRowChanged.connect(self._on_row_changed)
        self.export_panel.run_requested.connect(self._run_export)
        if hasattr(self.export_panel, "reveal_requested"):
            self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        if hasattr(self.export_panel, "toggle_requested"):
            self.export_panel.toggle_requested.connect(self._toggle_export_details)

    def _install_drop_targets(self) -> None:
        targets = [self, self.centralWidget(), self.window_shell, self.layer_card, self.layer_list, self.layer_list.viewport()]
        for target in targets:
            if target is None:
                continue
            target.setAcceptDrops(True)
            target.installEventFilter(self)
            self._drop_targets.append(target)

    def _sync_export_values(self) -> None:
        opts = self.service.state.output_options
        self.export_panel.set_values(
            str(opts.output_dir),
            opts.file_prefix,
            opts.open_folder_after_run,
            opts.export_session_json,
        )

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            APP_TITLE,
            "",
            "Images (*.png *.jpg *.jpeg *.tga *.bmp *.tif *.tiff *.exr)",
        )
        if files:
            self.service.add_inputs(files)
            self._refresh_all()

    def _remove_selected(self) -> None:
        self.service.remove_selected()
        self._refresh_all()

    def _move_up(self) -> None:
        self.service.move_selected_up()
        self._refresh_all()

    def _move_down(self) -> None:
        self.service.move_selected_down()
        self._refresh_all()

    def _clear_inputs(self) -> None:
        self.service.clear_inputs()
        self._refresh_all()

    def _on_row_changed(self, row: int) -> None:
        self.service.set_selected_index(row)
        self._refresh_buttons()

    def _refresh_all(self) -> None:
        self._refresh_list()
        self._refresh_buttons()
        self._refresh_header()
        self._set_export_status(self.service.state.status_text, self.service.state.detail_text)

    def _refresh_list(self) -> None:
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for index, channel in enumerate(self.service.state.channels):
            item = QListWidgetItem()
            item.setToolTip(channel.source_file or "-")
            row_widget = LayerRowWidget(index, channel, self._select_row, self._update_channel_from_row)
            item.setSizeHint(row_widget.sizeHint())
            self.layer_list.addItem(item)
            self.layer_list.setItemWidget(item, row_widget)
        if 0 <= self.service.state.selected_index < self.layer_list.count():
            self.layer_list.setCurrentRow(self.service.state.selected_index)
        self.layer_list.blockSignals(False)
        self.drop_hint.setText(
            qt_t("merge_to_exr.drop_hint_empty", "Drop image files anywhere in this window to add EXR layers.")
            if not self.service.state.channels
            else qt_t("merge_to_exr.drop_hint_more", "Drop more image files anywhere in this window to append new EXR layers.")
        )

    def _refresh_buttons(self) -> None:
        count = len(self.service.state.channels)
        index = self.service.state.selected_index
        has_selection = 0 <= index < count
        self.remove_btn.setEnabled(has_selection)
        self.clear_btn.setEnabled(count > 0)
        self.up_btn.setEnabled(has_selection and index > 0)
        self.down_btn.setEnabled(has_selection and index < count - 1)
        self._set_run_enabled(count > 0 and not self.service.state.is_exporting)

    def _refresh_header(self) -> None:
        count = len(self.service.state.channels)
        enabled = len([channel for channel in self.service.state.channels if channel.enabled])
        self.header_surface.set_asset_count(count)
        badge_text = f"{enabled} active" if count else "Ready"
        if self.service.state.error_text:
            badge_text = "Error"
        self.header_surface.runtime_status_badge.setText(badge_text)

    def _toggle_export_details(self) -> None:
        self.export_panel.set_expanded(not self.export_panel.details.isVisible())

    def _sync_output_options_from_panel(self) -> None:
        panel = self.export_panel
        self.service.update_output_options(
            panel.output_dir_edit.text(),
            panel.output_prefix_edit.text(),
            panel.open_folder_checkbox.isChecked(),
            panel.export_session_checkbox.isChecked(),
        )
        panel.refresh_summary()

    def _reveal_output_dir(self) -> None:
        self._sync_output_options_from_panel()
        self.service.reveal_output_dir()

    def _run_export(self) -> None:
        self._sync_output_options_from_panel()
        missing = self.service.get_missing_dependencies()
        if missing:
            self._set_export_status("Missing dependencies", ", ".join(missing))
            return

        self.service.state.is_exporting = True
        self._set_run_enabled(False)
        self._set_export_progress(0)
        self._set_export_status("Exporting EXR...", "")

        def _on_progress(progress: float, message: str) -> None:
            QTimer.singleShot(0, lambda: self._set_export_progress(int(progress * 100)))
            QTimer.singleShot(0, lambda: self._set_export_status("Exporting EXR...", message))

        def _on_complete(success: bool, message: str) -> None:
            QTimer.singleShot(0, lambda: self._finalize_export(success, message))

        self.service.export_exr(_on_progress, _on_complete)

    def _finalize_export(self, success: bool, message: str) -> None:
        self.service.state.is_exporting = False
        self._set_run_enabled(True)
        self._refresh_buttons()
        if success:
            output = Path(message)
            self._set_export_progress(100)
            self._set_export_status("EXR export complete", output.name)
            if self.service.state.output_options.open_folder_after_run:
                self.service.reveal_output_dir()
        else:
            self.service.state.error_text = message
            self._set_export_status("EXR export failed", message)
        self._refresh_header()

    def _set_export_status(self, status: str, detail: str) -> None:
        text = status if not detail else f"{status} - {detail}"
        if hasattr(self.export_panel, "set_status"):
            self.export_panel.set_status(text)
            return
        if hasattr(self.export_panel, "status_label"):
            self.export_panel.status_label.setText(text)

    def _set_export_progress(self, value: int) -> None:
        if hasattr(self.export_panel, "set_progress"):
            self.export_panel.set_progress(value)
            return
        if hasattr(self.export_panel, "progress_bar"):
            self.export_panel.progress_bar.setValue(value)

    def _set_run_enabled(self, enabled: bool) -> None:
        button = getattr(self.export_panel, "run_button", None) or getattr(self.export_panel, "run_btn", None)
        if button is not None:
            button.setEnabled(enabled)

    def _select_row(self, index: int) -> None:
        self.layer_list.setCurrentRow(index)

    def _update_channel_from_row(self, index: int, **changes: object) -> None:
        self.service.update_channel(index, **changes)
        self._refresh_header()

    def _extract_image_paths(self, mime_data) -> list[Path]:
        if not mime_data.hasUrls():
            return []
        allowed = {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".tif", ".tiff", ".exr"}
        paths: list[Path] = []
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() in allowed:
                paths.append(path)
        return paths

    def _set_drop_highlight(self, active: bool) -> None:
        if active:
            set_surface_role(self.layer_card, "card", "accent")
            self.drop_hint.setText("Drop image files to append new EXR layers.")
        else:
            set_surface_role(self.layer_card, "card", "default")
            self.drop_hint.setText(
                qt_t("merge_to_exr.drop_hint_empty", "Drop image files anywhere in this window to add EXR layers.")
                if not self.service.state.channels
                else qt_t("merge_to_exr.drop_hint_more", "Drop more image files anywhere in this window to append new EXR layers.")
            )

    def eventFilter(self, obj, event):
        if obj in self._drop_targets:
            if event.type() == QEvent.DragEnter:
                paths = self._extract_image_paths(event.mimeData())
                if paths:
                    self._set_drop_highlight(True)
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.DragMove:
                paths = self._extract_image_paths(event.mimeData())
                if paths:
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.DragLeave:
                self._set_drop_highlight(False)
            elif event.type() == QEvent.Drop:
                paths = self._extract_image_paths(event.mimeData())
                self._set_drop_highlight(False)
                if paths:
                    self.service.add_inputs([str(path) for path in paths])
                    self._refresh_all()
                    event.acceptProposedAction()
                    return True
        return super().eventFilter(obj, event)


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app_root = Path(__file__).resolve().parents[3] / "merge_to_exr"
    window = MergeToExrWindow(ExrMergeService(), app_root, targets)
    window.show()
    return app.exec()
