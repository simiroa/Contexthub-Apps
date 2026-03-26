from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.shell import (
    HeaderSurface,
    apply_app_icon,
    build_shell_stylesheet,
    build_size_grip,
    get_shell_metrics,
    get_shell_palette,
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
)
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


class ExportRunFoldout(QGroupBox):
    toggle_requested = Signal()
    browse_requested = Signal()
    source_requested = Signal()
    converted_requested = Signal()
    reveal_requested = Signal()
    run_requested = Signal()
    cancel_requested = Signal()

    def __init__(self) -> None:
        self._title_text = qt_t("video_convert_qt.convert_and_run", "Convert And Run")
        super().__init__(self._title_text)
        m = get_shell_metrics()
        self._expanded = False
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.setObjectName("runFoldout")
        self.setStyleSheet(
            "QGroupBox#runFoldout { margin-top: 8px; padding-top: 10px; } "
            "QGroupBox#runFoldout::title { left: 12px; top: 6px; padding: 0 3px; color: #b8c3d4; font-size: 12px; font-weight: 600; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 10)
        layout.setSpacing(6)

        self.details = QWidget()
        details_layout = QVBoxLayout(self.details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(5)

        self.output_dir_label = QLabel(qt_t("video_convert_qt.output_folder", "Output Folder"))
        self.output_dir_edit = QLineEdit()
        folder_row = QHBoxLayout()
        folder_row.setContentsMargins(0, 0, 0, 0)
        folder_row.setSpacing(6)
        self.browse_btn = QPushButton("…")
        self.browse_btn.setObjectName("iconBtn")
        self.browse_btn.clicked.connect(self.browse_requested.emit)
        folder_row.addWidget(self.output_dir_edit, 1)
        folder_row.addWidget(self.browse_btn, 0)
        details_layout.addWidget(self.output_dir_label)
        details_layout.addLayout(folder_row)

        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.setSpacing(6)
        self.source_btn = QPushButton(qt_t("video_convert_qt.source_folder", "Source"))
        self.source_btn.setCheckable(True)
        self.source_btn.setObjectName("segmentBtn")
        self.source_btn.setMinimumWidth(74)
        self.converted_btn = QPushButton(qt_t("video_convert_qt.converted_folder", "Converted"))
        self.converted_btn.setCheckable(True)
        self.converted_btn.setObjectName("segmentBtn")
        self.converted_btn.setMinimumWidth(88)
        self.open_btn = QPushButton("📁")
        self.open_btn.setObjectName("iconBtn")
        self.source_btn.clicked.connect(self.source_requested.emit)
        self.converted_btn.clicked.connect(self.converted_requested.emit)
        self.open_btn.clicked.connect(self.reveal_requested.emit)
        mode_row.addWidget(self.source_btn, 0)
        mode_row.addWidget(self.converted_btn, 0)
        mode_row.addWidget(self.open_btn, 0)
        mode_row.addStretch(1)
        details_layout.addLayout(mode_row)

        self.delete_original = QCheckBox(qt_t("video_convert_gui.delete_original", "Delete original"))
        details_layout.addWidget(self.delete_original)
        layout.addWidget(self.details)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)
        self.reveal_btn = QPushButton("📁")
        self.reveal_btn.setObjectName("iconBtn")
        self.reveal_btn.setToolTip(qt_t("video_convert_qt.open_output_folder", "Open output folder"))
        self.reveal_btn.clicked.connect(self.reveal_requested.emit)
        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setObjectName("iconBtn")
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        self.run_btn = QPushButton(qt_t("video_convert_qt.convert", "Convert"))
        self.run_btn.setObjectName("primary")
        self.run_btn.setMinimumHeight(max(38, m.primary_button_height - 6))
        self.toggle_btn = QPushButton("v")
        self.toggle_btn.setObjectName("iconBtn")
        self.toggle_btn.clicked.connect(self.toggle_requested.emit)
        button_row.addWidget(self.reveal_btn, 0)
        button_row.addWidget(self.cancel_btn, 0)
        button_row.addWidget(self.run_btn, 1)
        button_row.addWidget(self.toggle_btn, 0)
        layout.addLayout(button_row)

        self.status_label = QLabel(qt_t("video_convert_gui.ready_to_convert", "Ready to convert."))
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("panelHint")
        self.progress_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_label)

        self.run_btn.clicked.connect(self.run_requested.emit)
        self.set_expanded(False)

    def set_expanded(self, visible: bool) -> None:
        self._expanded = visible
        self.details.setVisible(visible)
        self.toggle_btn.setText("^" if visible else "v")
        self.output_dir_label.setVisible(visible)
        self.status_label.setVisible(visible)
        self.progress_label.setVisible(visible)
        self.setTitle(self._title_text if visible else "")


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
        self.resize(1480, 960)
        self.setMinimumSize(1180, 820)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._apply_compact_styles()
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
        root.setSpacing(m.section_gap)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
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
        self.splitter.setSizes([880, 540])
        shell_layout.addWidget(self.splitter, 1)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 2, 0)
        grip_row.addStretch(1)
        self.size_grip = build_size_grip()
        self.size_grip.setParent(self.window_shell)
        grip_row.addWidget(self.size_grip, 0, Qt.AlignRight | Qt.AlignBottom)
        shell_layout.addLayout(grip_row)
        root.addWidget(self.window_shell)

    def _build_left_panel(self) -> QFrame:
        m = get_shell_metrics()
        asset_list_min_height = getattr(m, "asset_list_min_height", 260)

        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.preview_card = QFrame()
        self.preview_card.setObjectName("subtlePanel")
        preview_layout = QVBoxLayout(self.preview_card)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(6)
        preview_title = QLabel(qt_t("video_convert_qt.preview_title", "Preview"))
        preview_title.setObjectName("sectionTitle")
        preview_title.setStyleSheet("font-size: 15px;")
        preview_layout.addWidget(preview_title)

        preview_shell = QFrame()
        preview_shell.setObjectName("subtlePanel")
        preview_shell.setStyleSheet("QFrame#subtlePanel { background: #0b0d11; }")
        preview_shell_layout = QVBoxLayout(preview_shell)
        preview_shell_layout.setContentsMargins(0, 0, 0, 0)
        preview_shell_layout.setSpacing(0)

        self.preview_stack_host = QWidget()
        self.preview_stack = QStackedLayout(self.preview_stack_host)
        self.preview_placeholder = QLabel(qt_t("video_convert_qt.preview_empty", "Select a video from the list below to preview it here."))
        self.preview_placeholder.setAlignment(Qt.AlignCenter)
        self.preview_placeholder.setWordWrap(True)
        self.preview_placeholder.setStyleSheet("padding: 24px; color: #9ca8bc;")
        self.preview_stack.addWidget(self.preview_placeholder)

        self.video_surface = None
        if HAS_MEDIA and QVideoWidget is not None and self.media_player is not None:
            self.video_surface = QVideoWidget()
            self.media_player.setVideoOutput(self.video_surface)
            self.preview_stack.addWidget(self.video_surface)
        preview_shell_layout.addWidget(self.preview_stack_host, 1)
        preview_layout.addWidget(preview_shell, 1)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)
        self.preview_name = QLabel(qt_t("video_convert_qt.no_selection", "No video selected"))
        self.preview_name.setObjectName("title")
        self.preview_time = QLabel("0:00 / 0:00")
        self.preview_time.setObjectName("muted")
        meta_row.addWidget(self.preview_name, 1)
        meta_row.addWidget(self.preview_time, 0)
        preview_layout.addLayout(meta_row)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(6)
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("iconBtn")
        self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.pause_btn = QPushButton()
        self.pause_btn.setObjectName("iconBtn")
        self.pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.volume_btn = QPushButton("🔊")
        self.volume_btn.setObjectName("iconBtn")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self._volume_value)
        self.volume_slider.setMaximumWidth(120)
        controls.addWidget(self.play_btn, 0)
        controls.addWidget(self.pause_btn, 0)
        controls.addWidget(self.position_slider, 1)
        controls.addWidget(self.volume_btn, 0)
        controls.addWidget(self.volume_slider, 0)
        preview_layout.addLayout(controls)
        layout.addWidget(self.preview_card, 3)

        self.list_card = QFrame()
        self.list_card.setObjectName("subtlePanel")
        list_layout = QVBoxLayout(self.list_card)
        list_layout.setContentsMargins(10, 10, 10, 10)
        list_layout.setSpacing(6)

        list_title_row = QHBoxLayout()
        list_title_row.setContentsMargins(0, 0, 0, 0)
        list_title_row.setSpacing(6)
        list_title = QLabel(qt_t("video_convert_qt.queue", "Queued Videos"))
        list_title.setObjectName("sectionTitle")
        list_title.setStyleSheet("font-size: 15px;")
        list_hint = QLabel(qt_t("video_convert_qt.queue_hint", "Select an item to update the preview above."))
        list_hint.setObjectName("muted")
        list_title_row.addWidget(list_title, 0)
        list_title_row.addStretch(1)
        list_title_row.addWidget(list_hint, 0)
        list_layout.addLayout(list_title_row)

        self.input_list = QListWidget()
        self.input_list.setMinimumHeight(asset_list_min_height)
        list_layout.addWidget(self.input_list, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(6)
        self.add_inputs_btn = QPushButton("＋")
        self.add_inputs_btn.setObjectName("iconBtn")
        self.add_inputs_btn.setToolTip(qt_t("video_convert_qt.add_inputs", "Add inputs"))
        self.remove_input_btn = QPushButton("✕")
        self.remove_input_btn.setObjectName("iconBtn")
        self.remove_input_btn.setToolTip(qt_t("video_convert_qt.remove_selected", "Remove selected"))
        self.clear_inputs_btn = QPushButton(qt_t("video_convert_qt.clear_all", "Clear"))
        self.clear_inputs_btn.setObjectName("pillBtn")
        self.clear_inputs_btn.setToolTip(qt_t("video_convert_qt.clear_all", "Clear"))
        action_row.addWidget(self.add_inputs_btn, 0)
        action_row.addWidget(self.remove_input_btn, 0)
        action_row.addWidget(self.clear_inputs_btn, 0)
        action_row.addStretch(1)
        list_layout.addLayout(action_row)
        layout.addWidget(self.list_card, 2)

        return card

    def _build_right_panel(self) -> QFrame:
        m = get_shell_metrics()
        palette = get_shell_palette()

        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        param_card = QFrame()
        param_card.setObjectName("subtlePanel")
        param_layout = QVBoxLayout(param_card)
        param_layout.setContentsMargins(10, 10, 10, 10)
        param_layout.setSpacing(8)

        title = QLabel(qt_t("video_convert_qt.parameters", "Parameters"))
        title.setObjectName("sectionTitle")
        desc = QLabel(qt_t("video_convert_qt.description", "Choose a preset, tune format and scale, then convert the queued videos."))
        desc.setObjectName("muted")
        desc.setWordWrap(True)
        param_layout.addWidget(title)
        param_layout.addWidget(desc)

        self.preset_label = QLabel(qt_t("video_convert_qt.preset", "Preset"))
        self.preset_label.setObjectName("eyebrow")
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("presetCombo")
        self.preset_combo.addItems(list(VIDEO_PRESETS.keys()))
        param_layout.addWidget(self.preset_label)
        param_layout.addWidget(self.preset_combo)

        self.format_group = self._create_group(qt_t("video_convert_gui.format_label", "Output Format"), palette)
        self.format_combo = QComboBox()
        self.format_combo.setObjectName("presetCombo")
        self.format_group.layout().addWidget(self.format_combo)
        param_layout.addWidget(self.format_group)

        self.scale_group = self._create_group(qt_t("video_convert_gui.scale_label", "Rescale"), palette)
        self.scale_combo = QComboBox()
        self.scale_combo.setObjectName("presetCombo")
        self.scale_combo.addItems(["100%", "50%", "25%", "Custom Width"])
        self.custom_width_edit = QLineEdit()
        self.custom_width_edit.setPlaceholderText(qt_t("video_convert_gui.width_placeholder", "Custom Width (px)"))
        self.scale_group.layout().addWidget(self.scale_combo)
        self.scale_group.layout().addWidget(self.custom_width_edit)
        param_layout.addWidget(self.scale_group)

        self.crf_group = self._create_group(qt_t("video_convert_gui.quality_crf", "Quality (CRF)"), palette)
        self.crf_label = QLabel("")
        self.crf_slider = QSlider(Qt.Horizontal)
        self.crf_slider.setMinimum(0)
        self.crf_slider.setMaximum(51)
        self.crf_group.layout().addWidget(self.crf_label)
        self.crf_group.layout().addWidget(self.crf_slider)
        param_layout.addWidget(self.crf_group)
        param_layout.addStretch(1)
        layout.addWidget(param_card, 1)

        self.run_card = ExportRunFoldout()
        layout.addWidget(self.run_card, 0)
        return card

    def _create_group(self, title: str, palette) -> QGroupBox:
        group = QGroupBox("")
        group.setStyleSheet(
            f"QGroupBox {{ background: {palette.surface_subtle}; border: 1px solid rgba(39, 52, 75, 0.4); border-radius: 10px; margin-top: 0px; padding-top: 0px; }}"
        )
        inner = QVBoxLayout(group)
        inner.setContentsMargins(8, 6, 8, 8)
        inner.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("eyebrow")
        inner.addWidget(title_label)
        return group

    def _apply_compact_styles(self) -> None:
        compact_field = """
            QComboBox {
                min-height: 30px;
                padding: 4px 10px;
                border-radius: 10px;
            }
            QLineEdit {
                min-height: 30px;
                padding: 4px 10px;
                border-radius: 10px;
            }
        """
        segment_style = """
            QPushButton#segmentBtn {
                min-height: 32px;
                padding: 4px 12px;
                border-radius: 12px;
                background: #1a2230;
                border: 1px solid rgba(118, 132, 156, 0.24);
            }
            QPushButton#segmentBtn:checked {
                background: #2a3547;
                border: 1px solid rgba(173, 188, 209, 0.34);
                color: #f1f5fb;
                font-weight: 600;
            }
        """
        self.preset_combo.setStyleSheet(compact_field)
        self.format_combo.setStyleSheet(compact_field)
        self.scale_combo.setStyleSheet(compact_field)
        self.custom_width_edit.setStyleSheet(compact_field)
        self.run_card.output_dir_edit.setStyleSheet(compact_field)
        self.run_card.source_btn.setStyleSheet(segment_style)
        self.run_card.converted_btn.setStyleSheet(segment_style)
        slider_style = """
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(156, 168, 188, 0.28);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #61c2ff;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #8ea2b7;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
        """
        self.position_slider.setStyleSheet(slider_style)
        self.volume_slider.setStyleSheet(slider_style)

    def _bind_actions(self) -> None:
        self.add_inputs_btn.clicked.connect(self._pick_inputs)
        self.remove_input_btn.clicked.connect(self._remove_selected_input)
        self.clear_inputs_btn.clicked.connect(self._clear_inputs)
        self.input_list.itemSelectionChanged.connect(self._sync_preview_from_selection)
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        self.scale_combo.currentTextChanged.connect(self._on_scale_changed)
        self.crf_slider.valueChanged.connect(self._on_crf_changed)
        self.custom_width_edit.textChanged.connect(self._on_custom_width_changed)
        self.run_card.toggle_requested.connect(self._toggle_run_card)
        self.run_card.browse_requested.connect(self._browse_output_dir)
        self.run_card.source_requested.connect(self._use_source_folder)
        self.run_card.converted_requested.connect(self._use_converted_folder)
        self.run_card.reveal_requested.connect(self._open_output_folder)
        self.run_card.run_requested.connect(self._start_conversion)
        self.run_card.cancel_requested.connect(self._cancel_conversion)
        self.run_card.output_dir_edit.textChanged.connect(self._on_output_dir_changed)
        self.run_card.delete_original.stateChanged.connect(self._on_delete_original_toggled)
        self.play_btn.clicked.connect(self._play_media)
        self.pause_btn.clicked.connect(self._pause_media)
        self.position_slider.sliderMoved.connect(self._seek_media)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_btn.clicked.connect(self._toggle_mute)

        if self.media_player is not None:
            self.media_player.positionChanged.connect(self._on_position_changed)
            self.media_player.durationChanged.connect(self._on_duration_changed)

    def _apply_state_to_controls(self) -> None:
        formats = _format_options(self.state)
        if self.state.output_format not in formats:
            self.state.output_format = formats[0]
        self.format_combo.clear()
        self.format_combo.addItems(formats)
        self.format_combo.setCurrentText(self.state.output_format)
        self.scale_combo.setCurrentText(self.state.scale)
        self.custom_width_edit.setText(self.state.custom_width)
        self.crf_slider.setValue(self.state.crf)
        self.run_card.output_dir_edit.setText(str(self.state.custom_output_dir) if self.state.custom_output_dir else "")
        self.run_card.delete_original.setChecked(self.state.delete_original)
        self.preset_combo.setCurrentText("Web MP4")

    def _refresh_all(self) -> None:
        self._refresh_list()
        self._refresh_preview()
        self._refresh_status()
        self._refresh_option_states()

    def _refresh_list(self) -> None:
        current_path = self.state.files[self._selected_index] if 0 <= self._selected_index < len(self.state.files) else None
        self.input_list.clear()
        for path in self.state.files:
            output_info = _output_path_for(self.state, path)
            item = QListWidgetItem(path.name)
            item.setToolTip(f"{path}\n{output_info}")
            self.input_list.addItem(item)
        if current_path and current_path in self.state.files:
            self._selected_index = self.state.files.index(current_path)
        elif self.state.files:
            self._selected_index = 0
        else:
            self._selected_index = -1
        if self._selected_index >= 0:
            self.input_list.setCurrentRow(self._selected_index)
        self.asset_count_badge.setText(qt_t("comfyui.qt_shell.asset_count", "{count} inputs", count=len(self.state.files)))

    def _refresh_preview(self) -> None:
        path = self._current_path()
        if path is None:
            self.preview_stack.setCurrentIndex(0)
            self.preview_name.setText(qt_t("video_convert_qt.no_selection", "No video selected"))
            self.preview_time.setText("0:00 / 0:00")
            self.preview_placeholder.setText(qt_t("video_convert_qt.preview_empty", "Select a video from the list below to preview it here."))
            self.position_slider.setRange(0, 0)
            return

        self.preview_name.setText(path.name)
        if self.media_player is not None and self.video_surface is not None:
            self.preview_stack.setCurrentIndex(1)
            self.media_player.setSource(QUrl.fromLocalFile(str(path)))
        else:
            self.preview_stack.setCurrentIndex(0)
            self.preview_placeholder.setText(str(path))

    def _refresh_status(self) -> None:
        runtime_text = (
            qt_t("video_convert_qt.nvenc_ready", "NVENC ready")
            if self.state.has_nvenc
            else qt_t("video_convert_qt.cpu_encode", "CPU encode")
        )
        if not self.state.ffmpeg_path:
            runtime_text = qt_t("video_convert_qt.ffmpeg_missing", "FFmpeg not found")
        self.runtime_status_badge.setText(runtime_text)
        self.run_card.status_label.setText(self.state.status_text or qt_t("video_convert_gui.ready_to_convert", "Ready to convert."))
        if self.state.total_count > 0:
            self.run_card.progress_label.setText(f"{self.state.completed_count}/{self.state.total_count} | {int(self.state.progress_value * 100)}%")
        else:
            self.run_card.progress_label.setText("")
        self.run_card.run_btn.setDisabled(self.state.is_processing or not self.state.files or not self.state.ffmpeg_path)
        self.run_card.cancel_btn.setDisabled(not self.state.is_processing)
        can_reveal = _resolve_output_dir(self.state) is not None
        self.run_card.open_btn.setDisabled(not can_reveal)
        self.run_card.reveal_btn.setDisabled(not can_reveal)
        is_custom = self.state.custom_output_dir is not None
        self.run_card.source_btn.setChecked(not is_custom and not self.state.save_to_folder)
        self.run_card.converted_btn.setChecked(not is_custom and self.state.save_to_folder)

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
        self.service.remove_input_at(self.input_list.currentRow())
        self._refresh_all()

    def _clear_inputs(self) -> None:
        self.service.clear_inputs()
        self._refresh_all()

    def _sync_preview_from_selection(self) -> None:
        self._selected_index = self.input_list.currentRow()
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
        self.run_card.set_expanded(not self.run_card._expanded)

    def _on_output_dir_changed(self, value: str) -> None:
        self.state.custom_output_dir = Path(value) if value.strip() else None
        if self.state.custom_output_dir:
            self.state.save_to_folder = False
        self._refresh_all()

    def _on_delete_original_toggled(self, checked: int) -> None:
        self.state.delete_original = bool(checked)

    def _browse_output_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, qt_t("video_convert_qt.choose_output", "Choose output folder"))
        if chosen:
            self.run_card.output_dir_edit.setText(chosen)

    def _use_source_folder(self) -> None:
        self.state.custom_output_dir = None
        self.state.save_to_folder = False
        self.run_card.output_dir_edit.blockSignals(True)
        self.run_card.output_dir_edit.setText("")
        self.run_card.output_dir_edit.blockSignals(False)
        self._refresh_all()

    def _use_converted_folder(self) -> None:
        if not self.state.files:
            return
        self.state.custom_output_dir = None
        self.state.save_to_folder = True
        self.run_card.output_dir_edit.blockSignals(True)
        self.run_card.output_dir_edit.setText("")
        self.run_card.output_dir_edit.blockSignals(False)
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
        self.volume_btn.setText("🔇" if value == 0 else "🔉" if value < 50 else "🔊")

    def _toggle_mute(self) -> None:
        if self.volume_slider.value() == 0:
            self.volume_slider.setValue(60 if self._volume_value == 0 else self._volume_value)
        else:
            self.volume_slider.setValue(0)

    def _on_position_changed(self, position: int) -> None:
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(position)
        self.position_slider.blockSignals(False)
        self.preview_time.setText(f"{_format_time(position)} / {_format_time(self._player_duration)}")

    def _on_duration_changed(self, duration: int) -> None:
        self._player_duration = duration
        self.position_slider.setRange(0, duration)
        self.preview_time.setText(f"{_format_time(0)} / {_format_time(duration)}")

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
