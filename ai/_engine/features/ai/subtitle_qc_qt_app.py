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
    set_badge_role,
    set_button_role,
)
from features.ai.subtitle_qc_document_logic import format_timestamp
from features.ai.subtitle_qc_qt_components import MediaPreviewHost, QueueDialog, ServiceBridge
from features.ai.subtitle_qc_service import SubtitleQcService

try:
    from PySide6.QtCore import Qt, QSettings, QTimer, QUrl, Slot
    from PySide6.QtGui import QAction, QColor, QTextCursor
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMenu,
        QPushButton,
        QSlider,
        QSplitter,
        QStatusBar,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
        QStyle,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for subtitle_qc.") from exc

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget

    HAS_MULTIMEDIA = True
except Exception:  # pragma: no cover
    HAS_MULTIMEDIA = False
    QAudioOutput = None
    QMediaPlayer = None
    QVideoWidget = None


APP_ID = "subtitle_qc"
APP_TITLE = qt_t("meeting_notes.title", "Meeting Notes AI")
APP_SUBTITLE = qt_t("meeting_notes.subtitle", "Transcribe meetings, review playback, and organize summary, decisions, and actions.")


def _format_ms(milliseconds: int) -> str:
    total = max(0, int(milliseconds))
    seconds = total // 1000
    minutes = seconds // 60
    hours = minutes // 60
    return f"{hours:02d}:{minutes % 60:02d}:{seconds % 60:02d}.{total % 1000:03d}"


def _document_has_timestamps(document) -> bool:
    return any(float(segment.end) > float(segment.start) for segment in getattr(document, "segments", []))


