from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.shell import (
    ElidedLabel,
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    qt_t,
    set_badge_role,
    set_button_role,
    set_surface_role,
)
from features.audio.audio_toolbox_panels import build_option_panels
from features.audio.audio_toolbox_run_widget import AudioRunWidget
from features.audio.audio_toolbox_service import AudioToolboxService
from features.audio.audio_toolbox_state import AudioToolboxState
from features.audio.audio_toolbox_tasks import (
    TASK_COMPRESS_AUDIO,
    TASK_CONVERT_AUDIO,
    TASK_ENHANCE_AUDIO,
    TASK_EXTRACT_BGM,
    TASK_EXTRACT_VOICE,
    TASK_LABELS,
    TASK_NORMALIZE_VOLUME,
    TASK_STACK_INDEX,
    export_formats_for_task,
)

try:
    from PySide6.QtCore import QObject, Qt, Signal
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSlider,
        QVBoxLayout,
        QWidget,
    )
    from PySide6.QtCore import QUrl
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for audio_toolbox.") from exc


APP_ID = "audio_toolbox"
APP_TITLE = qt_t("audio_toolbox.title", "Audio Toolbox")
APP_SUBTITLE = qt_t(
    "audio_toolbox.subtitle",
    "Unified audio processing shell for separation, normalization, and conversion.",
)
FILTER_TEXT = "Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a *.aac *.wma);;All Files (*.*)"


class ServiceBridge(QObject):
    updated = Signal(dict)

    def emit_update(self, **payload) -> None:
        self.updated.emit(payload)


