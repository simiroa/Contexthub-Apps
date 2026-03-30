from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from contexthub.ui.qt.panels import ExportFoldoutPanel, FixedParameterPanel
from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    refresh_runtime_preferences,
    runtime_settings_signature,
)

from .auto_lod_logic import (
    AutoLodSpec,
    build_expected_output_paths,
    collect_run_options,
    default_output_prefix,
    estimate_output_dir,
    safe_float,
    safe_int,
    supports_path,
)
from .auto_lod_preview_widget import AutoLodPreviewCard, SUPPORTED_PREVIEW_SUFFIXES
from .auto_lod_service import AutoLodService
from .auto_lod_state import AutoLodState

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, Signal
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for Auto LOD.") from exc


class AutoLodWindow(QMainWindow):
    progress_reported = Signal(int, int, str)
    task_completed = Signal(int, int, object, object)
    task_failed = Signal(str)

    def __init__(self, service: AutoLodService, app_root: Path, targets: list[str] | None) -> None:
        super().__init__()
        self.service = service
        self.state = AutoLodState()
        self.spec = AutoLodSpec()
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", "3d_lod")
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        self._dependency_status: dict[str, str | bool | None] = {}
        self.setWindowTitle(self.spec.title)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1320, 900)
        self.setMinimumSize(1120, 760)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self._bind_actions()
        self._restore_window_state()
        self._refresh_dependency_status()

        if targets:
            self._set_input_from_paths(Path(p) for p in targets)
        self._refresh_ui()
        if os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1":
            QTimer.singleShot(2500, self.close)
        self._runtime_timer.start()

    def _build_ui(self) -> None:
        metrics = get_shell_metrics()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(metrics.shell_margin - 2, metrics.shell_margin - 2, metrics.shell_margin - 2, metrics.shell_margin - 2)
        root.setSpacing(metrics.section_gap)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(metrics.shell_margin, metrics.shell_margin, metrics.shell_margin, metrics.shell_margin)
        shell_layout.setSpacing(metrics.section_gap)

        self.header_surface = HeaderSurface(self, self.spec.title, self.spec.subtitle, self.app_root)
        self.header_surface.open_webui_btn.hide()
        self.header_surface.set_header_visibility(
            show_subtitle=False,
            show_asset_count=False,
            show_runtime_status=True,
        )
        shell_layout.addWidget(self.header_surface)

        self.dependency_card = self._build_dependency_card()
        shell_layout.addWidget(self.dependency_card)

        body = QHBoxLayout()
        body.setSpacing(metrics.section_gap)
        body.addWidget(self._build_left_column(), 5)
        body.addWidget(self._build_right_column(), 2)
        shell_layout.addLayout(body, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _build_dependency_card(self) -> QFrame:
        metrics = get_shell_metrics()
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(metrics.panel_padding, metrics.panel_padding, metrics.panel_padding, metrics.panel_padding)
        layout.setSpacing(6)

        eyebrow = QLabel("Warning")
        eyebrow.setObjectName("eyebrow")
        self.dependency_title = QLabel("")
        self.dependency_title.setObjectName("sectionTitle")
        self.dependency_detail = QLabel("")
        self.dependency_detail.setObjectName("summaryText")
        self.dependency_detail.setWordWrap(True)
        self.dependency_retry_label = QLabel("Auto LOD uses the local simplification flow. Reopen the app if runtime settings changed.")
        self.dependency_retry_label.setObjectName("summaryText")
        self.dependency_retry_label.setWordWrap(True)

        layout.addWidget(eyebrow)
        layout.addWidget(self.dependency_title)
        layout.addWidget(self.dependency_detail)
        layout.addWidget(self.dependency_retry_label)
        return card

    def _build_left_column(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(get_shell_metrics().section_gap)

        self.preview_card = AutoLodPreviewCard()
        layout.addWidget(self.preview_card, 1)
        return panel

    def _build_right_column(self) -> QFrame:
        metrics = get_shell_metrics()
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(metrics.panel_padding, metrics.panel_padding, metrics.panel_padding, metrics.panel_padding)
        layout.setSpacing(max(8, metrics.section_gap - 2))

        self.param_panel = FixedParameterPanel(
            title="LOD Settings",
            description="Set the number of generated levels and the reduction step for each level.",
            preset_label="Preset",
        )
        self.param_panel.preset_label.hide()
        self.param_panel.preset_combo.hide()

        self.lod_count_combo = QComboBox()
        self.lod_count_combo.addItems(["1", "2", "3", "4", "5"])
        self.lod_count_combo.setCurrentText(str(self.state.lod_count))

        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(["0.25", "0.35", "0.50", "0.65", "0.75"])
        self.ratio_combo.setCurrentText(f"{self.state.lod_ratio:.2f}")

        self.preserve_uv_checkbox = QCheckBox("Preserve UV seams")
        self.preserve_uv_checkbox.setChecked(self.state.preserve_uv)
        self.preserve_normal_checkbox = QCheckBox("Preserve normals")
        self.preserve_normal_checkbox.setChecked(self.state.preserve_normal)
        self.preserve_boundary_checkbox = QCheckBox("Preserve boundaries")
        self.preserve_boundary_checkbox.setChecked(self.state.preserve_boundary)

        preserve_group = QWidget()
        preserve_layout = QVBoxLayout(preserve_group)
        preserve_layout.setContentsMargins(0, 0, 0, 0)
        preserve_layout.setSpacing(6)
        preserve_layout.addWidget(self.preserve_uv_checkbox)
        preserve_layout.addWidget(self.preserve_normal_checkbox)
        preserve_layout.addWidget(self.preserve_boundary_checkbox)

        self.param_panel.add_field("LOD Count", self.lod_count_combo)
        self.param_panel.add_field("Reduction Ratio", self.ratio_combo)
        self.param_panel.add_field("Preservation", preserve_group)
        layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportFoldoutPanel(self.spec.primary_action)
        self.export_panel.export_btn.hide()
        self.export_panel.export_session_checkbox.hide()
        self.export_panel.output_prefix_label.hide()
        self.export_panel.output_prefix_edit.hide()
        self.export_panel.output_dir_edit.setReadOnly(True)
        self.export_panel.toggle_btn.hide()
        self.export_panel.set_expanded(False)
        self.export_panel.progress_bar.setTextVisible(False)
        self.export_panel.progress_bar.setValue(0)
        layout.addWidget(self.export_panel, 0)
        return card

    def _bind_actions(self) -> None:
        self.progress_reported.connect(self._handle_progress_report)
        self.task_completed.connect(self._handle_task_complete)
        self.task_failed.connect(self._handle_task_failed)
        self.preview_card.file_dropped.connect(self._replace_input_from_drop)
        self.preview_card.mode_combo.currentIndexChanged.connect(self._on_view_mode_changed)
        self.preview_card.lod_combo.currentIndexChanged.connect(self._on_lod_index_changed)
        self.export_panel.run_requested.connect(self._start_run)
        self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        self.lod_count_combo.currentIndexChanged.connect(lambda _idx: self._refresh_ui())
        self.ratio_combo.currentIndexChanged.connect(lambda _idx: self._refresh_ui())
        self.preserve_uv_checkbox.toggled.connect(lambda _checked: self._refresh_ui())
        self.preserve_normal_checkbox.toggled.connect(lambda _checked: self._refresh_ui())
        self.preserve_boundary_checkbox.toggled.connect(lambda _checked: self._refresh_ui())

    def _replace_input_from_drop(self, path_obj: object) -> None:
        self._set_input_path(Path(path_obj))
        self._refresh_ui()

    def _set_input_from_paths(self, paths) -> None:
        for path in paths:
            self._set_input_path(path)
            if self.state.input_path is not None:
                return

    def _set_input_path(self, path: Path) -> None:
        if not path.exists():
            return
        if not supports_path(path)[0]:
            return
        self.state.input_path = path
        self.state.generated_paths = None
        self.state.selected_view = "source"
        self.state.selected_lod_index = 0

    def _refresh_dependency_status(self) -> None:
        self._dependency_status = self.service.get_dependency_status()

    def _refresh_dependency_card(self) -> None:
        available = bool(self._dependency_status.get("available"))
        self.dependency_title.setText(str(self._dependency_status.get("title") or ""))
        self.dependency_detail.setText(str(self._dependency_status.get("detail") or ""))
        self.dependency_card.setVisible(not available)
        self.header_surface.runtime_status_badge.setText("Ready" if available else f"{self.spec.dependency_name} Missing")

    def _sync_widgets_to_state(self) -> None:
        self.state.lod_count = safe_int(self.lod_count_combo.currentText(), self.state.lod_count)
        self.state.lod_ratio = safe_float(self.ratio_combo.currentText(), self.state.lod_ratio)
        self.state.preserve_uv = self.preserve_uv_checkbox.isChecked()
        self.state.preserve_normal = self.preserve_normal_checkbox.isChecked()
        self.state.preserve_boundary = self.preserve_boundary_checkbox.isChecked()

    def _existing_generated_paths(self) -> list[Path]:
        return [path for path in (self.state.generated_paths or []) if path.exists()]

    def _view_modes(self) -> list[tuple[str, str]]:
        modes = [("source", "Source")]
        if self._existing_generated_paths():
            modes.append(("generated", "Generated"))
        return modes

    def _lod_labels(self) -> list[str]:
        labels = []
        for index, _path in enumerate(self._existing_generated_paths(), start=1):
            labels.append(f"LOD {index}")
        return labels

    def _selected_preview_path(self) -> Path | None:
        if self.state.selected_view == "generated":
            generated = self._existing_generated_paths()
            if generated:
                index = max(0, min(self.state.selected_lod_index, len(generated) - 1))
                return generated[index]
        return self.state.input_path

    def _preview_status(self, path: Path | None) -> str:
        if path is None:
            return f"Drop one supported mesh here. Preview rendering is available for {', '.join(ext.upper().lstrip('.') for ext in sorted(SUPPORTED_PREVIEW_SUFFIXES))}."
        if not path.exists():
            return "Generated preview will appear here after a real output file exists."
        if path.suffix.lower() not in SUPPORTED_PREVIEW_SUFFIXES:
            return f"{path.suffix.lower()} is supported for processing but preview rendering is enabled for OBJ, STL, and PLY."
        if self.state.selected_view == "generated":
            return f"Previewing generated LOD {self.state.selected_lod_index + 1}: {path.name}"
        return f"Previewing source mesh: {path.name}"

    def _refresh_preview(self) -> None:
        modes = self._view_modes()
        if self.state.selected_view not in {value for value, _label in modes}:
            self.state.selected_view = "source"
        self.preview_card.set_view_modes(modes, self.state.selected_view)
        lod_labels = self._lod_labels() if self.state.selected_view == "generated" else []
        if not lod_labels:
            self.state.selected_lod_index = 0
        self.preview_card.set_lod_choices(lod_labels, self.state.selected_lod_index)
        self.preview_card.set_preview_path(self._selected_preview_path(), self._preview_status(self._selected_preview_path()))

    def _refresh_output_summary(self) -> None:
        output_dir = estimate_output_dir(self.state)
        self.export_panel.output_dir_edit.setText(str(output_dir) if output_dir else "")
        self.export_panel.output_prefix_edit.setText(default_output_prefix())
        if output_dir:
            summary = f"Output folder: {output_dir.name}"
            self.export_panel.summary_label.setText(summary)
            self.export_panel.summary_label.setToolTip(str(output_dir))
            self.export_panel.output_dir_edit.setToolTip(str(output_dir))
        else:
            self.export_panel.summary_label.setText("Output folder will appear after you load a mesh.")
            self.export_panel.summary_label.setToolTip("")
            self.export_panel.output_dir_edit.setToolTip("")

    def _refresh_ui(self) -> None:
        self._refresh_dependency_status()
        self._sync_widgets_to_state()
        if self.state.input_path is not None and not self.state.is_processing and not self._existing_generated_paths():
            self.state.generated_paths = build_expected_output_paths(self.state)
        self._refresh_dependency_card()
        self._refresh_output_summary()
        self._refresh_preview()

        has_input = self.state.input_path is not None
        self.export_panel.run_button.setText("Processing..." if self.state.is_processing else self.spec.primary_action)
        self.export_panel.run_button.setEnabled(has_input and not self.state.is_processing and bool(self._dependency_status.get("available")))
        self.export_panel.set_progress(int(self.state.progress * 100))
        detail = self.state.error_message or self._status_detail_text()
        self.export_panel.set_status(self.state.status_text if not detail else f"{self.state.status_text} - {detail}")
        self.update()

    def _status_detail_text(self) -> str:
        output_dir = estimate_output_dir(self.state)
        if not output_dir:
            return ""
        return output_dir.name

    def _on_view_mode_changed(self, _index: int) -> None:
        self.state.selected_view = str(self.preview_card.mode_combo.currentData() or "source")
        self._refresh_preview()

    def _on_lod_index_changed(self, index: int) -> None:
        self.state.selected_lod_index = max(0, index)
        if self.state.selected_view == "generated":
            self._refresh_preview()

    def _start_run(self) -> None:
        self._sync_widgets_to_state()
        if self.state.input_path is None or self.state.is_processing:
            return
        if not bool(self._dependency_status.get("available")):
            self._show_message("Dependency Missing", str(self._dependency_status.get("detail") or ""))
            return

        self.state.is_processing = True
        self.state.progress = 0.0
        self.state.status_text = "Processing"
        self.state.error_message = None
        self.state.generated_paths = []
        self.state.selected_view = "source"
        self.state.selected_lod_index = 0
        self._refresh_ui()
        threading.Thread(target=self._run_task, args=([self.state.input_path],), daemon=True).start()

    def _run_task(self, run_paths: list[Path]) -> None:
        def on_progress(current: int, total: int, filename: str) -> None:
            self.progress_reported.emit(current, total, filename)

        def on_complete(success: int, total: int, errors: list[str], result_paths: list[Path]) -> None:
            self.task_completed.emit(success, total, errors, result_paths)

        try:
            self.service.execute_task(
                run_paths,
                on_progress=on_progress,
                on_complete=on_complete,
                **collect_run_options(self.state),
            )
        except Exception as exc:
            self.task_failed.emit(str(exc))

    def _handle_progress_report(self, current: int, total: int, filename: str) -> None:
        self.state.progress = current / total if total else 0.0
        self.state.status_text = f"{current}/{total}"
        self.state.error_message = filename
        self._refresh_ui()

    def _handle_task_complete(self, success: int, total: int, errors_obj: object, result_paths_obj: object) -> None:
        errors = list(errors_obj) if isinstance(errors_obj, list) else []
        result_paths = list(result_paths_obj) if isinstance(result_paths_obj, list) else []
        self.state.is_processing = False
        self.state.progress = 1.0 if total else 0.0
        self.state.generated_paths = result_paths
        existing = self._existing_generated_paths()
        if existing:
            self.state.selected_view = "generated"
            self.state.selected_lod_index = 0
        if errors:
            self.state.status_text = "Completed with issues"
            self.state.error_message = "; ".join(errors[:2])
        else:
            self.state.status_text = f"{success}/{total} completed"
            self.state.error_message = "Done"
        self._refresh_ui()
        self._show_completion(success, total, errors)

    def _handle_task_failed(self, message: str) -> None:
        self.state.is_processing = False
        self.state.status_text = "Failed"
        self.state.error_message = message
        self._refresh_ui()
        self._show_message("Run Failed", message)

    def _show_completion(self, success: int, total: int, errors: list[str]) -> None:
        if errors:
            self._show_message("Completed with issues", f"{success}/{total} succeeded.\n\n" + "\n".join(errors[:3]))
        else:
            self._show_message("Completed", f"{success}/{total} completed successfully.")

    def _show_message(self, title: str, message: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        box.exec()

    def _reveal_output_dir(self) -> None:
        output_dir = estimate_output_dir(self.state)
        if output_dir and output_dir.exists():
            os.startfile(str(output_dir))

    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current == self._runtime_signature:
            return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self.setStyleSheet(build_shell_stylesheet())
        self._refresh_ui()

    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        if self._settings.value("is_maximized", False, bool):
            self.showMaximized()
            return
        self._ensure_visible_on_screen()

    def _ensure_visible_on_screen(self) -> None:
        frame = self.frameGeometry()
        screens = QGuiApplication.screens()
        if not screens:
            return
        if any(screen.availableGeometry().intersects(frame) for screen in screens):
            return
        target = QGuiApplication.primaryScreen().availableGeometry()
        width = min(max(self.width(), 1120), target.width() - 40)
        height = min(max(self.height(), 760), target.height() - 40)
        self.resize(width, height)
        self.move(target.center().x() - width // 2, target.center().y() - height // 2)

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())
        super().closeEvent(event)


def launch_auto_lod_window(app_root: Path, targets: list[str] | None) -> int:
    QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
    app = QApplication.instance() or QApplication(sys.argv)
    window = AutoLodWindow(AutoLodService(), app_root, targets or [])
    window.show()
    return app.exec()
