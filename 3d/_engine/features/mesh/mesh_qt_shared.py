from __future__ import annotations

import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from contexthub.ui.qt.panels import ExportFoldoutPanel, FixedParameterPanel, PreviewListPanel
from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    refresh_runtime_preferences,
    runtime_settings_signature,
)
from utils.i18n import t

from .mesh_service import MeshService
from .mesh_state import MeshAppState

try:
    from PySide6.QtCore import QSettings, Qt, QTimer
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for 3D mesh Qt apps.") from exc


def _tr(key: str, fallback: str, **kwargs) -> str:
    value = t(key, default=fallback, **kwargs)
    return fallback if not value or value == key else value


@dataclass(frozen=True)
class MeshModeSpec:
    mode: str
    title: str
    subtitle: str
    primary_action: str
    template: str
    dependency_name: str
    preview_title: str
    list_title: str
    list_hint: str


MODE_SPECS: dict[str, MeshModeSpec] = {
    "convert": MeshModeSpec(
        mode="convert",
        title="Mesh Convert",
        subtitle="Batch-convert mesh files with a shared Qt shell and Blender-backed execution.",
        primary_action="Convert Meshes",
        template="full",
        dependency_name="Blender",
        preview_title="Selection Summary",
        list_title="Input Meshes",
        list_hint="Add FBX, OBJ, GLB, USD, STL, or PLY files to convert.",
    ),
    "cad": MeshModeSpec(
        mode="cad",
        title="CAD to OBJ",
        subtitle="Confirm CAD sources, check Mayo availability, and export OBJ from a compact Qt flow.",
        primary_action="Convert to OBJ",
        template="compact",
        dependency_name="Mayo",
        preview_title="Selection Summary",
        list_title="CAD Inputs",
        list_hint="Add STEP, IGES, BREP, STL, or OBJ files for Mayo conversion.",
    ),
}


ALLOWED_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "convert": (".fbx", ".obj", ".glb", ".gltf", ".usd", ".usdc", ".stl", ".ply", ".abc"),
    "cad": (".step", ".stp", ".iges", ".igs", ".brep", ".stl", ".obj"),
}


def allowed_extensions(mode: str) -> tuple[str, ...]:
    return ALLOWED_EXTENSIONS.get(mode, ALLOWED_EXTENSIONS["convert"])


def supports_path(mode: str, path: Path) -> tuple[bool, str]:
    if path.suffix.lower() not in allowed_extensions(mode):
        return False, "Blocked"
    return True, "Ready"


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def estimate_output_dir(mode: str, state: MeshAppState) -> Path | None:
    if not state.input_paths:
        return None
    first = state.input_paths[0]
    if mode in {"convert", "cad"} and state.convert_to_subfolder:
        return first.parent / "Converted_Mesh"
    return first.parent


def load_mesh_locales(engine_root: Path) -> None:
    try:
        loc_file = engine_root / "locales.json"
        if loc_file.exists():
            from utils.i18n import load_extra_strings

            load_extra_strings(loc_file)
    except Exception:
        pass


