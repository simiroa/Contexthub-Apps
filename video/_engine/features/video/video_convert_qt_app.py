from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    get_shell_palette,
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
    set_button_role,
    set_surface_role,
    set_transparent_surface,
)
from shared._engine.components.icon_button import build_icon_button
from contexthub.ui.qt.panels_export import ExportFoldoutPanel
from contexthub.ui.qt.panels_parameters import FixedParameterPanel
from contexthub.ui.qt.panels_preview import PreviewListPanel, VideoPreviewCard
from features.video.video_convert_service import VideoConvertService
from features.video.video_convert_state import VideoConvertState

try:
    from PySide6.QtCore import QObject, QSettings, Qt, QTimer, QUrl, Signal
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSlider,
        QSplitter,
        QStyle,
        QVBoxLayout,
        QWidget,
        QStackedLayout,
    )
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAS_MEDIA = True
except ImportError:  # pragma: no cover
    from PySide6.QtCore import QObject, QSettings, Qt, QTimer, Signal
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSlider,
        QSplitter,
        QStyle,
        QVBoxLayout,
        QWidget,
        QStackedLayout,
    )
    QMediaPlayer = None
    QAudioOutput = None
    QVideoWidget = None
    HAS_MEDIA = False


APP_ID = "video_convert"
APP_TITLE = qt_t("video_convert_gui.title", "Video Convert")
APP_SUBTITLE = qt_t(
    "video_convert_qt.subtitle",
    "Fast desktop shell for format, scale, and bitrate conversion with FFmpeg.",
)
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
VIDEO_PRESETS = {
    "Web MP4": {"format_hint": "MP4 (H.264 High)", "scale": "100%", "crf": 20},
    "Edit Proxy": {"format_hint": "MP4 (H.264 Low/Proxy)", "scale": "50%", "crf": 28},
    "Master ProRes 422": {"format_hint": "MOV (ProRes 422)", "scale": "100%", "crf": 18},
    "Archive Copy": {"format_hint": "MKV (Copy Stream)", "scale": "100%", "crf": 18},
    "Animated GIF": {"format_hint": "GIF (High Quality)", "scale": "50%", "crf": 18},
}


def _format_options(state: VideoConvertState) -> list[str]:
    options: list[str] = []
    if state.has_nvenc:
        options.append("MP4 (H.264 NVENC)")
    options.extend(
        [
            "MP4 (H.264 High)",
            "MP4 (H.264 Low/Proxy)",
            "MOV (ProRes 422)",
            "MOV (ProRes 4444)",
            "MOV (DNxHD)",
            "MKV (Copy Stream)",
            "GIF (High Quality)",
        ]
    )
    return options


def _resolve_output_dir(state: VideoConvertState) -> Path | None:
    if state.custom_output_dir:
        return state.custom_output_dir
    if not state.files:
        return None
    if state.save_to_folder:
        return state.files[0].parent / "Converted"
    return state.files[0].parent


def _output_summary(state: VideoConvertState) -> str:
    out_dir = _resolve_output_dir(state)
    if not state.files:
        return qt_t("video_convert_qt.output_unavailable", "Output path appears after videos are queued.")
    label = out_dir.name if out_dir else qt_t("video_convert_qt.output_unavailable", "Output path unavailable.")
    mode = qt_t("video_convert_qt.converted_folder", "Converted") if state.save_to_folder else qt_t("video_convert_qt.source_folder", "Source")
    if state.custom_output_dir:
        mode = qt_t("video_convert_qt.custom_folder", "Custom")
    return f"{label} / {mode}"


def _format_time(ms: int) -> str:
    total_seconds = max(0, int(ms / 1000))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _output_path_for(state: VideoConvertState, path: Path) -> str:
    suffix = path.suffix
    if "MP4" in state.output_format:
        suffix = ".mp4"
    elif "MOV" in state.output_format:
        suffix = ".mov"
    elif "MKV" in state.output_format:
        suffix = ".mkv"
    elif "GIF" in state.output_format:
        suffix = ".gif"
    out_dir = _resolve_output_dir(state)
    name = f"{path.stem}{suffix}" if (state.save_to_folder or state.custom_output_dir) else f"{path.stem}_conv{suffix}"
    if out_dir is None:
        return name
    return str(out_dir / name)