class MeetingNotesWindow(QMainWindow):
    def __init__(self, service: SubtitleQcService, app_root: str | Path, targets: list[str | Path] | None = None) -> None:
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
        self.queue_dialog: QueueDialog | None = None
        self._is_scrubbing = False
        self._suppress_transcript_change = False
        self._suppress_ai_summary_change = False
        self._transcript_dirty_local = False
        self._ai_summary_dirty_local = False
        self._last_transcript_asset: str | None = None
        self._last_ai_summary_asset: str | None = None
        self._search_matches: list[tuple[int, int]] = []
        self._search_match_index = -1

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
        self.resize(1680, 980)
        self.setMinimumSize(1420, 860)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self._apply_styles()
        self._restore_window_state()
        self._bind_actions()

        if targets:
            self.service.add_inputs([str(path) for path in targets])
        self._populate_provider_defaults()
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
        self.header.open_webui_btn.hide()
        shell_layout.addWidget(self.header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        splitter.addWidget(self._build_center_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 10)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([1160, 420])
        shell_layout.addWidget(splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, shell)

        root.addWidget(shell)
        self.setStatusBar(QStatusBar())

    def _build_center_panel(self) -> QWidget:
        m = get_shell_metrics()
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        self.preview_name = QLabel("Procissing")
        self.preview_name.setObjectName("sectionTitle")
        self.summary_status = QLabel("Ready")
        self.summary_mode = QLabel("Selected")
        self.summary_focus = QLabel("No meeting selected")
        self.files_btn = QPushButton("Queue")
        set_button_role(self.files_btn, "secondary")
        self.files_btn.setToolTip("Open the meeting queue to add, remove, or switch recordings.")
        for widget in (self.summary_status, self.summary_mode):
            set_badge_role(widget, "muted")
        self.summary_focus.setObjectName("summaryText")
        header_row.addWidget(self.preview_name, 0)
        header_row.addSpacing(8)
        header_row.addWidget(self.summary_status, 0)
        header_row.addWidget(self.summary_mode, 0)
        header_row.addWidget(self.summary_focus, 1)
        header_row.addWidget(self.files_btn, 0)
        layout.addLayout(header_row)

        layout.addWidget(self._build_media_strip())

        self.preview_host = MediaPreviewHost(QVideoWidget() if self.media_available and QVideoWidget is not None else None)
        self.preview_host.setMinimumHeight(56)
        self.preview_host.setMaximumHeight(220)
        if self.media_player is not None and self.preview_host._video_widget is not None:
            self.media_player.setVideoOutput(self.preview_host._video_widget)
        layout.addWidget(self.preview_host)

        editor_card = QFrame()
        editor_card.setObjectName("subtlePanel")
        editor_layout = QVBoxLayout(editor_card)
        editor_layout.setContentsMargins(12, 12, 12, 12)
        editor_layout.setSpacing(10)

        editor_toolbar = QHBoxLayout()
        self.transcript_status = QLabel("No transcript yet")
        self.transcript_status.setObjectName("summaryText")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search transcript")
        self.search_edit.setClearButtonEnabled(True)
        self.search_count_label = QLabel("0")
        self.search_count_label.setObjectName("summaryText")
        self.search_prev_btn = QPushButton()
        self.search_next_btn = QPushButton()
        self.insert_time_btn = QPushButton()
        self.sync_transcript_btn = QPushButton("Sync")
        self.export_btn = QToolButton()
        self.export_btn.setText("Export")
        self.export_btn.setPopupMode(QToolButton.InstantPopup)
        self.export_menu = QMenu(self)
        self.copy_transcript_action = QAction("Copy Transcript", self)
        self.open_folder_action = QAction("Open Folder", self)
        self.save_txt_action = QAction("Save TXT", self)
        self.save_md_action = QAction("Save MD", self)
        for action in (
            self.copy_transcript_action,
            self.open_folder_action,
            self.save_txt_action,
            self.save_md_action,
        ):
            self.export_menu.addAction(action)
        self.export_btn.setMenu(self.export_menu)
        for button in (
            self.search_prev_btn,
            self.search_next_btn,
            self.insert_time_btn,
            self.sync_transcript_btn,
        ):
            set_button_role(button, "secondary")
        set_button_role(self.export_btn, "secondary")
        self.search_prev_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.search_next_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        self.insert_time_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.search_prev_btn.setToolTip("Find previous match")
        self.search_next_btn.setToolTip("Find next match")
        self.insert_time_btn.setToolTip("Insert the current playback time into the transcript.")
        self.sync_transcript_btn.setToolTip("Apply your edited transcript text back into the structured transcript before running AI summary or saving.")
        self.export_btn.setToolTip("Copy or save the current transcript and notes.")
        editor_toolbar.addWidget(self.transcript_status, 1)
        editor_toolbar.addWidget(self.search_edit, 1)
        editor_toolbar.addWidget(self.search_count_label, 0)
        editor_toolbar.addWidget(self.search_prev_btn)
        editor_toolbar.addWidget(self.search_next_btn)
        editor_toolbar.addWidget(self.insert_time_btn)
        editor_toolbar.addWidget(self.sync_transcript_btn)
        editor_toolbar.addWidget(self.export_btn)
        editor_layout.addLayout(editor_toolbar)

        self.transcript_edit = QTextEdit()
        self.transcript_edit.setPlaceholderText(
            "Transcription will appear here.\n\nYou can edit the text directly.\nUse [00:12:34] or [00:12:34-00:12:58] at the start of a line to keep manual time markers."
        )
        editor_layout.addWidget(self.transcript_edit, 1)
        layout.addWidget(editor_card, 1)
        return panel

    def _build_media_strip(self) -> QWidget:
        card = QFrame()
        card.setObjectName("subtlePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        top = QHBoxLayout()
        self.current_file_label = QLabel("No media loaded")
        self.current_file_label.setObjectName("summaryText")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Selected", userData="selected")
        self.mode_combo.addItem("Queue", userData="batch")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Auto", "ko", "en", "ja", "zh", "es", "fr", "de", "ru", "it"])
        self.task_combo = QComboBox()
        self.task_combo.addItems(["transcribe", "translate"])
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(self.service.available_generation_providers())
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cuda", "cpu"])
        self.rate_combo = QComboBox()
        self.rate_combo.addItem("0.75x", userData=0.75)
        self.rate_combo.addItem("1.0x", userData=1.0)
        self.rate_combo.addItem("1.25x", userData=1.25)
        self.rate_combo.addItem("1.5x", userData=1.5)
        self.run_btn = QPushButton("Run Selected")
        self.advanced_toggle_btn = QPushButton("Advanced")
        self.advanced_toggle_btn.setCheckable(True)
        set_button_role(self.run_btn, "primary")
        set_button_role(self.advanced_toggle_btn, "secondary")
        for combo, width in (
            (self.language_combo, 92),
            (self.rate_combo, 92),
            (self.mode_combo, 110),
            (self.task_combo, 120),
            (self.provider_combo, 120),
            (self.device_combo, 96),
        ):
            combo.setMinimumWidth(width)
        self.model_combo.setMinimumWidth(220)
        top.addWidget(self.current_file_label, 1)
        top.addWidget(QLabel("Lang"))
        top.addWidget(self.language_combo)
        top.addWidget(QLabel("Playback"))
        top.addWidget(self.rate_combo)
        top.addWidget(self.advanced_toggle_btn)
        top.addWidget(self.run_btn)
        layout.addLayout(top)

        controls = QHBoxLayout()
        self.play_btn = QPushButton()
        self.pause_btn = QPushButton()
        set_button_role(self.play_btn, "icon")
        set_button_role(self.pause_btn, "icon")
        if self.media_available:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.seek = QSlider(Qt.Horizontal)
        self.time_label = QLabel("00:00:00.000 / 00:00:00.000")
        self.time_label.setObjectName("summaryText")
        controls.addWidget(self.play_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.seek, 1)
        controls.addWidget(self.time_label)
        layout.addLayout(controls)

        self.advanced_panel = QWidget()
        advanced_layout = QVBoxLayout(self.advanced_panel)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(8)
        advanced_row_1 = QHBoxLayout()
        advanced_row_1.setSpacing(8)
        advanced_row_1.addWidget(QLabel("Mode"))
        advanced_row_1.addWidget(self.mode_combo)
        advanced_row_1.addWidget(QLabel("Task"))
        advanced_row_1.addWidget(self.task_combo)
        advanced_row_1.addWidget(QLabel("Provider"))
        advanced_row_1.addWidget(self.provider_combo)
        advanced_row_2 = QHBoxLayout()
        advanced_row_2.setSpacing(8)
        advanced_row_2.addWidget(QLabel("Model"))
        advanced_row_2.addWidget(self.model_combo, 1)
        advanced_row_2.addWidget(QLabel("Device"))
        advanced_row_2.addWidget(self.device_combo)
        advanced_layout.addLayout(advanced_row_1)
        advanced_layout.addLayout(advanced_row_2)
        self.advanced_panel.setVisible(False)
        layout.addWidget(self.advanced_panel)
        return card

    def _build_right_panel(self) -> QWidget:
        m = get_shell_metrics()
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        summary_card = QFrame()
        summary_card.setObjectName("subtlePanel")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setSpacing(10)
        title = QLabel("Ollama Summary")
        title.setObjectName("sectionTitle")
        self.run_hint = QLabel("Generate a meeting summary from the edited transcript. Select a local Ollama model and run when the transcript is ready.")
        self.run_hint.setObjectName("summaryText")
        self.run_hint.setWordWrap(True)
        summary_layout.addWidget(title)
        summary_layout.addWidget(self.run_hint)

        model_row = QHBoxLayout()
        self.ollama_model_combo = QComboBox()
        self.refresh_ollama_btn = QPushButton("Refresh")
        self.summarize_btn = QPushButton("Summarize")
        self.cancel_btn = QPushButton("Cancel")
        set_button_role(self.refresh_ollama_btn, "secondary")
        set_button_role(self.summarize_btn, "primary")
        set_button_role(self.cancel_btn, "secondary")
        model_row.addWidget(self.ollama_model_combo, 1)
        model_row.addWidget(self.refresh_ollama_btn)
        summary_layout.addLayout(model_row)

        action_row = QHBoxLayout()
        action_row.addWidget(self.summarize_btn)
        action_row.addWidget(self.cancel_btn)
        summary_layout.addLayout(action_row)

        self.ai_summary_edit = QTextEdit()
        self.ai_summary_edit.setPlaceholderText("Ollama summary will appear here.")
        summary_layout.addWidget(self.ai_summary_edit, 1)

        note_actions = QHBoxLayout()
        self.copy_summary_btn = QPushButton("Copy Summary")
        self.save_summary_btn = QPushButton("Save Summary")
        set_button_role(self.copy_summary_btn, "secondary")
        set_button_role(self.save_summary_btn, "secondary")
        note_actions.addWidget(self.copy_summary_btn)
        note_actions.addWidget(self.save_summary_btn)
        summary_layout.addLayout(note_actions)
        layout.addWidget(summary_card, 1)
        return panel

    def _apply_styles(self) -> None:
        p = get_shell_palette()
        self.preview_host.setStyleSheet(
            f"""
            QFrame {{
                background: {p.surface_subtle};
                border: 1px solid {p.control_border};
                border-radius: 14px;
            }}
            QLabel {{
                color: {p.text};
                padding: 18px;
            }}
            """
        )
        self.transcript_edit.setStyleSheet(
            f"""
            QTextEdit {{
                border: 1px solid {p.control_border};
                border-radius: 12px;
                background: {p.field_bg};
                padding: 8px;
            }}
            """
        )

    def _bind_actions(self) -> None:
        self.files_btn.clicked.connect(self._show_files_dialog)
        self.play_btn.clicked.connect(self._play_media)
        self.pause_btn.clicked.connect(self._pause_media)
        self.seek.sliderPressed.connect(self._on_slider_pressed)
        self.seek.sliderReleased.connect(self._seek_released)
        self.seek.valueChanged.connect(self._seek)
        if self.media_player is not None:
            self.media_player.positionChanged.connect(self._on_position)
            self.media_player.durationChanged.connect(self._on_duration)

        self.mode_combo.currentIndexChanged.connect(self._sync_generation_options)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.model_combo.currentTextChanged.connect(self._sync_generation_options)
        self.task_combo.currentTextChanged.connect(self._sync_generation_options)
        self.device_combo.currentTextChanged.connect(self._sync_generation_options)
        self.language_combo.currentTextChanged.connect(self._sync_generation_options)
        self.rate_combo.currentIndexChanged.connect(self._sync_playback_rate)

        self.run_btn.clicked.connect(self._run)
        self.cancel_btn.clicked.connect(self._cancel)
        self.copy_transcript_action.triggered.connect(self._copy_transcript)
        self.open_folder_action.triggered.connect(self._reveal_output_dir)
        self.save_txt_action.triggered.connect(self._save_transcript_txt)
        self.save_md_action.triggered.connect(self._save_meeting_markdown)
        self.advanced_toggle_btn.toggled.connect(self._toggle_advanced_options)
        self.insert_time_btn.clicked.connect(self._insert_timestamp)
        self.sync_transcript_btn.clicked.connect(self._apply_transcript_edits)
        self.transcript_edit.textChanged.connect(self._on_transcript_changed)
        self.search_edit.textChanged.connect(self._update_search_matches)
        self.search_next_btn.clicked.connect(self._find_next_match)
        self.search_prev_btn.clicked.connect(self._find_previous_match)
        self.refresh_ollama_btn.clicked.connect(self._refresh_ollama_models)
        self.summarize_btn.clicked.connect(self._summarize_with_ollama)
        self.copy_summary_btn.clicked.connect(self._copy_ai_summary)
        self.save_summary_btn.clicked.connect(self._save_ai_summary)
        self.ai_summary_edit.textChanged.connect(self._on_ai_summary_changed)
        self.run_btn.setToolTip("Run transcription for the current meeting or the full queue, depending on the selected mode.")
        self.summarize_btn.setToolTip("Generate an Ollama summary from the current transcript.")
        self.advanced_toggle_btn.setToolTip("Show or hide provider, task, model, and device options.")

    def _populate_provider_defaults(self) -> None:
        if self.provider_combo.count() == 0:
            self.provider_combo.addItem("whisper")
        current = self.provider_combo.currentText() or "whisper"
        self._set_model_defaults(current)
        self._refresh_ollama_models()

    def _set_model_defaults(self, provider: str) -> None:
        defaults = {
            "whisper": "small",
            "cohere": "CohereLabs/cohere-transcribe-03-2026",
        }
        value = defaults.get(provider, "small")
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItem(value)
        self.model_combo.setCurrentText(value)
        self.model_combo.blockSignals(False)

    def _show_files_dialog(self) -> None:
        if self.queue_dialog is None:
            self.queue_dialog = QueueDialog(self, self.service, APP_TITLE)
        self.queue_dialog.refresh()
        self.queue_dialog.exec()
        self._sync_from_state()

    def _run_mode_is_batch(self) -> bool:
        return self.mode_combo.currentData() == "batch"

    def _sync_generation_options(self) -> None:
        self.service.update_generation_options(
            provider=self.provider_combo.currentText(),
            model=self.model_combo.currentText(),
            task=self.task_combo.currentText(),
            device=self.device_combo.currentText(),
            language=self.language_combo.currentText(),
            output_formats=["txt"],
        )

    def _sync_playback_rate(self) -> None:
        if self.media_player is not None:
            self.media_player.setPlaybackRate(float(self.rate_combo.currentData()))

    def _sync_from_state(self) -> None:
        state = self.service.state
        self.summary_status.setText(f"{state.generation_status} · {int(state.progress * 100)}%")
        self.summary_mode.setText("Queue" if self._run_mode_is_batch() else "Selected")
        set_badge_role(self.summary_status, state.generation_status_tone if state.generation_status_tone in {"accent", "success", "warning", "error"} else "muted")
        set_badge_role(self.summary_mode, "accent" if self._run_mode_is_batch() else "muted")
        self.run_btn.setText("Run Queue" if self._run_mode_is_batch() else "Run Selected")
        self.cancel_btn.setEnabled(state.is_processing)
        if self.queue_dialog is not None and self.queue_dialog.isVisible():
            self.queue_dialog.refresh()

        self._sync_options_panel()
        self._sync_preview()
        self._sync_transcript()
        self._sync_ai_summary()

    def _sync_options_panel(self) -> None:
        options = self.service.state.generation_options
        self.provider_combo.blockSignals(True)
        if self.provider_combo.findText(options.provider) < 0:
            self.provider_combo.addItem(options.provider)
        self.provider_combo.setCurrentText(options.provider)
        self.provider_combo.blockSignals(False)
        self.model_combo.blockSignals(True)
        self.model_combo.setCurrentText(options.model)
        self.model_combo.blockSignals(False)
        self.task_combo.blockSignals(True)
        self.language_combo.blockSignals(True)
        self.device_combo.blockSignals(True)
        self.task_combo.setCurrentText(options.task)
        self.language_combo.setCurrentText(options.language)
        self.device_combo.setCurrentText(options.device)
        self.task_combo.blockSignals(False)
        self.language_combo.blockSignals(False)
        self.device_combo.blockSignals(False)

    def _sync_preview(self) -> None:
        asset = self.service.get_selected_asset()
        self.summary_focus.setText(asset.path.name if asset else "No meeting selected")
        self.current_file_label.setText(asset.path.name if asset else "No meeting selected")
        if asset is None:
            if self.media_player is not None:
                self.media_player.setSource(QUrl())
            self.preview_host.set_video_mode(False)
            self.preview_name.setText("Procissing")
            self.time_label.setText("00:00:00.000 / 00:00:00.000")
            self.preview_host.hide()
            return

        self.preview_name.setText(asset.path.name)
        if self.media_player is not None:
            self.media_player.setSource(QUrl.fromLocalFile(str(asset.path)))
            self.media_player.setPlaybackRate(float(self.rate_combo.currentData()))

        if asset.kind == "video" and self.preview_host._video_widget is not None:
            self.preview_host.show()
            self.preview_host.set_video_mode(True)
            self.preview_host.set_placeholder_text("")
        else:
            self.preview_host.hide()

    def _sync_transcript(self) -> None:
        document = self.service.get_document()
        asset = self.service.get_selected_asset()
        asset_key = str(asset.path) if asset else None
        if document is None:
            self.transcript_status.setText("No transcript yet")
            self.search_count_label.setText("0")
            if self._transcript_dirty_local and self._last_transcript_asset == asset_key:
                return
            self._last_transcript_asset = asset_key
            if not self.transcript_edit.toPlainText().strip():
                return
            self._suppress_transcript_change = True
            self.transcript_edit.clear()
            self._suppress_transcript_change = False
            self._transcript_dirty_local = False
            self._clear_search_highlights()
            return

        has_timestamps = _document_has_timestamps(document)
        transcript = self.service.get_transcript_text(include_timestamps=has_timestamps)
        should_replace = asset_key != self._last_transcript_asset or not self._transcript_dirty_local
        if should_replace and self.transcript_edit.toPlainText() != transcript:
            self._suppress_transcript_change = True
            self.transcript_edit.setPlainText(transcript)
            self._suppress_transcript_change = False
            self._transcript_dirty_local = False
        self._last_transcript_asset = asset_key
        if has_timestamps:
            self.transcript_status.setText(f"{len(document.segments)} entries · time markers available")
        else:
            self.transcript_status.setText(f"{len(document.segments)} paragraphs · add manual time markers if needed")
        self._update_search_matches(self.search_edit.text())

    def _sync_ai_summary(self) -> None:
        summary = self.service.get_ai_summary()
        asset = self.service.get_selected_asset()
        asset_key = str(asset.path) if asset else None
        should_replace = asset_key != self._last_ai_summary_asset or not self._ai_summary_dirty_local
        if not should_replace or self.ai_summary_edit.toPlainText() == summary:
            self._last_ai_summary_asset = asset_key
            return
        self._suppress_ai_summary_change = True
        self.ai_summary_edit.blockSignals(True)
        self.ai_summary_edit.setPlainText(summary)
        self.ai_summary_edit.blockSignals(False)
        self._suppress_ai_summary_change = False
        self._ai_summary_dirty_local = False
        self._last_ai_summary_asset = asset_key

    def _refresh_ollama_models(self) -> None:
        models = self.service.list_ollama_models()
        current = self.ollama_model_combo.currentText()
        self.ollama_model_combo.blockSignals(True)
        self.ollama_model_combo.clear()
        if models:
            self.ollama_model_combo.addItems(models)
            if current and current in models:
                self.ollama_model_combo.setCurrentText(current)
        else:
            self.ollama_model_combo.addItem("No Ollama models found")
        self.ollama_model_combo.blockSignals(False)

    def _summarize_with_ollama(self) -> None:
        model = self.ollama_model_combo.currentText().strip()
        if not model or model == "No Ollama models found":
            self.statusBar().showMessage("No Ollama model available", 3000)
            return
        self._apply_transcript_edits()
        try:
            summary = self.service.summarize_transcript_with_ollama(model=model)
        except Exception as exc:
            self.statusBar().showMessage(f"Ollama summary failed: {exc}", 4000)
            return
        self._suppress_ai_summary_change = True
        self.ai_summary_edit.setPlainText(summary)
        self._suppress_ai_summary_change = False
        self._ai_summary_dirty_local = False
        self.statusBar().showMessage("Ollama summary generated", 2000)

    def _apply_transcript_edits(self) -> None:
        text = self.transcript_edit.toPlainText().strip()
        if not text:
            self.statusBar().showMessage("Nothing to save", 2000)
            return
        try:
            self.service.update_transcript_text(text)
        except Exception as exc:
            self.statusBar().showMessage(f"Transcript parse failed: {exc}", 4000)
            return
        self._transcript_dirty_local = False
        self.statusBar().showMessage("Transcript edits applied", 2000)

    def _insert_timestamp(self) -> None:
        cursor = self.transcript_edit.textCursor()
        if self.media_player is not None:
            stamp = format_timestamp(self.media_player.position() / 1000.0, "vtt").split(".")[0]
        else:
            stamp = "00:00:00"
        cursor.insertText(f"[{stamp}] ")
        self.transcript_edit.setTextCursor(cursor)
        self.transcript_edit.setFocus()

    def _copy_transcript(self) -> None:
        QApplication.clipboard().setText(self.transcript_edit.toPlainText())
        self.statusBar().showMessage("Transcript copied", 2000)

    def _save_transcript_txt(self) -> None:
        self._apply_transcript_edits()
        asset = self.service.get_selected_asset()
        suggested = f"{asset.path.stem if asset else 'meeting'}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Save Transcript", str(Path.home() / suggested), "Text Files (*.txt)")
        if not path:
            return
        Path(path).write_text(self.transcript_edit.toPlainText(), encoding="utf-8")
        self.statusBar().showMessage("Transcript saved", 2000)

    def _build_meeting_markdown(self) -> str:
        asset = self.service.get_selected_asset()
        title = asset.path.stem if asset else "Meeting"
        transcript = self.transcript_edit.toPlainText().strip()
        summary = self.ai_summary_edit.toPlainText().strip()
        return "\n\n".join(
            [
                f"# {title}",
                "## Ollama Summary\n" + (summary or "-"),
                "## Transcript\n" + (transcript or "-"),
            ]
        )

    def _copy_ai_summary(self) -> None:
        QApplication.clipboard().setText(self.ai_summary_edit.toPlainText())
        self.statusBar().showMessage("AI summary copied", 2000)

    def _save_meeting_markdown(self) -> None:
        self._apply_transcript_edits()
        asset = self.service.get_selected_asset()
        suggested = f"{asset.path.stem if asset else 'meeting'}.md"
        path, _ = QFileDialog.getSaveFileName(self, "Save Meeting Notes", str(Path.home() / suggested), "Markdown Files (*.md)")
        if not path:
            return
        Path(path).write_text(self._build_meeting_markdown(), encoding="utf-8")
        self.statusBar().showMessage("Meeting markdown saved", 2000)

    def _save_ai_summary(self) -> None:
        asset = self.service.get_selected_asset()
        suggested = f"{asset.path.stem if asset else 'meeting'}.summary.md"
        path, _ = QFileDialog.getSaveFileName(self, "Save AI Summary", str(Path.home() / suggested), "Markdown Files (*.md)")
        if not path:
            return
        Path(path).write_text(self.ai_summary_edit.toPlainText(), encoding="utf-8")
        self.statusBar().showMessage("AI summary saved", 2000)

    def _run(self) -> None:
        if self.service.state.is_processing:
            return
        self._sync_generation_options()
        if self._run_mode_is_batch():
            self.service.run_batch()
        else:
            self.service.run_selected()

    def _cancel(self) -> None:
        self.service.cancel_generation()

    def _reveal_output_dir(self) -> None:
        self.service.reveal_output_dir()

    def _on_provider_changed(self) -> None:
        self._set_model_defaults(self.provider_combo.currentText())
        self._sync_generation_options()

    def _toggle_advanced_options(self, checked: bool) -> None:
        self.advanced_panel.setVisible(checked)
        self.advanced_toggle_btn.setText("Advanced On" if checked else "Advanced")

    def _clear_search_highlights(self) -> None:
        self.transcript_edit.setExtraSelections([])

    def _update_search_matches(self, text: str) -> None:
        query = text.strip()
        content = self.transcript_edit.toPlainText()
        if not query or not content:
            self._search_matches = []
            self._search_match_index = -1
            self.search_count_label.setText("0")
            self._clear_search_highlights()
            return

        lower_content = content.lower()
        lower_query = query.lower()
        matches: list[tuple[int, int]] = []
        start = 0
        while True:
            index = lower_content.find(lower_query, start)
            if index < 0:
                break
            matches.append((index, len(query)))
            start = index + len(query)
        self._search_matches = matches
        if not matches:
            self._search_match_index = -1
        elif self._search_match_index >= len(matches):
            self._search_match_index = 0
        self.search_count_label.setText(str(len(matches)))

        selections: list[QTextEdit.ExtraSelection] = []
        if matches:
            highlight = QColor("#4f8cff")
            highlight.setAlpha(55)
            for offset, length in matches:
                cursor = self.transcript_edit.textCursor()
                cursor.setPosition(offset)
                cursor.setPosition(offset + length, QTextCursor.KeepAnchor)
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                selection.format.setBackground(highlight)
                selections.append(selection)
        self.transcript_edit.setExtraSelections(selections)

    def _find_match(self, backward: bool = False) -> None:
        if not self._search_matches:
            return
        if self._search_match_index < 0:
            self._search_match_index = len(self._search_matches) - 1 if backward else 0
        else:
            step = -1 if backward else 1
            self._search_match_index = (self._search_match_index + step) % len(self._search_matches)
        offset, length = self._search_matches[self._search_match_index]
        cursor = self.transcript_edit.textCursor()
        cursor.setPosition(offset)
        cursor.setPosition(offset + length, QTextCursor.KeepAnchor)
        self.transcript_edit.setTextCursor(cursor)
        self.transcript_edit.ensureCursorVisible()

    def _find_next_match(self) -> None:
        self._find_match(backward=False)

    def _find_previous_match(self) -> None:
        self._find_match(backward=True)

    def _on_transcript_changed(self) -> None:
        if self._suppress_transcript_change:
            return
        self._transcript_dirty_local = True
        self.transcript_status.setText("Unsaved edits")
        self._update_search_matches(self.search_edit.text())

    def _on_ai_summary_changed(self) -> None:
        if self._suppress_ai_summary_change:
            return
        self._ai_summary_dirty_local = True
        self.service.update_ai_summary(self.ai_summary_edit.toPlainText())

    def _play_media(self) -> None:
        if self.media_player is not None:
            self.media_player.play()

    def _pause_media(self) -> None:
        if self.media_player is not None:
            self.media_player.pause()

    def _on_slider_pressed(self) -> None:
        self._is_scrubbing = True

    def _seek(self, value: int) -> None:
        if self.media_player is None:
            return
        if self._is_scrubbing:
            self.time_label.setText(f"{_format_ms(value)} / {_format_ms(self.media_player.duration())}")
            return
        self.media_player.setPosition(value)

    def _seek_released(self) -> None:
        if self.media_player is None:
            return
        self._is_scrubbing = False
        self.media_player.setPosition(self.seek.value())

    def _on_position(self, position: int) -> None:
        if self.media_player is None:
            return
        self.seek.blockSignals(True)
        self.seek.setValue(position)
        self.seek.blockSignals(False)
        self.time_label.setText(f"{_format_ms(position)} / {_format_ms(self.media_player.duration())}")

    def _on_duration(self, duration: int) -> None:
        self.seek.setRange(0, duration)

    @Slot(dict)
    def _on_service_update(self, _payload: dict) -> None:
        QTimer.singleShot(0, self._sync_from_state)

    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current == self._runtime_signature:
            return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self.setStyleSheet(build_shell_stylesheet())
        self._apply_styles()

    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        if self._settings.value("is_maximized", False, bool):
            self.showMaximized()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._transcript_dirty_local and self.transcript_edit.toPlainText().strip():
            self._apply_transcript_edits()
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())
        self.service.export_session()
        super().closeEvent(event)


def start_app(targets: list[str] | None = None, app_root: str | Path | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    root = Path(app_root) if app_root else Path(__file__).resolve().parents[3] / "ai" / APP_ID
    window = MeetingNotesWindow(SubtitleQcService(), root, targets)
    window.show()
    return app.exec()