class MeshWindowBase(QMainWindow):
    def __init__(self, service: MeshService, app_root: Path, targets: list[str] | None, mode: str) -> None:
        super().__init__()
        self.service = service
        self.state = MeshAppState(mode=mode)
        self.app_root = Path(app_root)
        self.spec = MODE_SPECS[mode]
        self._settings = QSettings("Contexthub", f"3d_{mode}")
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        self._dependency_status: dict[str, str | bool | None] = {}

        self.setWindowTitle(self.spec.title)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1200, 860 if self.spec.template == "full" else 780)
        self.setMinimumSize(960, 680 if self.spec.template == "full" else 620)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self._bind_actions()
        self._restore_window_state()
        self._refresh_dependency_status()

        if targets:
            self._add_paths(Path(p) for p in targets)
        self._refresh_ui()
        if os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1":
            QTimer.singleShot(2500, self.close)
        self._runtime_timer.start()

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

        self.header_surface = HeaderSurface(self, self.spec.title, self.spec.subtitle, self.app_root)
        self.header_surface.open_webui_btn.hide()
        self.header_surface.set_header_visibility(
            show_subtitle=False,
            show_asset_count=(self.spec.mode == "convert"),
            show_runtime_status=True,
        )
        shell_layout.addWidget(self.header_surface)

        self.dependency_card = self._build_dependency_card()
        shell_layout.addWidget(self.dependency_card)

        if self.spec.template == "compact":
            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(m.section_gap)
            self.preview_list_panel = self._build_left_panel()
            self.preview_list_panel.preview_label.setMinimumHeight(120)
            content_layout.addWidget(self.preview_list_panel, 1)
            content_layout.addWidget(self._build_right_panel(), 0)
            shell_layout.addWidget(content, 1)
        else:
            self.splitter = QSplitter(Qt.Horizontal)
            self.splitter.setChildrenCollapsible(False)
            self.splitter.setHandleWidth(6)
            self.preview_list_panel = self._build_left_panel()
            self.splitter.addWidget(self.preview_list_panel)
            self.splitter.addWidget(self._build_right_panel())
            self.splitter.setStretchFactor(0, 3)
            self.splitter.setStretchFactor(1, 2)
            shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _build_dependency_card(self) -> QFrame:
        m = get_shell_metrics()
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(6)

        eyebrow = QLabel(_tr("common.warning", "Warning"))
        eyebrow.setObjectName("eyebrow")
        self.dependency_title = QLabel("")
        self.dependency_title.setObjectName("sectionTitle")
        self.dependency_detail = QLabel("")
        self.dependency_detail.setObjectName("summaryText")
        self.dependency_detail.setWordWrap(True)
        self.dependency_retry_btn = QLabel(_tr("common.ready", "Open the dependency in Manager settings, then reopen this app."))
        self.dependency_retry_btn.setObjectName("summaryText")
        self.dependency_retry_btn.setWordWrap(True)

        layout.addWidget(eyebrow)
        layout.addWidget(self.dependency_title)
        layout.addWidget(self.dependency_detail)
        layout.addWidget(self.dependency_retry_btn)
        return card

    def _build_left_panel(self) -> PreviewListPanel:
        panel = PreviewListPanel(
            preview_title=self.spec.preview_title,
            list_title=self.spec.list_title,
            list_hint=self.spec.list_hint,
        )
        panel.preview_btn.hide()
        panel.preview_label.setText("Add files to begin.")
        return panel

    def _build_right_panel(self) -> QFrame:
        m = get_shell_metrics()
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(max(8, m.section_gap - 2))

        self.param_panel = self.build_parameter_panel()
        layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportFoldoutPanel(self.spec.primary_action)
        self.export_panel.export_btn.hide()
        self.export_panel.export_session_checkbox.hide()
        self.export_panel.output_prefix_label.hide()
        self.export_panel.output_prefix_edit.hide()
        self.export_panel.output_dir_edit.setReadOnly(True)
        self.export_panel.toggle_btn.hide()
        self.export_panel.set_expanded(False)
        layout.addWidget(self.export_panel, 0)
        return card

    def build_parameter_panel(self) -> FixedParameterPanel:
        raise NotImplementedError

    def _bind_actions(self) -> None:
        self.preview_list_panel.add_requested.connect(self._pick_inputs)
        self.preview_list_panel.remove_requested.connect(self._remove_selected)
        self.preview_list_panel.clear_requested.connect(self._clear_inputs)
        self.preview_list_panel.selection_changed.connect(self._on_selection_changed)
        self.preview_list_panel.files_dropped.connect(self._on_files_dropped)
        self.export_panel.run_requested.connect(self._start_run)
        self.export_panel.reveal_requested.connect(self._reveal_output_dir)

    def _pick_inputs(self) -> None:
        extensions = " ".join(f"*{ext}" for ext in allowed_extensions(self.state.mode))
        files, _ = QFileDialog.getOpenFileNames(self, self.spec.title, "", f"Supported Files ({extensions})")
        if files:
            self._add_paths(Path(path) for path in files)

    def _on_files_dropped(self, paths: list[Path]) -> None:
        self._add_paths(paths)

    def _add_paths(self, paths: Iterable[Path]) -> None:
        known = {str(path.resolve()) for path in self.state.input_paths}
        for path in paths:
            if not path.exists():
                continue
            resolved = str(path.resolve())
            if resolved in known:
                continue
            if path.suffix.lower() not in allowed_extensions(self.state.mode):
                continue
            self.state.input_paths.append(path)
            known.add(resolved)
        if self.state.selected_index < 0 and self.state.input_paths:
            self.state.selected_index = 0
        self._refresh_ui()

    def _remove_selected(self) -> None:
        index = self.state.selected_index
        if index < 0 or index >= len(self.state.input_paths):
            return
        self.state.input_paths.pop(index)
        if not self.state.input_paths:
            self.state.selected_index = -1
        else:
            self.state.selected_index = min(index, len(self.state.input_paths) - 1)
        self._refresh_ui()

    def _clear_inputs(self) -> None:
        self.state.input_paths.clear()
        self.state.selected_index = -1
        self.state.last_output = None
        self._refresh_ui()

    def _on_selection_changed(self, *_args: object) -> None:
        self.state.selected_index = self.preview_list_panel.current_row()
        self._refresh_preview()
        self._refresh_output_summary()

    def _eligible_paths(self) -> list[Path]:
        return [path for path in self.state.input_paths if supports_path(self.state.mode, path)[0]]

    def _refresh_dependency_status(self) -> None:
        self._dependency_status = self.service.get_dependency_status(self.state.mode)

    def _refresh_dependency_card(self) -> None:
        available = bool(self._dependency_status.get("available"))
        self.dependency_title.setText(str(self._dependency_status.get("title") or ""))
        self.dependency_detail.setText(str(self._dependency_status.get("detail") or ""))
        self.dependency_card.setVisible(not available)
        self.header_surface.runtime_status_badge.setText("Ready" if available else f"{self.spec.dependency_name} Missing")

    def _refresh_preview(self) -> None:
        if not self.state.input_paths:
            self.preview_list_panel.set_preview("Add supported files to begin.", "")
            self.preview_list_panel.preview_meta.setText(self.spec.list_hint)
            return

        index = self.state.selected_index
        if index < 0 or index >= len(self.state.input_paths):
            index = 0
            self.state.selected_index = 0

        path = self.state.input_paths[index]
        supported, status = supports_path(self.state.mode, path)
        try:
            size_text = format_size(path.stat().st_size)
        except OSError:
            size_text = "-"
        meta = f"{path.parent}\n{size_text} • {status}"
        if not supported:
            meta = f"{meta}\nThis file is blocked for the current mode."
        self.preview_list_panel.preview_label.setText(path.name)
        self.preview_list_panel.preview_meta.setText(meta)

    def _refresh_output_summary(self) -> None:
        output_dir = estimate_output_dir(self.state.mode, self.state)
        self.export_panel.output_dir_edit.setText(str(output_dir) if output_dir else "")
        self.export_panel.output_prefix_edit.setText(self._default_output_prefix())
        self.export_panel.refresh_summary()

    def _default_output_prefix(self) -> str:
        if self.state.mode == "convert":
            return self.state.output_format.lower()
        if self.state.mode == "cad":
            return "obj"
        return ""

    def _refresh_input_list(self) -> None:
        items = [(path.name, str(path)) for path in self.state.input_paths]
        self.preview_list_panel.set_items(items)
        if 0 <= self.state.selected_index < self.preview_list_panel.input_list.count():
            self.preview_list_panel.input_list.setCurrentRow(self.state.selected_index)

    def _refresh_ui(self) -> None:
        self._refresh_dependency_status()
        self._sync_widgets_to_state()
        self._refresh_dependency_card()
        self._refresh_input_list()
        self._refresh_preview()
        self._refresh_output_summary()

        eligible = self._eligible_paths()
        count = len(self.state.input_paths)
        self.header_surface.set_asset_count(count)
        self.export_panel.run_button.setText("Processing..." if self.state.is_processing else self.spec.primary_action)
        self.export_panel.run_button.setEnabled(bool(eligible) and not self.state.is_processing and bool(self._dependency_status.get("available")))
        self.preview_list_panel.remove_btn.setEnabled(0 <= self.state.selected_index < count)
        self.preview_list_panel.clear_btn.setEnabled(count > 0)
        self.export_panel.set_progress(int(self.state.progress * 100))
        detail = self.state.error_message or (str(self.state.last_output.parent) if self.state.last_output else "")
        self.export_panel.set_status(self.state.status_text if not detail else f"{self.state.status_text} - {detail}")
        self.export_panel.progress_bar.setVisible(self.state.is_processing)
        self.update()

    def _sync_widgets_to_state(self) -> None:
        return None

    def _collect_options(self) -> dict[str, object]:
        return {}

    def _start_run(self) -> None:
        self._sync_widgets_to_state()
        run_paths = self._eligible_paths()
        if not run_paths or self.state.is_processing:
            return
        if not bool(self._dependency_status.get("available")):
            self._show_message("Dependency Missing", str(self._dependency_status.get("detail") or ""))
            return

        blocked_count = len(self.state.input_paths) - len(run_paths)
        self.state.is_processing = True
        self.state.progress = 0.0
        self.state.status_text = "Processing"
        self.state.error_message = f"{blocked_count} blocked" if blocked_count else None
        self.state.last_output = None
        self._refresh_ui()
        threading.Thread(target=self._run_task, args=(run_paths, blocked_count), daemon=True).start()

    def _run_task(self, run_paths: list[Path], blocked_count: int) -> None:
        def on_progress(current: int, total: int, filename: str) -> None:
            self.state.progress = current / total if total else 0.0
            self.state.status_text = f"{current}/{total}"
            self.state.error_message = filename
            QTimer.singleShot(0, self._refresh_ui)

        def on_complete(success: int, total: int, errors: list[str], last_path: Path | None) -> None:
            self.state.is_processing = False
            self.state.progress = 1.0 if total else 0.0
            self.state.last_output = last_path
            if blocked_count:
                errors = [f"{blocked_count} file(s) blocked by current mode."] + errors
            if errors:
                self.state.status_text = "Completed with issues"
                self.state.error_message = "; ".join(errors[:2])
            else:
                self.state.status_text = f"{success}/{total} completed"
                self.state.error_message = "Done"
            QTimer.singleShot(0, self._refresh_ui)
            QTimer.singleShot(0, lambda: self._show_completion(success, total, errors))

        try:
            self.service.execute_mesh_task(
                self.state.mode,
                run_paths,
                on_progress=on_progress,
                on_complete=on_complete,
                **self._collect_options(),
            )
        except Exception as exc:
            self.state.is_processing = False
            self.state.status_text = "Failed"
            self.state.error_message = str(exc)
            QTimer.singleShot(0, self._refresh_ui)
            QTimer.singleShot(0, lambda: self._show_message("Run Failed", str(exc)))

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
        output_dir = estimate_output_dir(self.state.mode, self.state)
        target = self.state.last_output.parent if self.state.last_output else output_dir
        if target and target.exists():
            os.startfile(str(target))

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

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())
        super().closeEvent(event)


