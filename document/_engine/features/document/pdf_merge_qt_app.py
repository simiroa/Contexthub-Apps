from __future__ import annotations

import sys
import threading
from pathlib import Path

from contexthub.ui.qt.panels import ExportFoldoutPanel
from contexthub.ui.qt.shell import (
    DropListWidget,
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    set_surface_role,
    qt_t,
)
from features.document.pdf_merge.service import PdfMergeService
from shared._engine.components.icon_button import build_icon_button

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QDragEnterEvent, QDropEvent
    from PySide6.QtWidgets import (
        QApplication,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for pdf_merge.") from exc

APP_TITLE = qt_t("pdf_merge.title", "PDF Merge")
APP_SUBTITLE = qt_t("pdf_merge.subtitle", "Merge multiple PDFs in your chosen order.")


class PdfMergeWindow(QMainWindow):
    def __init__(self, service: PdfMergeService, app_root: Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = app_root

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.resize(760, 860)
        self.setMinimumSize(620, 760)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._bind_actions()

        if targets:
            self.service.add_inputs(targets)
        self._sync_export_values()
        self._refresh_all()

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(m.section_gap)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
        self.header_surface.open_webui_btn.hide()
        self.header_surface.set_header_visibility(
            show_subtitle=False,
            show_asset_count=True,
            show_runtime_status=False,
        )
        shell_layout.addWidget(self.header_surface)

        self.list_card = QFrame()
        self.list_card.setObjectName("card")
        list_layout = QVBoxLayout(self.list_card)
        list_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        list_layout.setSpacing(10)

        title = QLabel(qt_t("pdf_merge.ordered_list", "Ordered PDF List"))
        title.setObjectName("sectionTitle")
        list_layout.addWidget(title)

        hint = QLabel(qt_t("pdf_merge.hint", "Adjust order with the Up and Down buttons before merging."))
        hint.setObjectName("summaryText")
        hint.setWordWrap(True)
        list_layout.addWidget(hint)

        self.file_list = DropListWidget()
        self.file_list.setMinimumHeight(320)
        list_layout.addWidget(self.file_list, 1)

        self.drop_hint = QLabel(qt_t("pdf_merge.drop_hint", "Drop PDF files here or use Add PDFs."))
        self.drop_hint.setObjectName("summaryText")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setWordWrap(True)
        list_layout.addWidget(self.drop_hint)

        action_row = QHBoxLayout()
        self.add_btn = build_icon_button(qt_t("pdf_merge.add", "Add PDFs"), icon_name="plus", role="secondary")
        self.remove_btn = build_icon_button(qt_t("pdf_merge.remove", "Remove"), icon_name="trash-2", role="secondary")
        self.up_btn = build_icon_button(qt_t("pdf_merge.up", "Move Up"), icon_name="chevron-up", role="secondary")
        self.down_btn = build_icon_button(qt_t("pdf_merge.down", "Move Down"), icon_name="chevron-down", role="secondary")
        self.clear_btn = build_icon_button(qt_t("pdf_merge.clear", "Clear"), icon_name="refresh-ccw", role="secondary")
        for button in (self.add_btn, self.remove_btn, self.up_btn, self.down_btn, self.clear_btn):
            action_row.addWidget(button)
        list_layout.addLayout(action_row)

        self.summary_card = QFrame()
        self.summary_card.setObjectName("subtlePanel")
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setSpacing(6)
        summary_title = QLabel(qt_t("pdf_merge.selection", "Selected File"))
        summary_title.setObjectName("eyebrow")
        self.selection_name = QLabel("-")
        self.selection_name.setObjectName("sectionTitle")
        self.selection_meta = QLabel("-")
        self.selection_meta.setObjectName("summaryText")
        self.selection_meta.setWordWrap(True)
        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.selection_name)
        summary_layout.addWidget(self.selection_meta)
        list_layout.addWidget(self.summary_card)

        shell_layout.addWidget(self.list_card, 1)

        self.export_panel = ExportFoldoutPanel(qt_t("pdf_merge.run", "Merge PDFs"))
        self.export_panel.export_btn.hide()
        self.export_panel.export_session_checkbox.hide()
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
        self.file_list.currentRowChanged.connect(self._on_row_changed)
        self.file_list.files_dropped.connect(self._on_files_dropped)
        self.export_panel.run_requested.connect(self._run_merge)
        if hasattr(self.export_panel, "reveal_requested"):
            self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        if hasattr(self.export_panel, "toggle_requested"):
            self.export_panel.toggle_requested.connect(self._toggle_export_details)

    def _sync_export_values(self) -> None:
        if hasattr(self.export_panel, "set_values"):
            opts = self.service.state.output_options
            self.export_panel.set_values(
                str(opts.output_dir),
                opts.file_prefix,
                opts.open_folder_after_run,
                opts.export_session_json,
            )
        if hasattr(self.export_panel, "set_expanded"):
            self.export_panel.set_expanded(False)

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, APP_TITLE, "", "PDF Files (*.pdf)")
        if files:
            self.service.add_inputs(files)
            self._refresh_all()

    def _on_files_dropped(self, paths: list[Path]) -> None:
        self.service.add_inputs([str(path) for path in paths])
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
        self._refresh_selection_summary()
        self._refresh_buttons()

    def _refresh_all(self) -> None:
        self._refresh_list()
        self._refresh_selection_summary()
        self._refresh_buttons()
        self._refresh_header()
        self._set_export_status(self.service.state.status_text, self.service.state.detail_text)

    def _refresh_list(self) -> None:
        self.file_list.blockSignals(True)
        self.file_list.clear()
        for index, path in enumerate(self.service.state.files, start=1):
            item = QListWidgetItem(f"{index}. {path.name}")
            item.setToolTip(str(path))
            self.file_list.addItem(item)
        if self.service.state.selected_index >= 0 and self.service.state.selected_index < self.file_list.count():
            self.file_list.setCurrentRow(self.service.state.selected_index)
        self.file_list.blockSignals(False)
        self.drop_hint.setText(
            qt_t("pdf_merge.drop_hint_empty", "Drop PDF files here or use Add PDFs.")
            if not self.service.state.files
            else qt_t("pdf_merge.drop_hint_more", "Drop more PDF files here to append them to the merge order.")
        )

    def _refresh_selection_summary(self) -> None:
        selected = self.service.selected_file()
        if selected is None:
            self.selection_name.setText("-")
            self.selection_meta.setText(qt_t("pdf_merge.no_selection", "No PDF selected."))
            return
        self.selection_name.setText(selected.name)
        order_text = f"Order {self.service.state.selected_index + 1} of {len(self.service.state.files)}"
        self.selection_meta.setText(f"{order_text}\n{selected.parent}\n{selected.stat().st_size / 1024:.1f} KB")

    def _refresh_buttons(self) -> None:
        count = len(self.service.state.files)
        index = self.service.state.selected_index
        has_selection = 0 <= index < count
        self.remove_btn.setEnabled(has_selection)
        self.clear_btn.setEnabled(count > 0)
        self.up_btn.setEnabled(has_selection and index > 0)
        self.down_btn.setEnabled(has_selection and index < count - 1)
        self._set_run_enabled(count >= 2 and not self.service.state.is_processing)

    def _refresh_header(self) -> None:
        self.header_surface.set_asset_count(len(self.service.state.files))

    def _toggle_export_details(self) -> None:
        if hasattr(self.export_panel, "details") and hasattr(self.export_panel, "set_expanded"):
            self.export_panel.set_expanded(not self.export_panel.details.isVisible())

    def _reveal_output_dir(self) -> None:
        self._sync_output_options_from_panel()
        self.service.reveal_output_dir()

    def _sync_output_options_from_panel(self) -> None:
        panel = self.export_panel
        self.service.update_output_options(
            panel.output_dir_edit.text() if hasattr(panel, "output_dir_edit") else str(self.service.state.output_options.output_dir),
            panel.output_prefix_edit.text() if hasattr(panel, "output_prefix_edit") else self.service.state.output_options.file_prefix,
            panel.open_folder_checkbox.isChecked() if hasattr(panel, "open_folder_checkbox") else True,
            panel.export_session_checkbox.isChecked() if hasattr(panel, "export_session_checkbox") else False,
        )
        if hasattr(panel, "refresh_summary"):
            panel.refresh_summary()

    def _run_merge(self) -> None:
        self._sync_output_options_from_panel()
        self._set_run_enabled(False)
        self._set_export_progress(0)
        self._set_export_status("Merging PDFs...", "")

        def _worker() -> None:
            try:
                output = self.service.run_merge(on_progress=self._on_merge_progress)
            except Exception as exc:
                QTimer.singleShot(0, lambda: self._on_merge_failed(str(exc)))
                return
            QTimer.singleShot(0, lambda: self._on_merge_complete(output))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_merge_progress(self, current: int, total: int, name: str) -> None:
        progress = int((current / total) * 100) if total else 0
        QTimer.singleShot(0, lambda: self._set_export_progress(progress))
        QTimer.singleShot(0, lambda: self._set_export_status(f"Merging {current}/{total}" if total else "Merging", name))

    def _on_merge_complete(self, output: Path) -> None:
        self._set_export_progress(100)
        self._set_export_status("Merge complete", output.name)
        self._refresh_all()
        if self.service.state.output_options.open_folder_after_run:
            self.service.reveal_output_dir()

    def _on_merge_failed(self, message: str) -> None:
        self.service.state.error = message
        self._set_export_status("Merge failed", message)
        self._set_run_enabled(True)
        self._refresh_header()

    def _set_export_status(self, status: str, detail: str) -> None:
        if hasattr(self.export_panel, "set_status"):
            self.export_panel.set_status(status if not detail else f"{status} - {detail}")
            return
        label = getattr(self.export_panel, "status_label", None)
        if label is not None:
            label.setText(status if not detail else f"{status} - {detail}")

    def _set_export_progress(self, value: int) -> None:
        if hasattr(self.export_panel, "set_progress"):
            self.export_panel.set_progress(value)
            return
        bar = getattr(self.export_panel, "progress_bar", None)
        if bar is not None:
            bar.setVisible(True)
            bar.setValue(value)

    def _set_run_enabled(self, enabled: bool) -> None:
        button = getattr(self.export_panel, "run_button", None) or getattr(self.export_panel, "run_btn", None)
        if button is not None:
            button.setEnabled(enabled)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        paths = self._extract_pdf_paths(event)
        if paths:
            event.acceptProposedAction()
            self._set_drop_highlight(True)
            return
        super().dragEnterEvent(event)

    def dragLeaveEvent(self, event) -> None:
        self._set_drop_highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = self._extract_pdf_paths(event)
        self._set_drop_highlight(False)
        if paths:
            self.service.add_inputs([str(path) for path in paths])
            self._refresh_all()
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _extract_pdf_paths(self, event) -> list[Path]:
        if not event.mimeData().hasUrls():
            return []
        paths: list[Path] = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() == ".pdf":
                paths.append(path)
        return paths

    def _set_drop_highlight(self, active: bool) -> None:
        if active:
            set_surface_role(self.list_card, "card", "accent")
            self.drop_hint.setText("Drop PDF files to append them to the merge order.")
        else:
            set_surface_role(self.list_card, "card", "default")
            self.drop_hint.setText(
                qt_t("pdf_merge.drop_hint_empty", "Drop PDF files here or use Add PDFs.")
                if not self.service.state.files
                else qt_t("pdf_merge.drop_hint_more", "Drop more PDF files here to append them to the merge order.")
            )


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app_root = Path(__file__).resolve().parents[3] / "pdf_merge"
    window = PdfMergeWindow(PdfMergeService(), app_root, targets)
    window.show()
    return app.exec()
