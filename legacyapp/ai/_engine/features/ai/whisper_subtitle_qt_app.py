from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.panels import ExportFoldoutPanel, FixedParameterPanel
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
)
from features.ai.whisper_subtitle_service import WhisperSubtitleService

try:
    from PySide6.QtCore import Qt, QSettings, QTimer, QUrl, Signal, Slot
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QFrame,
        QHeaderView,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QPushButton,
        QSlider,
        QSplitter,
        QStatusBar,
        QStyle,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QTabWidget,
        QVBoxLayout,
        QWidget,
        QStackedLayout,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for whisper_subtitle.") from exc

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget

    HAS_MULTIMEDIA = True
except Exception:  # pragma: no cover
    HAS_MULTIMEDIA = False
    QAudioOutput = None
    QMediaPlayer = None
    QVideoWidget = None


APP_ID = "whisper_subtitle"
APP_TITLE = qt_t("whisper_subtitle.title", "Whisper Subtitle AI")
APP_SUBTITLE = qt_t("whisper_subtitle.subtitle", "Generate and edit subtitles directly.")


def _format_ms(milliseconds: int) -> str:
    seconds = max(0, int(milliseconds) // 1000)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    ms = max(0, int(milliseconds)) % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_timestamp(seconds: float, fmt: str = "srt") -> str:
    total = max(0.0, float(seconds))
    h = int(total // 3600)
    m = int((total % 3600) // 60)
    s = total % 60
    ms = int((s - int(s)) * 1000)
    if fmt == "vtt":
        return f"{h:02d}:{m:02d}:{int(s):02d}.{ms:03d}"
    return f"{h:02d}:{m:02d}:{int(s):02d},{ms:03d}"


def _segments_to_text(document, fmt: str) -> str:
    output: list[str] = []
    if fmt == "vtt":
        output.append("WEBVTT")
        output.append("")
    for index, item in enumerate(document.segments, start=1):
        output.append(str(index))
        output.append(f"{_format_timestamp(item.start, fmt)} --> {_format_timestamp(item.end, fmt)}")
        output.append(item.text)
        output.append("")
    return "\\n".join(output)


def _collect_formats(values: dict[str, bool]) -> list[str]:
    formats: list[str] = []
    for key, enabled in values.items():
        if enabled:
            formats.append(key)
    return formats


class ServiceBridge(QWidget):
    updated = Signal(dict)


class WhisperSubtitleWindow(QMainWindow):
    def __init__(self, service: WhisperSubtitleService, app_root: str | Path, targets: list[str | Path] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)

        self._bridge = ServiceBridge()
        self._bridge.updated.connect(self._on_service_update)
        self.service._on_update = self._bridge.updated.emit
        self._block_table_sync = False
        self._is_scrubbing = False

        self.media_available = HAS_MULTIMEDIA
        if self.media_available:
            self.media_player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.media_player.setAudioOutput(self.audio_output)
        else:
            self.media_player = None
            self.audio_output = None

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1580, 950)
        self.setMinimumSize(1280, 780)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self._apply_compact_styles()
        self._restore_window_state()
        self._bind_actions()

        if targets:
            self.service.add_inputs([str(path) for path in targets])
        self._sync_from_state()
        self._runtime_timer.start()

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(m.section_gap)

        shell = QFrame()
        shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root, show_webui=False)
        self.header.set_header_visibility(show_subtitle=True, show_asset_count=True, show_runtime_status=True)
        self.header.open_webui_btn.hide()
        self.runtime_status_badge = self.header.runtime_status_badge
        shell_layout.addWidget(self.header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_editor_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 7)
        splitter.setStretchFactor(2, 4)
        splitter.setSizes([470, 760, 360])
        shell_layout.addWidget(splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, shell)

        root.addWidget(shell)
        self.setStatusBar(QStatusBar())

    def _build_left_panel(self) -> QWidget:
        m = get_shell_metrics()
        p = get_shell_palette()
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        preview_card = QFrame()
        preview_card.setObjectName("subtlePanel")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(6)
        preview_title = QLabel(qt_t("whisper_subtitle.preview", "Media Preview"))
        preview_title.setObjectName("sectionTitle")
        preview_layout.addWidget(preview_title)

        preview_shell = QFrame()
        preview_shell.setObjectName("subtitlePreviewShell")
        preview_shell.setStyleSheet(f"QFrame#subtitlePreviewShell {{ background: {p.field_bg}; border-radius: 12px; }}")
        preview_shell_layout = QVBoxLayout(preview_shell)
        preview_shell_layout.setContentsMargins(0, 0, 0, 0)
        preview_shell_layout.setSpacing(0)

        self.preview_stack_host = QWidget()
        self.preview_stack = QStackedLayout(self.preview_stack_host)

        if self.media_available and QVideoWidget is not None:
            self.preview_surface = QVideoWidget()
            self.media_player.setVideoOutput(self.preview_surface)  # type: ignore[union-attr]
        else:
            self.preview_surface = None

        self.preview_placeholder = QLabel(qt_t("whisper_subtitle.no_media", "Select media to preview"))
        self.preview_placeholder.setAlignment(Qt.AlignCenter)
        self.preview_placeholder.setWordWrap(True)
        self.preview_placeholder.setStyleSheet(f"padding: 24px; color: {p.text_muted};")
        self.preview_placeholder.setMinimumHeight(m.preview_min_height)
        self.preview_stack.addWidget(self.preview_placeholder)

        if self.preview_surface:
            self.preview_surface.setMinimumHeight(m.preview_min_height)
            self.preview_stack.addWidget(self.preview_surface)
        preview_shell_layout.addWidget(self.preview_stack_host, 1)
        preview_layout.addWidget(preview_shell, 1)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)
        self.preview_name = QLabel(qt_t("whisper_subtitle.no_selection", "No media selected"))
        self.preview_name.setObjectName("title")
        self.preview_time = QLabel("0:00 / 0:00")
        self.preview_time.setObjectName("muted")
        meta_row.addWidget(self.preview_name, 1)
        meta_row.addWidget(self.preview_time, 0)
        preview_layout.addLayout(meta_row)

        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(6)
        self.play_btn = QPushButton()
        self.pause_btn = QPushButton()
        self.seek = QSlider(Qt.Horizontal)
        self.seek.setEnabled(False)
        self.time_label = self.preview_time
        if self.media_available and self.media_player is not None:
            self.play_btn.setObjectName("iconBtn")
            self.pause_btn.setObjectName("iconBtn")
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            control_row.addWidget(self.play_btn)
            control_row.addWidget(self.pause_btn)
            control_row.addWidget(self.seek, 1)
        else:
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.seek.setEnabled(False)
        preview_layout.addLayout(control_row)
        layout.addWidget(preview_card, 3)

        list_card = QFrame()
        list_card.setObjectName("subtlePanel")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(10, 10, 10, 10)
        list_layout.setSpacing(6)

        row = QHBoxLayout()
        title = QLabel(qt_t("whisper_subtitle.inputs", "Inputs"))
        title.setObjectName("sectionTitle")
        row.addWidget(title)
        self.assets_badge = QLabel("0")
        self.assets_badge.setObjectName("muted")
        self.assets_badge.setMaximumWidth(44)
        row.addStretch(1)
        row.addWidget(self.assets_badge)
        list_layout.addLayout(row)

        self.input_list = QListWidget()
        list_layout.addWidget(self.input_list, 1)

        self.preview_placeholder.setMinimumHeight(m.preview_min_height)
        self.preview_stack.addWidget(self.preview_placeholder)

        if self.preview_surface:
            self.preview_surface.setMinimumHeight(m.preview_min_height)
            self.preview_stack.addWidget(self.preview_surface)
        preview_shell_layout.addWidget(self.preview_stack_host, 1)
        preview_layout.addWidget(preview_shell, 1)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)
        self.preview_name = QLabel(qt_t("whisper_subtitle.no_selection", "No media selected"))
        self.preview_name.setObjectName("title")
        self.preview_time = QLabel("0:00 / 0:00")
        self.preview_time.setObjectName("muted")
        meta_row.addWidget(self.preview_name, 1)
        meta_row.addWidget(self.preview_time, 0)
        preview_layout.addLayout(meta_row)

        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(6)
        self.play_btn = QPushButton()
        self.pause_btn = QPushButton()
        self.seek = QSlider(Qt.Horizontal)
        self.seek.setEnabled(False)
        self.time_label = self.preview_time
        if self.media_available and self.media_player is not None:
            self.play_btn.setObjectName("iconBtn")
            self.pause_btn.setObjectName("iconBtn")
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            control_row.addWidget(self.play_btn)
            control_row.addWidget(self.pause_btn)
            control_row.addWidget(self.seek, 1)
        else:
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.seek.setEnabled(False)
        preview_layout.addLayout(control_row)
        layout.addWidget(preview_card, 3)

        list_card = QFrame()
        list_card.setObjectName("subtlePanel")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(10, 10, 10, 10)
        list_layout.setSpacing(6)

        row = QHBoxLayout()
        title = QLabel(qt_t("whisper_subtitle.inputs", "Inputs"))
        title.setObjectName("sectionTitle")
        row.addWidget(title)
        self.assets_badge = QLabel("0")
        self.assets_badge.setObjectName("muted")
        self.assets_badge.setMaximumWidth(44)
        row.addStretch(1)
        row.addWidget(self.assets_badge)
        list_layout.addLayout(row)

        self.input_list = QListWidget()
        list_layout.addWidget(self.input_list, 1)

        action_row = QHBoxLayout()
        self.add_btn = QPushButton("＋")
        self.add_btn.setObjectName("iconBtn")
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setObjectName("iconBtn")
        self.clear_btn = QPushButton(qt_t("whisper_subtitle.clear", "Clear Results"))
        self.clear_btn.setProperty("buttonRole", "pill")
        action_row.addWidget(self.add_btn)
        action_row.addWidget(self.remove_btn)
        action_row.addWidget(self.clear_btn)
        action_row.addStretch(1)
        list_layout.addLayout(action_row)
        layout.addWidget(list_card, 2)
        return panel

    def _build_editor_panel(self) -> QWidget:
        m = get_shell_metrics()
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.doc_state = QLabel(qt_t("whisper_subtitle.ready", "No active document"))
        self.doc_state.setObjectName("muted")
        self.edit_hint = QLabel(qt_t("whisper_subtitle.edit_hint", "Double-click a cell to edit."))
        self.edit_hint.setObjectName("muted")
        self.parse_error = QLabel("")
        self.parse_error.setObjectName("muted")
        self.parse_error.setStyleSheet(f"color: {get_shell_palette().error};")
        top_row.addWidget(self.doc_state, 1)
        top_row.addWidget(self.edit_hint, 0)
        top_row.addWidget(self.parse_error, 1)
        layout.addLayout(top_row)

        self.tabs = QTabWidget()
        segment_tab = QWidget()
        segment_layout = QVBoxLayout(segment_tab)
        self.segment_table = QTableWidget(0, 4)
        self.segment_table.setHorizontalHeaderLabels(["#", "Start", "End", "Text"])
        self.segment_table.setAlternatingRowColors(True)
        self.segment_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.segment_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.segment_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.segment_table.setWordWrap(False)
        self.segment_table.setShowGrid(False)
        self.segment_table.verticalHeader().setVisible(False)
        header = self.segment_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        segment_layout.addWidget(self.segment_table)
        self.tabs.addTab(segment_tab, qt_t("whisper_subtitle.segment_table", "Segments"))

        raw_tab = QWidget()
        raw_layout = QVBoxLayout(raw_tab)
        raw_row = QHBoxLayout()
        self.raw_format = QComboBox()
        self.raw_format.addItems(["srt", "vtt"])
        self.refresh_raw_btn = QPushButton(qt_t("whisper_subtitle.refresh_raw", "Refresh"))
        self.refresh_raw_btn.setProperty("buttonRole", "pill")
        self.apply_raw_btn = QPushButton(qt_t("whisper_subtitle.apply_raw", "Apply"))
        self.apply_raw_btn.setProperty("buttonRole", "pill")
        raw_row.addWidget(self.raw_format)
        raw_row.addWidget(self.refresh_raw_btn)
        raw_row.addWidget(self.apply_raw_btn)
        raw_row.addStretch(1)
        raw_layout.addLayout(raw_row)
        self.raw_editor = QTextEdit()
        self.raw_editor.setPlaceholderText(qt_t("whisper_subtitle.raw_placeholder", "No subtitle loaded"))
        self.raw_editor.setObjectName("subtitleRawEditor")
        raw_layout.addWidget(self.raw_editor, 1)
        self.tabs.addTab(raw_tab, qt_t("whisper_subtitle.raw", "Raw"))
        layout.addWidget(self.tabs, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        m = get_shell_metrics()
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(8)

        self.param_panel = FixedParameterPanel(
            title=qt_t("whisper_subtitle.parameters", "Parameters"),
            description=qt_t("whisper_subtitle.parameters_desc", "Compact generation controls"),
            preset_label=qt_t("whisper_subtitle.preset", "Preset"),
        )
        self.param_panel.preset_combo.hide()
        self.param_panel.preset_label.hide()
        self.param_panel.description_label.hide()

        self.mode_combo = QComboBox()
        self.mode_combo.addItem(qt_t("whisper_subtitle.selected_only", "Selected"), userData="selected")
        self.mode_combo.addItem(qt_t("whisper_subtitle.batch_mode", "Batch"), userData="batch")

        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v2", "large-v3"])
        self.task_combo = QComboBox()
        self.task_combo.addItems(["transcribe", "translate"])
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cuda", "cpu"])
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Auto", "en", "ko", "ja", "zh", "es", "fr", "de", "ru", "it"])

        self.fmt_srt = QCheckBox("SRT")
        self.fmt_vtt = QCheckBox("VTT")
        self.fmt_txt = QCheckBox("TXT")
        self.fmt_json = QCheckBox("JSON")
        self.fmt_srt.setChecked(True)
        self.fmt_vtt.setChecked(True)
        self.param_panel.add_field(qt_t("whisper_subtitle.run_mode", "Run mode"), self.mode_combo)
        self.param_panel.add_field(qt_t("whisper_subtitle.model_task", "Model / Task"), self._pair_widget(self.model_combo, self.task_combo))
        self.param_panel.add_field(qt_t("whisper_subtitle.device_language", "Device / Language"), self._pair_widget(self.device_combo, self.language_combo))
        self.param_panel.add_field(qt_t("whisper_subtitle.formats", "Formats"), self._formats_widget())
        layout.addWidget(self.param_panel, 1)

        self.export_panel = ExportFoldoutPanel(qt_t("whisper_subtitle.export_and_run", "Generate And Run"))
        layout.addWidget(self.export_panel)
        return panel

    def _pair_widget(self, left: QWidget, right: QWidget) -> QWidget:
        pair = QWidget()
        pair_layout = QHBoxLayout(pair)
        pair_layout.setContentsMargins(0, 0, 0, 0)
        pair_layout.setSpacing(6)
        pair_layout.addWidget(left, 1)
        pair_layout.addWidget(right, 1)
        return pair

    def _formats_widget(self) -> QWidget:
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(self.fmt_srt)
        row.addWidget(self.fmt_vtt)
        row.addWidget(self.fmt_txt)
        row.addWidget(self.fmt_json)
        row.addStretch(1)
        return wrap

    def _apply_compact_styles(self) -> None:
        p = get_shell_palette()
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
        slider_style = f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {p.button_bg};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {p.accent};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {p.text_muted};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
        """
        tab_style = f"""
            QTabWidget::pane {{
                border: 1px solid {p.control_border};
                border-radius: 12px;
                top: -1px;
                background: {p.surface_bg};
            }}
            QTabBar::tab {{
                min-height: 28px;
                padding: 4px 12px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{
                background: {p.card_bg};
            }}
        """
        table_style = f"""
            QTableWidget {{
                border: 1px solid {p.control_border};
                border-radius: 10px;
                background: {p.field_bg};
                alternate-background-color: {p.surface_subtle};
                selection-background-color: {p.accent_soft};
            }}
            QHeaderView::section {{
                padding: 6px 8px;
                border: none;
                border-right: 1px solid {p.control_border};
                background: {p.control_bg};
                color: {p.text};
            }}
        """
        raw_style = """
            QTextEdit#subtitleRawEditor {
                border-radius: 10px;
                padding: 8px;
            }
        """
        for widget in (self.mode_combo, self.model_combo, self.task_combo, self.device_combo, self.language_combo):
            widget.setStyleSheet(compact_field)
        self.export_panel.output_dir_edit.setStyleSheet(compact_field)
        self.export_panel.output_prefix_edit.setStyleSheet(compact_field)
        self.seek.setStyleSheet(slider_style)
        self.tabs.setStyleSheet(tab_style)
        self.segment_table.setStyleSheet(table_style)
        self.raw_editor.setStyleSheet(raw_style)

    def _bind_actions(self) -> None:
        self._wire_inputs()
        self._wire_player()
        self._wire_editor()
        self._wire_options()
        self._wire_actions()
        self._sync_from_state()

    def _wire_inputs(self) -> None:
        self.add_btn.clicked.connect(self._pick_inputs)
        self.remove_btn.clicked.connect(self._remove_selected)
        self.clear_btn.clicked.connect(self._clear_inputs)
        self.input_list.itemSelectionChanged.connect(self._on_selected_changed)

    def _wire_player(self) -> None:
        if not self.media_available or self.media_player is None:
            return
        self.play_btn.clicked.connect(self._play_media)
        self.pause_btn.clicked.connect(self._pause_media)
        self.seek.valueChanged.connect(self._seek)
        self.seek.sliderPressed.connect(self._on_slider_pressed)
        self.seek.sliderReleased.connect(self._seek_released)
        self.media_player.positionChanged.connect(self._on_position)
        self.media_player.durationChanged.connect(self._on_duration)
        self.media_player.errorOccurred.connect(lambda *_: self._set_parse_hint(qt_t("whisper_subtitle.media_error", "Media preview failed.")))

    def _wire_editor(self) -> None:
        self.segment_table.itemChanged.connect(self._on_segment_cell_changed)
        self.segment_table.itemSelectionChanged.connect(self._on_segment_selected)
        self.raw_format.currentTextChanged.connect(self._refresh_raw_editor)
        self.refresh_raw_btn.clicked.connect(self._refresh_raw_editor)
        self.apply_raw_btn.clicked.connect(self._apply_raw_editor)

    def _wire_options(self) -> None:
        self.model_combo.currentTextChanged.connect(lambda value: self.service.update_generation_options(model=value))
        self.task_combo.currentTextChanged.connect(lambda value: self.service.update_generation_options(task=value))
        self.device_combo.currentTextChanged.connect(lambda value: self.service.update_generation_options(device=value))
        self.language_combo.currentTextChanged.connect(lambda value: self.service.update_generation_options(language=value))
        self.fmt_srt.toggled.connect(self._sync_formats)
        self.fmt_vtt.toggled.connect(self._sync_formats)
        self.fmt_txt.toggled.connect(self._sync_formats)
        self.fmt_json.toggled.connect(self._sync_formats)

    def _wire_actions(self) -> None:
        self.export_panel.run_requested.connect(self._run)
        self.export_panel.export_requested.connect(self._export_session)
        self.export_panel.reveal_requested.connect(self._reveal_output_dir)
        self.export_panel.toggle_requested.connect(self._toggle_export_panel)
        self.cancel_btn.clicked.connect(self._cancel)

    def _run_mode_is_batch(self) -> bool:
        mode = self.mode_combo.currentData()
        if mode in {"batch", "selected"}:
            return mode == "batch"
        return self.mode_combo.currentText() == qt_t("whisper_subtitle.batch_mode", "Batch")

    def _set_parse_hint(self, message: str) -> None:
        self.parse_error.setText(message)
        self.parse_error.setStyleSheet(f"color: {get_shell_palette().error};")

    def _sync_controls_from_state(self) -> None:
        state = self.service.state
        is_processing = state.is_processing
        has_items = bool(state.queued_assets)

        self.remove_btn.setEnabled(has_items and not is_processing)
        self.clear_btn.setEnabled(has_items and not is_processing)
        self.add_btn.setEnabled(not is_processing)

        self.mode_combo.setEnabled(not is_processing)
        self.model_combo.setEnabled(not is_processing)
        self.task_combo.setEnabled(not is_processing)
        self.device_combo.setEnabled(not is_processing)
        self.language_combo.setEnabled(not is_processing)
        self.fmt_srt.setEnabled(not is_processing)
        self.fmt_vtt.setEnabled(not is_processing)
        self.fmt_txt.setEnabled(not is_processing)
        self.fmt_json.setEnabled(not is_processing)

        media_enabled = self.media_available and self.media_player is not None and (state.selected_asset is not None)
        if self.media_available and self.media_player is not None:
            self.play_btn.setEnabled(media_enabled and not is_processing)
            self.pause_btn.setEnabled(media_enabled and not is_processing)
            self.seek.setEnabled(media_enabled and not is_processing)

        self.export_panel.run_btn.setEnabled(has_items and not is_processing)
        self.export_panel.export_btn.setEnabled(has_items and not is_processing)
        self.export_panel.reveal_btn.setEnabled(has_items)
        self.cancel_btn.setEnabled(is_processing)
        self.export_panel.run_btn.setText(
            qt_t("whisper_subtitle.run_batch", "Run Batch")
            if self._run_mode_is_batch()
            else qt_t("whisper_subtitle.run_selected", "Run Selected")
        )
        self.export_panel.status_label.setText(state.generation_status)
        self._sync_output_panel()

    def _pick_inputs(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        filters = "Media Files (*.mp4 *.mov *.avi *.mkv *.webm *.mp3 *.wav *.m4a *.flac *.ogg)"
        files, _ = QFileDialog.getOpenFileNames(self, APP_TITLE, "", filters)
        if not files:
            return
        self.service.add_inputs(files)
        self._sync_from_state()

    def _remove_selected(self) -> None:
        self.service.remove_input_at(self.input_list.currentRow())
        self._sync_from_state()

    def _clear_inputs(self) -> None:
        self.service.clear_inputs()
        self._sync_from_state()

    def _on_selected_changed(self) -> None:
        row = self.input_list.currentRow()
        if row < 0:
            if self.input_list.count() == 0:
                self._refresh_editor()
            self._sync_controls_from_state()
            return
        try:
            target = self.service.state.queued_assets[row].path
        except Exception:
            return
        self.service.set_selected_asset(target)
        self.service.load_session_for_asset(target)
        self._sync_from_state()

    def _sync_from_state(self) -> None:
        state = self.service.state
        self.input_list.clear()
        for name, path in self.service.get_selected_items():
            item = QListWidgetItem(name)
            item.setToolTip(path)
            self.input_list.addItem(item)

        self.assets_badge.setText(str(len(state.queued_assets)))
        self.header.set_asset_count(len(state.queued_assets))
        self.runtime_status_badge.setText(state.generation_status)

        if state.selected_asset is None and state.queued_assets:
            state.selected_asset = state.queued_assets[0].path
        if state.selected_asset is not None and state.queued_assets:
            for index, asset in enumerate(state.queued_assets):
                if asset.path == state.selected_asset:
                    self.input_list.setCurrentRow(index)
                    break

        self._sync_preview()
        self._refresh_editor()
        self._sync_output_panel()
        self._sync_controls_from_state()

    def _sync_preview(self) -> None:
        selected = self.service.state.selected_asset
        if selected is None:
            if self.media_available and self.media_player is not None:
                self.media_player.setSource(QUrl())
                self.seek.setValue(0)
                self.seek.setEnabled(False)
            self.preview_name.setText(qt_t("whisper_subtitle.no_selection", "No media selected"))
            self.preview_time.setText("0:00 / 0:00")
            self.preview_placeholder.setText(qt_t("whisper_subtitle.no_selection", "No selection"))
            if hasattr(self, "preview_stack"):
                self.preview_stack.setCurrentIndex(0)
            return

        if self.media_available and self.media_player is not None and self.preview_surface is not None:
            self.media_player.setSource(QUrl.fromLocalFile(str(selected)))
            self.preview_name.setText(selected.name)
            self.preview_stack.setCurrentIndex(1)
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(True)
        else:
            self.preview_name.setText(selected.name)
            self.preview_time.setText("0:00 / 0:00")
            self.preview_placeholder.setText(selected.name)
            if hasattr(self, "preview_stack"):
                self.preview_stack.setCurrentIndex(0)

    def _refresh_editor(self) -> None:
        document = self.service.get_documents()
        if document is None:
            self.doc_state.setText(qt_t("whisper_subtitle.no_document", "No document"))
            self.edit_hint.setText(qt_t("whisper_subtitle.edit_hint", "Double-click a cell to edit."))
            self.parse_error.setText("")
            self.segment_table.setRowCount(0)
            self.raw_editor.clear()
            return

        self.doc_state.setText(qt_t("whisper_subtitle.segment_count", "{count} segments", count=len(document.segments)))
        self.edit_hint.setText(qt_t("whisper_subtitle.edit_hint", "Double-click a cell to edit."))
        self.parse_error.setText(document.parse_error or "")

        self._block_table_sync = True
        self.segment_table.setRowCount(0)
        for row, segment in enumerate(document.segments):
            self.segment_table.insertRow(row)
            self.segment_table.setItem(row, 0, QTableWidgetItem(str(segment.segment_id)))
            self.segment_table.setItem(row, 1, QTableWidgetItem(f"{segment.start:.3f}"))
            self.segment_table.setItem(row, 2, QTableWidgetItem(f"{segment.end:.3f}"))
            self.segment_table.setItem(row, 3, QTableWidgetItem(segment.text))
            id_item = self.segment_table.item(row, 0)
            if id_item is not None:
                id_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self._block_table_sync = False
        self.segment_table.resizeRowsToContents()
        self._refresh_raw_editor()

    def _sync_output_panel(self) -> None:
        self.export_panel.set_values(
            str(self.service.state.output_options.output_dir) if self.service.state.output_options.output_dir else "",
            self.service.state.output_options.file_prefix,
            self.service.state.output_options.open_folder_after_run,
            self.service.state.output_options.export_session_json,
        )
        self.export_panel.refresh_summary()

        options = self.service.state.generation_options
        self.model_combo.blockSignals(True)
        self.task_combo.blockSignals(True)
        self.device_combo.blockSignals(True)
        self.language_combo.blockSignals(True)
        self.model_combo.setCurrentText(options.model)
        self.task_combo.setCurrentText(options.task)
        self.device_combo.setCurrentText(options.device)
        self.language_combo.setCurrentText(options.language)
        self.model_combo.blockSignals(False)
        self.task_combo.blockSignals(False)
        self.device_combo.blockSignals(False)
        self.language_combo.blockSignals(False)

        self.fmt_srt.setChecked("srt" in options.output_formats)
        self.fmt_vtt.setChecked("vtt" in options.output_formats)
        self.fmt_txt.setChecked("txt" in options.output_formats)
        self.fmt_json.setChecked("json" in options.output_formats)

    def _sync_formats(self) -> None:
        self.service.update_generation_options(
            output_formats=_collect_formats(
                {
                    "srt": self.fmt_srt.isChecked(),
                    "vtt": self.fmt_vtt.isChecked(),
                    "txt": self.fmt_txt.isChecked(),
                    "json": self.fmt_json.isChecked(),
                }
            )
        )

    def _refresh_raw_editor(self, *_args: object) -> None:
        document = self.service.get_documents()
        if document is None:
            self.raw_editor.clear()
            return
        self.raw_editor.blockSignals(True)
        self.raw_editor.setPlainText(_segments_to_text(document, self.raw_format.currentText()))
        self.raw_editor.blockSignals(False)

    def _apply_raw_editor(self) -> None:
        document = self.service.get_documents()
        if document is None:
            return
        ok, message = self.service.apply_text_edit(
            document.asset_path,
            self.raw_format.currentText(),
            self.raw_editor.toPlainText(),
        )
        self.parse_error.setText(message)
        if not ok:
            self._set_parse_hint(message)
            return
        self._refresh_editor()

    def _on_segment_cell_changed(self, item: QTableWidgetItem) -> None:
        if self._block_table_sync or item is None:
            return
        document = self.service.get_documents()
        if document is None:
            return

        row = item.row()
        segment_id_item = self.segment_table.item(row, 0)
        if segment_id_item is None:
            return
        try:
            segment_id = int(segment_id_item.text())
        except Exception:
            return

        if item.column() == 1:
            self.service.update_segment(document.asset_path, segment_id, "start", item.text())
        elif item.column() == 2:
            self.service.update_segment(document.asset_path, segment_id, "end", item.text())
        elif item.column() == 3:
            self.service.update_segment(document.asset_path, segment_id, "text", item.text())
        self._refresh_raw_editor()

    def _on_segment_selected(self) -> None:
        rows = self.segment_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        document = self.service.get_documents()
        if document is None or self.media_player is None:
            return
        if 0 <= row < len(document.segments):
            self.media_player.setPosition(int(document.segments[row].start * 1000))

    def _play_media(self) -> None:
        if self.media_player is None:
            return
        self.media_player.play()

    def _pause_media(self) -> None:
        if self.media_player is None:
            return
        self.media_player.pause()

    def _on_slider_pressed(self) -> None:
        self._is_scrubbing = True

    def _seek(self, value: int) -> None:
        if not self.media_available or self.media_player is None:
            return
        if self._is_scrubbing:
            self.time_label.setText(f"{_format_ms(value)} / {_format_ms(self.media_player.duration())}")
            return
        self.media_player.setPosition(value)

    def _seek_released(self) -> None:
        if not self.media_available or self.media_player is None:
            return
        self._is_scrubbing = False
        self.media_player.setPosition(self.seek.value())

    def _on_position(self, position: int) -> None:
        if self.media_player is None:
            return
        self.seek.blockSignals(True)
        self.seek.setValue(position)
        self.seek.setEnabled(True)
        self.seek.blockSignals(False)
        segment_index = self.service.get_segment_at_time(self.service.state.selected_asset, position)
        if segment_index is not None:
            self._highlight_segment(segment_index)
        self.time_label.setText(f"{_format_ms(position)} / {_format_ms(self.media_player.duration())}")

    def _on_duration(self, duration: int) -> None:
        self.seek.setRange(0, duration)

    def _highlight_segment(self, active_row: int) -> None:
        for row in range(self.segment_table.rowCount()):
            for col in range(self.segment_table.columnCount()):
                item = self.segment_table.item(row, col)
                if item is None:
                    continue
                item.setBackground(QColor(0, 0, 0, 0))
            if row == active_row:
                for col in range(self.segment_table.columnCount()):
                    target = self.segment_table.item(row, col)
                    if target is not None:
                        target.setBackground(QColor(45, 92, 146, 80))
                focus_item = self.segment_table.item(row, 3) or self.segment_table.item(row, 0)
                if focus_item is not None:
                    self.segment_table.scrollToItem(focus_item, QAbstractItemView.PositionAtCenter)

    def _sync_output_options(self) -> None:
        self.service.update_output_options(
            self.export_panel.output_dir_edit.text(),
            self.export_panel.output_prefix_edit.text(),
            self.export_panel.open_folder_checkbox.isChecked(),
            self.export_panel.export_session_checkbox.isChecked(),
        )
        document = self.service.get_documents()
        if document is not None:
            document.meta_file_prefix = self.export_panel.output_prefix_edit.text().strip() or document.asset_path.stem
        self._sync_output_panel()

    def _run(self) -> None:
        if self.service.state.is_processing:
            return
        self._sync_output_options()
        self._sync_formats()
        if self._run_mode_is_batch():
            self.service.run_batch()
        else:
            self.service.run_selected()

    def _cancel(self) -> None:
        self.service.cancel_generation()

    def _reveal_output_dir(self) -> None:
        self._sync_output_options()
        self.service.reveal_output_dir()

    def _export_session(self) -> None:
        self._sync_output_options()
        document = self.service.get_documents()
        if document is None:
            return
        path = self.service.export_session(document.asset_path)
        self.export_panel.status_label.setText(str(path))

    def _toggle_export_panel(self) -> None:
        self.export_panel.set_expanded(not self.export_panel.details.isVisible())

    @Slot(dict)
    def _on_service_update(self, payload: dict) -> None:
        QTimer.singleShot(0, self._sync_from_state)

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

    def closeEvent(self, event) -> None:  # noqa: N802
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())
        super().closeEvent(event)


def start_app(targets: list[str] | None = None, app_root: str | Path | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    root = Path(app_root) if app_root else Path(__file__).resolve().parents[3] / "ai" / APP_ID
    window = WhisperSubtitleWindow(WhisperSubtitleService(), root, targets)
    window.show()
    return app.exec()