class MeshConvertWindow(MeshWindowBase):
    def __init__(self, service: MeshService, app_root: Path, targets: list[str] | None) -> None:
        super().__init__(service, app_root, targets, "convert")

    def build_parameter_panel(self) -> FixedParameterPanel:
        panel = FixedParameterPanel(
            title="Conversion Settings",
            description="Choose the output format and output placement for all selected mesh files.",
            preset_label="Preset",
        )
        panel.preset_label.hide()
        panel.preset_combo.hide()

        self.format_combo = QComboBox()
        self.format_combo.addItems(["OBJ", "FBX", "GLB", "USD", "PLY", "STL"])
        self.format_combo.setCurrentText(self.state.output_format)

        self.subfolder_checkbox = QCheckBox("Save converted files to a Converted_Mesh subfolder")
        self.subfolder_checkbox.setChecked(self.state.convert_to_subfolder)

        panel.add_field("Output Format", self.format_combo)
        panel.add_field("Output Location", self.subfolder_checkbox)
        return panel

    def _sync_widgets_to_state(self) -> None:
        self.state.output_format = self.format_combo.currentText() or "OBJ"
        self.state.convert_to_subfolder = self.subfolder_checkbox.isChecked()

    def _collect_options(self) -> dict[str, object]:
        return {
            "format": self.state.output_format,
            "convert_to_subfolder": self.state.convert_to_subfolder,
        }


def launch_window(window_cls: type[QMainWindow], app_root: Path, targets: list[str] | None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = window_cls(MeshService(), app_root, targets or [])
    window.show()
    return app.exec()