class AudioToolboxWindow(QMainWindow):
    def __init__(self, state: AudioToolboxState, app_root: str | Path) -> None:
        super().__init__()
        self.state = state
        self.app_root = Path(app_root)
        self.bridge = ServiceBridge()
        self.bridge.updated.connect(self._on_service_update)
        self.service = AudioToolboxService(self.state, on_update=self.bridge.emit_update)
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.8)
        self._duration_ms = 0

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1180, 840)
        self.setMinimumSize(980, 760)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self._bind_actions()
        self._sync_controls_from_state()
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
        shell_layout.addWidget(self.header_surface)
        set_badge_role(self.header_surface.asset_count_badge, "status", "accent")
        set_badge_role(self.header_surface.runtime_status_badge, "status", "muted")

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(m.section_gap)
        body.addWidget(self._build_left_panel(), 10)
        body.addWidget(self._build_right_panel(), 13)
        shell_layout.addLayout(body, 1)

        self.size_grip = attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

        field_style = """
            QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
                min-height: 38px;
                border-radius: 12px;
            }
        """
        self.task_combo.setStyleSheet(field_style)
        self.model_combo.setStyleSheet(field_style)
        self.stem_mode_combo.setStyleSheet(field_style)
        self.convert_quality_combo.setStyleSheet(field_style)
        self.run_foldout.export_format_combo.setStyleSheet(
            "QComboBox#compactField { min-height: 34px; border-radius: 12px; padding: 4px 10px; }"
        )

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        set_surface_role(panel, "card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        player_card = QFrame()
        set_surface_role(player_card, "subtle")
        player_card.setMaximumHeight(176)
        player_layout = QVBoxLayout(player_card)
        player_layout.setContentsMargins(12, 12, 12, 12)
        player_layout.setSpacing(10)
        player_title = QLabel("Selected Audio")
        player_title.setObjectName("eyebrow")
        self.now_playing = ElidedLabel("No selection")
        self.now_playing.setObjectName("title")
        self.audio_path = ElidedLabel("")
        self.audio_path.setObjectName("summaryText")
        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(8)
        name_row.addWidget(self.now_playing, 1)
        name_row.addWidget(player_title, 0, Qt.AlignRight | Qt.AlignVCenter)
        player_layout.addLayout(name_row)
        player_layout.addWidget(self.audio_path)

        transport = QHBoxLayout()
        transport.setContentsMargins(0, 0, 0, 0)
        transport.setSpacing(6)
        self.play_btn = QPushButton("Play")
        self.pause_btn = QPushButton("Pause")
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setObjectName("muted")
        set_button_role(self.play_btn, "pill")
        set_button_role(self.pause_btn, "pill")
        transport.addWidget(self.play_btn, 0)
        transport.addWidget(self.pause_btn, 0)
        transport.addWidget(self.time_label, 1)
        player_layout.addLayout(transport)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        player_layout.addWidget(self.position_slider)
        layout.addWidget(player_card, 0)

        queue_card = QFrame()
        set_surface_role(queue_card, "subtle")
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(12, 12, 12, 12)
        queue_layout.setSpacing(10)
        title = QLabel("Queued Audio")
        title.setObjectName("sectionTitle")
        queue_layout.addWidget(title)

        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(200)
        queue_layout.addWidget(self.file_list, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(6)
        self.add_btn = QPushButton("Add")
        self.remove_btn = QPushButton("Remove")
        self.clear_btn = QPushButton("Clear")
        self.pick_output_btn = QPushButton("Output Folder")
        for button in (self.add_btn, self.remove_btn, self.clear_btn, self.pick_output_btn):
            set_button_role(button, "secondary")
            action_row.addWidget(button)
        queue_layout.addLayout(action_row)
        layout.addWidget(queue_card, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        set_surface_role(panel, "card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        head = QLabel("Task Settings")
        head.setObjectName("sectionTitle")
        layout.addWidget(head)

        self.task_combo = QComboBox()
        for task_id, label in TASK_LABELS.items():
            self.task_combo.addItem(label, task_id)
        layout.addWidget(self.task_combo)

        self.task_card = QFrame()
        set_surface_role(self.task_card, "subtle")
        task_card_layout = QVBoxLayout(self.task_card)
        task_card_layout.setContentsMargins(12, 12, 12, 12)
        task_card_layout.setSpacing(10)

        task_card_title = QLabel("Options")
        task_card_title.setObjectName("eyebrow")
        task_card_layout.addWidget(task_card_title)

        panels = build_option_panels()
        self.task_stack = panels.task_stack
        self.model_combo = panels.model_combo
        self.stem_mode_combo = panels.stem_mode_combo
        self.chunk_spin = panels.chunk_spin
        self.loudness_spin = panels.loudness_spin
        self.true_peak_spin = panels.true_peak_spin
        self.lra_spin = panels.lra_spin
        self.convert_quality_combo = panels.convert_quality_combo
        self.copy_metadata_check = panels.copy_metadata_check
        self.delete_original_check = panels.delete_original_check
        self.compress_level_combo = panels.compress_level_combo
        self.enhance_profile_combo = panels.enhance_profile_combo
        task_card_layout.addWidget(self.task_stack, 1)
        layout.addWidget(self.task_card, 3)

        self.run_foldout = AudioRunWidget()
        layout.addWidget(self.run_foldout, 0)
        return panel

    def _bind_actions(self) -> None:
        self.add_btn.clicked.connect(self._pick_inputs)
        self.remove_btn.clicked.connect(self._remove_selected)
        self.clear_btn.clicked.connect(self._clear_inputs)
        self.pick_output_btn.clicked.connect(self._browse_output_dir)
        self.file_list.currentRowChanged.connect(self._on_row_changed)
        self.play_btn.clicked.connect(self._play_current)
        self.pause_btn.clicked.connect(self._pause_current)
        self.position_slider.sliderMoved.connect(self._seek_current)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.task_combo.currentIndexChanged.connect(self._on_task_changed)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        self.stem_mode_combo.currentTextChanged.connect(self._on_stem_mode_changed)
        self.chunk_spin.valueChanged.connect(self._on_chunk_changed)
        self.loudness_spin.valueChanged.connect(self._on_loudness_changed)
        self.true_peak_spin.valueChanged.connect(self._on_true_peak_changed)
        self.lra_spin.valueChanged.connect(self._on_lra_changed)
        self.convert_quality_combo.currentTextChanged.connect(self._on_convert_quality_changed)
        self.compress_level_combo.currentTextChanged.connect(self._on_compress_level_changed)
        self.enhance_profile_combo.currentTextChanged.connect(self._on_enhance_profile_changed)
        self.copy_metadata_check.toggled.connect(self._on_copy_metadata_changed)
        self.delete_original_check.toggled.connect(self._on_delete_original_changed)
        self.run_foldout.toggle_requested.connect(self._toggle_run_foldout)
        self.run_foldout.output_dir_edit.textChanged.connect(self._on_output_dir_text_changed)
        self.run_foldout.export_format_combo.currentTextChanged.connect(self._on_export_format_changed)
        self.run_foldout.browse_requested.connect(self._browse_output_dir)
        self.run_foldout.source_requested.connect(lambda: self._set_output_mode("source_folder"))
        self.run_foldout.task_folder_requested.connect(lambda: self._set_output_mode("task_folder"))
        self.run_foldout.custom_requested.connect(lambda: self._set_output_mode("custom_folder"))
        self.run_foldout.trim_check.toggled.connect(self._on_trim_toggled)
        self.run_foldout.trim_start_edit.textChanged.connect(self._on_trim_start_changed)
        self.run_foldout.trim_end_edit.textChanged.connect(self._on_trim_end_changed)
        self.run_foldout.run_requested.connect(self._run_task)

    def _sync_controls_from_state(self) -> None:
        self.task_combo.setCurrentIndex(max(0, self.task_combo.findData(self.state.task_type)))
        self.model_combo.setCurrentText(self.state.model)
        self.stem_mode_combo.setCurrentText(self.state.stem_mode)
        self.chunk_spin.setValue(self.state.chunk_duration)
        self.loudness_spin.setValue(self.state.target_loudness)
        self.true_peak_spin.setValue(self.state.true_peak)
        self.lra_spin.setValue(self.state.loudness_range)
        self.convert_quality_combo.setCurrentText(self.state.convert_quality)
        self.compress_level_combo.setCurrentText(self.state.compress_level)
        self.enhance_profile_combo.setCurrentText(self.state.enhance_profile)
        self.copy_metadata_check.setChecked(self.state.copy_metadata)
        self.delete_original_check.setChecked(self.state.delete_original)
        self.run_foldout.output_dir_edit.setText(str(self.state.custom_output_dir or ""))
        self.run_foldout.trim_start_edit.setText(self.state.trim_start)
        self.run_foldout.trim_end_edit.setText(self.state.trim_end)
        self.run_foldout.set_trim_enabled(self.state.trim_enabled)
        self._refresh_export_format_controls()

    def _refresh_all(self) -> None:
        self._refresh_list()
        self._refresh_preview()
        self._refresh_task_stack()
        self._refresh_export_format_controls()
        self._refresh_output_mode()
        self._refresh_status()

    def _refresh_list(self) -> None:
        self.file_list.blockSignals(True)
        self.file_list.clear()
        for path in self.state.files:
            item = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            self.file_list.addItem(item)
        if 0 <= self.state.selected_index < len(self.state.files):
            self.file_list.setCurrentRow(self.state.selected_index)
        self.file_list.blockSignals(False)
        self.header_surface.set_asset_count(len(self.state.files))

    def _refresh_preview(self) -> None:
        current = self._current_path()
        if current is None:
            self.now_playing.setText("No selection")
            self.audio_path.setText("")
            self.position_slider.setRange(0, 0)
            self.time_label.setText("0:00 / 0:00")
            return
        self.now_playing.setText(current.name)
        self.audio_path.setText(str(current))
        self.media_player.setSource(QUrl.fromLocalFile(str(current)))

    def _refresh_task_stack(self) -> None:
        self.task_stack.setCurrentIndex(TASK_STACK_INDEX.get(self.state.task_type, 0))

    def _refresh_export_format_controls(self) -> None:
        combo = self.run_foldout.export_format_combo
        combo.blockSignals(True)
        combo.clear()
        task = self.state.task_type
        formats = export_formats_for_task(task)
        combo.addItems(formats)
        if task in {TASK_EXTRACT_VOICE, TASK_EXTRACT_BGM}:
            combo.setCurrentText(self.state.separator_output_format)
        elif task == TASK_CONVERT_AUDIO:
            combo.setCurrentText(self.state.convert_output_format)
        elif task == TASK_COMPRESS_AUDIO:
            combo.setCurrentText(self.state.compress_output_format)
        elif task == TASK_ENHANCE_AUDIO:
            combo.setCurrentText(self.state.enhance_output_format)
        combo.blockSignals(False)
        combo.setVisible(bool(formats))

    def _refresh_output_mode(self) -> None:
        self.run_foldout.source_btn.setChecked(self.state.output_mode == "source_folder")
        self.run_foldout.task_folder_btn.setChecked(self.state.output_mode == "task_folder")
        self.run_foldout.custom_btn.setChecked(self.state.output_mode == "custom_folder")
        self.run_foldout.output_dir_edit.setEnabled(self.state.output_mode == "custom_folder")
        self.run_foldout.set_trim_enabled(self.state.trim_enabled)

    def _refresh_status(self) -> None:
        tone = "accent"
        runtime_badge = "Ready"
        if self.state.error_message:
            tone = "error"
            runtime_badge = "Error"
        elif self.state.is_processing:
            tone = "warning"
            runtime_badge = "Working"
        elif self.state.completed_count and self.state.completed_count == self.state.total_count:
            tone = "success"
            runtime_badge = "Complete"
        set_badge_role(self.header_surface.runtime_status_badge, "status", tone)
        self.header_surface.runtime_status_badge.setText(runtime_badge)
        self.run_foldout.progress_label.setText(f"{self.state.completed_count} / {self.state.total_count}")
        self.run_foldout.status_label.setText(self.state.status_text or "Ready")
        detail = self.state.detail_text or self.state.error_message or ""
        self.run_foldout.detail_label.setText(detail)
        self.run_foldout.detail_label.setVisible(self.run_foldout._expanded and bool(detail))
        total = self.state.total_count or len(self.state.files)
        if total:
            self.run_foldout.progress_label.setText(f"{self.state.completed_count}/{total}")
        else:
            self.run_foldout.progress_label.setText(f"{len(self.state.files)} items")
        can_run = bool(self.state.files) and not self.state.is_processing
        self.run_foldout.run_btn.setEnabled(can_run)
        self.remove_btn.setEnabled(self._current_path() is not None and not self.state.is_processing)
        self.clear_btn.setEnabled(bool(self.state.files) and not self.state.is_processing)
        tooltip = self._build_summary_tooltip()
        self.run_foldout.run_btn.setToolTip(tooltip)
        self.run_foldout.export_format_combo.setToolTip("Export format")
        self.run_foldout.toggle_btn.setToolTip("Output settings")
        self.pick_output_btn.setToolTip(tooltip)

    def _current_path(self) -> Path | None:
        if 0 <= self.state.selected_index < len(self.state.files):
            return self.state.files[self.state.selected_index]
        return None

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, APP_TITLE, "", FILTER_TEXT)
        if files:
            self.service.add_inputs(files)

    def _remove_selected(self) -> None:
        self.service.remove_input_at(self.file_list.currentRow())

    def _clear_inputs(self) -> None:
        self.service.clear_inputs()

    def _browse_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not folder:
            return
        self.state.custom_output_dir = Path(folder)
        self.run_foldout.output_dir_edit.setText(folder)
        self._set_output_mode("custom_folder")

    def _on_row_changed(self, index: int) -> None:
        self.state.selected_index = index
        self._refresh_preview()
        self._refresh_status()

    def _on_task_changed(self, index: int) -> None:
        self.state.task_type = str(self.task_combo.itemData(index))
        self._refresh_task_stack()
        self._refresh_export_format_controls()
        self._refresh_output_mode()
        self._refresh_preview()
        self._refresh_status()

    def _on_model_changed(self, value: str) -> None:
        self.state.model = value

    def _on_stem_mode_changed(self, value: str) -> None:
        self.state.stem_mode = value

    def _on_chunk_changed(self, value: int) -> None:
        self.state.chunk_duration = int(value)

    def _on_loudness_changed(self, value: float) -> None:
        self.state.target_loudness = float(value)

    def _on_true_peak_changed(self, value: float) -> None:
        self.state.true_peak = float(value)

    def _on_lra_changed(self, value: float) -> None:
        self.state.loudness_range = float(value)

    def _on_convert_quality_changed(self, value: str) -> None:
        self.state.convert_quality = value

    def _on_compress_level_changed(self, value: str) -> None:
        self.state.compress_level = value

    def _on_enhance_profile_changed(self, value: str) -> None:
        self.state.enhance_profile = value

    def _on_export_format_changed(self, value: str) -> None:
        if self.state.task_type in {TASK_EXTRACT_VOICE, TASK_EXTRACT_BGM}:
            self.state.separator_output_format = value.lower()
        elif self.state.task_type == TASK_CONVERT_AUDIO:
            self.state.convert_output_format = value.upper()
        elif self.state.task_type == TASK_COMPRESS_AUDIO:
            self.state.compress_output_format = value.upper()
        elif self.state.task_type == TASK_ENHANCE_AUDIO:
            self.state.enhance_output_format = value.upper()

    def _on_copy_metadata_changed(self, checked: bool) -> None:
        self.state.copy_metadata = checked

    def _on_delete_original_changed(self, checked: bool) -> None:
        self.state.delete_original = checked

    def _on_trim_toggled(self, checked: bool) -> None:
        self.state.trim_enabled = checked
        self.run_foldout.set_trim_enabled(checked)
        self._refresh_status()

    def _on_trim_start_changed(self, value: str) -> None:
        self.state.trim_start = value.strip()
        self._refresh_status()

    def _on_trim_end_changed(self, value: str) -> None:
        self.state.trim_end = value.strip()
        self._refresh_status()

    def _set_output_mode(self, mode: str) -> None:
        self.state.output_mode = mode
        if mode != "custom_folder":
            self.state.custom_output_dir = None
            self.run_foldout.output_dir_edit.blockSignals(True)
            self.run_foldout.output_dir_edit.setText("")
            self.run_foldout.output_dir_edit.blockSignals(False)
        elif not self.run_foldout.output_dir_edit.text().strip() and self.state.custom_output_dir:
            self.run_foldout.output_dir_edit.blockSignals(True)
            self.run_foldout.output_dir_edit.setText(str(self.state.custom_output_dir))
            self.run_foldout.output_dir_edit.blockSignals(False)
        self._refresh_output_mode()
        self._refresh_preview()

    def _on_output_dir_text_changed(self) -> None:
        if self.state.output_mode != "custom_folder":
            return
        raw_path = self.run_foldout.output_dir_edit.text().strip()
        self.state.custom_output_dir = Path(raw_path) if raw_path else None
        self._refresh_status()

    def _run_task(self) -> None:
        if self.state.output_mode == "custom_folder":
            raw_path = self.run_foldout.output_dir_edit.text().strip()
            if not raw_path:
                QMessageBox.warning(self, APP_TITLE, "Choose a custom output folder first.")
                return
            self.state.custom_output_dir = Path(raw_path)
        self.service.start()

    def _on_service_update(self, payload: dict) -> None:
        self._refresh_all()
        if payload.get("finished"):
            errors = payload.get("errors") or []
            if errors:
                QMessageBox.warning(self, APP_TITLE, "\n".join(errors[:5]))
            elif self.state.last_output_path is not None:
                QMessageBox.information(self, APP_TITLE, f"Finished.\nLast output:\n{self.state.last_output_path}")

    def _toggle_run_foldout(self) -> None:
        self.run_foldout.set_expanded(not self.run_foldout._expanded)
        self._refresh_export_format_controls()

    def _build_summary_tooltip(self) -> str:
        current = self._current_path()
        current_text = str(current) if current is not None else "No file selected"
        backend_text = f"Backend: {self.state.active_backend}" if self.state.active_backend else "Backend: auto"
        trim_text = "Trim: off"
        if self.state.trim_enabled:
            trim_text = f"Trim: {self.state.trim_start or 'start'} -> {self.state.trim_end or 'end'}"
        return "\n".join(
            [
                current_text,
                self.service.output_summary(),
                trim_text,
                self.service.runtime_summary(),
                backend_text,
            ]
        )

    def _play_current(self) -> None:
        if self._current_path() is not None:
            self.media_player.play()

    def _pause_current(self) -> None:
        self.media_player.pause()

    def _seek_current(self, value: int) -> None:
        self.media_player.setPosition(value)

    def _on_position_changed(self, position: int) -> None:
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(position)
        self.position_slider.blockSignals(False)
        self.time_label.setText(f"{self._format_time(position)} / {self._format_time(self._duration_ms)}")

    def _on_duration_changed(self, duration: int) -> None:
        self._duration_ms = duration
        self.position_slider.setRange(0, duration)
        self.time_label.setText(f"{self._format_time(0)} / {self._format_time(duration)}")

    @staticmethod
    def _format_time(ms: int) -> str:
        total_seconds = max(0, int(ms / 1000))
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"


def start_app(targets: list[Path] | None, app_root: str | Path) -> int:
    state = AudioToolboxState(files=[Path(item) for item in (targets or [])])
    if state.files:
        state.selected_index = 0
    app = QApplication.instance() or QApplication(sys.argv)
    window = AudioToolboxWindow(state, app_root)
    window.show()
    return app.exec()