class ServiceBridge(QObject):
    updated = Signal(dict)

    def emit_update(self, **payload) -> None:
        self.updated.emit(payload)


class VideoConvertWindow(QMainWindow):
    def __init__(self, state: VideoConvertState, app_root: str | Path) -> None:
        super().__init__()
        self.state = state
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        self._selected_index = 0 if self.state.files else -1
        self._player_duration = 0
        self._volume_value = 60

        self.service_bridge = ServiceBridge()
        self.service_bridge.updated.connect(self._on_service_update)
        self.service = VideoConvertService(self.state, on_update=self.service_bridge.emit_update)

        self.media_player = None
        self.audio_output = None
        if HAS_MEDIA and QMediaPlayer is not None:
            self.media_player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.media_player.setAudioOutput(self.audio_output)
            self.audio_output.setVolume(self._volume_value / 100.0)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1080, 720)
        self.setMinimumSize(960, 640)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()

        self._restore_window_state()
        self._bind_actions()
        self._apply_state_to_controls()
        self._refresh_all()
        self._runtime_timer.start()

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
        self.header_surface.set_header_visibility(show_subtitle=False, show_asset_count=True, show_runtime_status=True)
        self.asset_count_badge = self.header_surface.asset_count_badge
        self.runtime_status_badge = self.header_surface.runtime_status_badge
        self.header_surface.open_webui_btn.hide()
        shell_layout.addWidget(self.header_surface)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        self.splitter.addWidget(self._build_left_panel())
        self.splitter.addWidget(self._build_right_panel())
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 5)
        self.splitter.setSizes([640, 440])

        shell_layout.addWidget(self.splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _build_left_panel(self) -> QWidget:
        card = QWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. Modular Video Preview
        self.preview_panel = VideoPreviewCard(
            title=qt_t("video_convert_qt.preview_title", "Preview"),
            empty_text=qt_t("video_convert_qt.preview_empty", "Select a video to preview."),
            no_selection_text=qt_t("video_convert_qt.no_selection", "No video selected")
        )
        
        # Video Surface integration
        if HAS_MEDIA and QVideoWidget is not None and self.media_player is not None:
            self.video_surface = QVideoWidget()
            self.media_player.setVideoOutput(self.video_surface)
            surface_layout = QVBoxLayout(self.preview_panel.video_container)
            surface_layout.setContentsMargins(0, 0, 0, 0)
            surface_layout.addWidget(self.video_surface)
        
        layout.addWidget(self.preview_panel, 3)

        # 2. Modular Queue List
        self.queue_panel = PreviewListPanel(
            preview_title="",
            list_title=qt_t("video_convert_qt.queue", "Queued Videos"),
            list_hint=qt_t("video_convert_qt.drop_here", "Drop video files here")
        )
        # We only use this component for the list functionality.
        self.queue_panel.preview_title_label.hide()
        self.queue_panel.preview_label.hide()
        self.queue_panel.preview_meta.hide()
        self.queue_panel.preview_btn.hide()
        layout.addWidget(self.queue_panel, 2)

        return card

    def _build_right_panel(self) -> QWidget:
        card = QWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. Modular Parameters
        self.param_panel = FixedParameterPanel(
            title=qt_t("video_convert_qt.parameters", "Parameters"),
            description=qt_t("video_convert_qt.description", "Choose a preset, tune format and scale, then convert the queued videos."),
            preset_label=qt_t("video_convert_qt.preset", "Preset")
        )
        self.preset_combo = self.param_panel.preset_combo
        self.preset_combo.addItems(list(VIDEO_PRESETS.keys()))

        # Format Combo
        self.format_combo = QComboBox()
        self.param_panel.add_field(qt_t("video_convert_gui.format_label", "Output Format"), self.format_combo)

        # Scale Combo
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["100%", "50%", "25%", "Custom Width"])
        self.param_panel.add_field(qt_t("video_convert_gui.scale_label", "Rescale"), self.scale_combo)

        # Custom Width (conditionally shown)
        self.custom_width_edit = QLineEdit()
        self.custom_width_edit.setPlaceholderText(qt_t("video_convert_gui.width_placeholder", "Custom Width (px)"))
        self.param_panel.add_field("", self.custom_width_edit) # Label-less row

        # CRF Slider
        self.crf_slider = QSlider(Qt.Horizontal)
        self.crf_slider.setRange(0, 51)
        self.param_panel.add_field(qt_t("video_convert_gui.quality_crf", "Quality (CRF)"), self.crf_slider)
        self.crf_label = self.param_panel.fields_layout.itemAt(self.param_panel.fields_layout.count()-1).widget().findChild(QLabel, "eyebrow")

        layout.addWidget(self.param_panel, 1)

        # 2. Modular Execution (Run) Section
        self.run_panel = ExportFoldoutPanel(
            title=qt_t("video_convert_qt.convert", "Convert")
        )
        # Hide standard fields that don't apply to this tool's specific flow
        self.run_panel.output_prefix_label.hide()
        self.run_panel.output_prefix_edit.hide()
        self.run_panel.export_session_checkbox.hide()
        self.run_panel.open_folder_checkbox.hide()
        self.run_panel.export_btn.hide()

        # Add Folder Toggle Buttons (Source vs Converted) into the grid layout
        folder_row = QHBoxLayout()
        self.source_btn = build_icon_button(qt_t("video_convert_qt.source_folder", "Source"), icon_name="folder", role="secondary")
        self.source_btn.setCheckable(True)
        
        self.converted_btn = build_icon_button(qt_t("video_convert_qt.converted_folder", "Converted"), icon_name="folder-check", role="secondary")
        self.converted_btn.setCheckable(True)
        
        folder_row.addWidget(self.source_btn)
        folder_row.addWidget(self.converted_btn)
        
        # We know ExportFoldoutPanel uses a QVBoxLayout (details_layout) containing a QGridLayout at index 0.
        # We can just insert our widgets at index 1 so they appear between the grid and the progress bar.
        self.run_panel.details_layout.insertLayout(1, folder_row)

        self.delete_original_check = QCheckBox(qt_t("video_convert_gui.delete_original", "Delete original"))
        self.run_panel.details_layout.insertWidget(2, self.delete_original_check)
        
        # Hide the progress bar and labels initially to reduce clutter, they can be shown during conversion
        self.run_panel.progress_bar.hide()
        self.run_panel.status_label.hide()
        self.run_panel.progress_label.hide()
        
        layout.addWidget(self.run_panel, 0)

        return card

    def _bind_actions(self) -> None:
        self.queue_panel.add_btn.clicked.connect(self._pick_inputs)
        self.queue_panel.remove_btn.clicked.connect(self._remove_selected_input)
        self.queue_panel.clear_btn.clicked.connect(self._clear_inputs)
        self.queue_panel.input_list.itemSelectionChanged.connect(self._sync_preview_from_selection)
        
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        self.scale_combo.currentTextChanged.connect(self._on_scale_changed)
        self.crf_slider.valueChanged.connect(self._on_crf_changed)
        self.custom_width_edit.textChanged.connect(self._on_custom_width_changed)

        self.run_panel.toggle_btn.clicked.connect(self._toggle_run_card)
        self.run_panel.browse_btn.clicked.connect(self._browse_output_dir)
        self.source_btn.clicked.connect(self._use_source_folder)
        self.converted_btn.clicked.connect(self._use_converted_folder)
        self.run_panel.run_btn.clicked.connect(self._start_conversion)
        self.run_panel.cancel_btn.clicked.connect(self._cancel_conversion)
        self.run_panel.reveal_btn.clicked.connect(self._open_output_folder)
        self.run_panel.output_dir_edit.textChanged.connect(self._on_output_dir_changed)
        self.delete_original_check.stateChanged.connect(self._on_delete_original_toggled)

        self.preview_panel.play_clicked.connect(self._play_media)
        self.preview_panel.pause_clicked.connect(self._pause_media)
        self.preview_panel.seek_requested.connect(self._seek_media)
        self.preview_panel.volume_changed.connect(self._on_volume_changed)
        self.preview_panel.mute_requested.connect(self._toggle_mute)

        if self.media_player is not None:
            self.media_player.positionChanged.connect(self._on_position_changed)
            self.media_player.durationChanged.connect(self._on_duration_changed)

    def _apply_state_to_controls(self) -> None:
        formats = _format_options(self.state)
        self.format_combo.clear()
        self.format_combo.addItems(formats)
        if self.state.output_format in formats:
            self.format_combo.setCurrentText(self.state.output_format)
        self.scale_combo.setCurrentText(self.state.scale)
        self.custom_width_edit.setText(self.state.custom_width)
        self.crf_slider.setValue(self.state.crf)
        self.run_panel.output_dir_edit.setText(str(self.state.custom_output_dir) if self.state.custom_output_dir else "")
        self.delete_original_check.setChecked(self.state.delete_original)
        self.preset_combo.setCurrentText("Web MP4")

    def _refresh_all(self) -> None:
        self._refresh_list()
        self._refresh_preview()
        self._refresh_status()
        self._refresh_option_states()

    def _refresh_list(self) -> None:
        current_path = self.state.files[self._selected_index] if 0 <= self._selected_index < len(self.state.files) else None
        self.queue_panel.input_list.clear()
        for path in self.state.files:
            output_info = _output_path_for(self.state, path)
            item = QListWidgetItem(path.name)
            item.setToolTip(f"{path}\n{output_info}")
            self.queue_panel.input_list.addItem(item)
        if current_path and current_path in self.state.files:
            self._selected_index = self.state.files.index(current_path)
        elif self.state.files:
            self._selected_index = 0
        else:
            self._selected_index = -1
        if self._selected_index >= 0:
            self.queue_panel.input_list.setCurrentRow(self._selected_index)
        self.asset_count_badge.setText(qt_t("comfyui.qt_shell.asset_count", "{count} inputs", count=len(self.state.files)))

    def _refresh_preview(self) -> None:
        path = self._current_path()
        if path is None:
            self.preview_panel.set_placeholder_mode(True, qt_t("video_convert_qt.preview_empty", "Select a video to preview."))
            self.preview_panel.set_metadata(qt_t("video_convert_qt.no_selection", "No video selected"), "0:00 / 0:00")
            self.preview_panel.slider.setRange(0, 0)
            return

        self.preview_panel.set_placeholder_mode(False)
        self.preview_panel.set_metadata(path.name, f"0:00 / {_format_time(self._player_duration)}")
        if self.media_player is not None and self.video_surface is not None:
            self.media_player.setSource(QUrl.fromLocalFile(str(path)))
        else:
            self.preview_panel.set_placeholder_mode(True, str(path))

    def _refresh_status(self) -> None:
        runtime_text = (
            qt_t("video_convert_qt.nvenc_ready", "NVENC ready")
            if self.state.has_nvenc
            else qt_t("video_convert_qt.cpu_encode", "CPU encode")
        )
        if not self.state.ffmpeg_path:
            runtime_text = qt_t("video_convert_qt.ffmpeg_missing", "FFmpeg not found")
        self.runtime_status_badge.setText(runtime_text)
        
        self.run_panel.set_status(self.state.status_text or qt_t("video_convert_gui.ready_to_convert", "Ready to convert."))
        if self.state.total_count > 0:
            self.run_panel.progress_label.setText(f"{self.state.completed_count}/{self.state.total_count} | {int(self.state.progress_value * 100)}%")
            self.run_panel.set_progress(int(self.state.progress_value * 100))
            self.run_panel.progress_bar.show()
            self.run_panel.status_label.show()
            self.run_panel.progress_label.show()
        else:
            self.run_panel.progress_label.setText("")
            self.run_panel.set_progress(0)
            self.run_panel.progress_bar.hide()
            self.run_panel.status_label.hide()
            self.run_panel.progress_label.hide()
        
        self.run_panel.run_btn.setDisabled(self.state.is_processing or not self.state.files or not self.state.ffmpeg_path)
        self.run_panel.cancel_btn.setDisabled(not self.state.is_processing)
        
        can_reveal = _resolve_output_dir(self.state) is not None
        self.run_panel.reveal_btn.setDisabled(not can_reveal)
        
        is_custom = self.state.custom_output_dir is not None
        self.source_btn.setChecked(not is_custom and not self.state.save_to_folder)
        self.converted_btn.setChecked(not is_custom and self.state.save_to_folder)

        # Initial summary
        self.run_panel.summary_label.setText(_output_summary(self.state))

    def _refresh_option_states(self) -> None:
        self.custom_width_edit.setVisible(self.scale_combo.currentText() == "Custom Width")
        is_quality_mode = "H.264" in self.state.output_format or "NVENC" in self.state.output_format
        self.crf_slider.setEnabled(is_quality_mode)
        self.crf_label.setText(f"{qt_t('video_convert_gui.quality_crf', 'Quality (CRF)')}: {self.state.crf}")

    def _current_path(self) -> Path | None:
        if 0 <= self._selected_index < len(self.state.files):
            return self.state.files[self._selected_index]
        return None

    def _on_service_update(self, payload: dict) -> None:
        self._refresh_all()
        if payload.get("finished"):
            success = payload.get("success", 0)
            total = payload.get("total", 0)
            errors = payload.get("errors") or []
            title = qt_t("video_convert_qt.completed", "Conversion Complete")
            message = f"Converted {success}/{total} files."
            if errors:
                title = qt_t("video_convert_qt.completed_with_errors", "Conversion Finished With Errors")
                message += "\n\n" + "\n".join(str(err) for err in errors[:5])
            QMessageBox.information(self, title, message)

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            APP_TITLE,
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm *.m4v);;All Files (*.*)",
        )
        if not files:
            return
        self.service.add_inputs(files)
        if self._selected_index < 0 and self.state.files:
            self._selected_index = 0
        self._refresh_all()

    def _remove_selected_input(self) -> None:
        self.service.remove_input_at(self.queue_panel.input_list.currentRow())
        self._refresh_all()

    def _clear_inputs(self) -> None:
        self.service.clear_inputs()
        self._refresh_all()

    def _sync_preview_from_selection(self) -> None:
        self._selected_index = self.queue_panel.input_list.currentRow()
        self._refresh_preview()

    def _on_preset_changed(self, name: str) -> None:
        preset = VIDEO_PRESETS.get(name)
        if not preset:
            return
        target = preset["format_hint"]
        if target == "MP4 (H.264 High)" and self.state.has_nvenc:
            target = "MP4 (H.264 NVENC)"
        self.state.output_format = target
        self.state.scale = str(preset["scale"])
        self.state.crf = int(preset["crf"])
        self.format_combo.setCurrentText(self.state.output_format)
        self.scale_combo.setCurrentText(self.state.scale)
        self.crf_slider.setValue(self.state.crf)
        self._refresh_all()

    def _on_format_changed(self, value: str) -> None:
        self.state.output_format = value
        if "High" in value:
            self.state.crf = 18
            self.crf_slider.setValue(self.state.crf)
        elif "Low" in value:
            self.state.crf = 28
            self.crf_slider.setValue(self.state.crf)
        self._refresh_all()

    def _on_scale_changed(self, value: str) -> None:
        self.state.scale = value
        self._refresh_all()

    def _on_crf_changed(self, value: int) -> None:
        self.state.crf = int(value)
        self._refresh_all()

    def _on_custom_width_changed(self, value: str) -> None:
        self.state.custom_width = value
        self._refresh_all()

    def _toggle_run_card(self) -> None:
        visible = not self.run_panel.details.isVisible()
        self.run_panel.set_expanded(visible)

    def _on_output_dir_changed(self, value: str) -> None:
        self.state.custom_output_dir = Path(value) if value.strip() else None
        if self.state.custom_output_dir:
            self.state.save_to_folder = False
        self._refresh_status()

    def _on_delete_original_toggled(self, checked: int) -> None:
        self.state.delete_original = bool(checked)

    def _browse_output_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, qt_t("video_convert_qt.choose_output", "Choose output folder"))
        if chosen:
            self.run_panel.output_dir_edit.setText(chosen)

    def _use_source_folder(self) -> None:
        self.state.custom_output_dir = None
        self.state.save_to_folder = False
        self.run_panel.output_dir_edit.blockSignals(True)
        self.run_panel.output_dir_edit.setText("")
        self.run_panel.output_dir_edit.blockSignals(False)
        self._refresh_all()

    def _use_converted_folder(self) -> None:
        if not self.state.files:
            return
        self.state.custom_output_dir = None
        self.state.save_to_folder = True
        self.run_panel.output_dir_edit.blockSignals(True)
        self.run_panel.output_dir_edit.setText("")
        self.run_panel.output_dir_edit.blockSignals(False)
        self._refresh_all()

    def _open_output_folder(self) -> None:
        self.service.reveal_output_dir()

    def _start_conversion(self) -> None:
        if self.state.files:
            self.service.start_conversion()
            self._refresh_status()

    def _cancel_conversion(self) -> None:
        self.service.cancel_conversion()
        self._refresh_status()

    def _play_media(self) -> None:
        if self.media_player is not None and self._current_path() is not None:
            self.media_player.play()

    def _pause_media(self) -> None:
        if self.media_player is not None:
            self.media_player.pause()

    def _seek_media(self, value: int) -> None:
        if self.media_player is not None:
            self.media_player.setPosition(value)

    def _on_volume_changed(self, value: int) -> None:
        self._volume_value = value
        if self.audio_output is not None:
            self.audio_output.setVolume(value / 100.0)
        self.preview_panel.volume_btn.setText("🔇" if value == 0 else "🔉" if value < 50 else "🔊")

    def _toggle_mute(self) -> None:
        if self.preview_panel.volume_slider.value() == 0:
            self.preview_panel.volume_slider.setValue(60 if self._volume_value == 0 else self._volume_value)
        else:
            self.preview_panel.volume_slider.setValue(0)

    def _on_position_changed(self, position: int) -> None:
        self.preview_panel.slider.blockSignals(True)
        self.preview_panel.slider.setValue(position)
        self.preview_panel.slider.blockSignals(False)
        self.preview_panel.time_label.setText(f"{_format_time(position)} / {_format_time(self._player_duration)}")

    def _on_duration_changed(self, duration: int) -> None:
        self._player_duration = duration
        self.preview_panel.slider.setRange(0, duration)
        self.preview_panel.time_label.setText(f"{_format_time(0)} / {_format_time(duration)}")

    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current == self._runtime_signature:
            return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self.setStyleSheet(build_shell_stylesheet())

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


def start_app(targets: list[Path] | None, app_root: str | Path) -> int:
    files = [path for path in (targets or []) if path.suffix.lower() in VIDEO_EXTS]
    state = VideoConvertState(files=files)
    app = QApplication.instance() or QApplication(sys.argv)
    window = VideoConvertWindow(state, app_root)
    window.show()
    return app.exec()
