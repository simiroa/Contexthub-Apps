from __future__ import annotations

import os
import sys
import threading
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
)
from features.ai.standalone.qwen3_tts_profile_editor import Qwen3TTSProfileDialog
from features.ai.standalone.qwen3_tts_qt_service import Qwen3TTSQtService
from features.ai.standalone.qwen3_tts_qt_widgets import MessageBubbleWidget, status_text
from features.ai.standalone.qwen3_tts_service import SUPPORTED_LANGUAGES, SUPPORTED_SPEAKERS, TONE_PRESETS

try:
    from PySide6.QtCore import QObject, QSettings, QTimer, Qt, QUrl, Signal
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for qwen3_tts.") from exc

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except Exception:  # pragma: no cover
    QAudioOutput = None
    QMediaPlayer = None


APP_ID = "qwen3_tts"
APP_TITLE = qt_t("qwen3_tts.title", "Qwen3 TTS")
APP_SUBTITLE = qt_t("qwen3_tts.subtitle", "Chat-style voice generation with preset, clone, and design modes.")


def _has_media_player() -> bool:
    return QMediaPlayer is not None and QAudioOutput is not None


class _RunSignals(QObject):
    progress = Signal(str)
    done = Signal(bool, str)


class Qwen3TTSQtWindow(QMainWindow):
    def __init__(self, service: Qwen3TTSQtService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        self._is_running = False
        self._updating_ui = False
        self._expanded_message_id: str | None = None
        self._editing_profile_id: str | None = None

        self._bridge = _RunSignals()
        self._bridge.progress.connect(self._on_generation_progress)
        self._bridge.done.connect(self._on_generation_done)

        if _has_media_player():
            self.player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.player.setAudioOutput(self.audio_output)
        else:
            self.player = None
            self.audio_output = None

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1560, 980)
        self.setMinimumSize(1220, 760)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())

        self._build_ui()
        self._restore_window_state()
        self._bind_actions()
        self._refresh_all()
        self._runtime_timer.start()

    def _accent_generate_button(self, button: QPushButton) -> None:
        button.setProperty("buttonRole", "primary")
        button.style().unpolish(button)
        button.style().polish(button)

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        p = get_shell_palette()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)
        root.setSpacing(m.section_gap)

        shell = QFrame()
        shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root, show_webui=False)
        self.header_surface.set_header_visibility(show_subtitle=True, show_asset_count=True, show_runtime_status=True)
        self.header_surface.open_webui_btn.hide()
        self.asset_count_badge = self.header_surface.asset_count_badge
        self.runtime_status_badge = self.header_surface.runtime_status_badge
        shell_layout.addWidget(self.header_surface)

        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_bottom_panel())
        splitter.setStretchFactor(0, 8)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([700, 320])
        shell_layout.addWidget(splitter, 1)

        self.size_grip = attach_size_grip(shell_layout, shell)

        root.addWidget(shell)
        self._build_profile_dialog()

    def _build_left_panel(self) -> QFrame:
        m = get_shell_metrics()
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(m.section_gap)

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel(qt_t("qwen3_tts.conversation", "Conversation")), 1)
        self.message_count_label = QLabel("0")
        self.message_count_label.setObjectName("muted")
        title_row.addWidget(self.message_count_label)
        layout.addLayout(title_row)

        self.message_list = QListWidget()
        self.message_list.setMinimumHeight(360)
        self.message_list.setSpacing(8)
        self.message_list.setStyleSheet(
            """
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                padding: 4px 0;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 2px 0;
            }
            QListWidget::item:selected {
                background: transparent;
            }
            """
        )
        layout.addWidget(self.message_list, 1)
        return panel

    def _build_bottom_panel(self) -> QFrame:
        m = get_shell_metrics()
        p = get_shell_palette()
        container = QFrame()
        container.setObjectName("card")
        root = QVBoxLayout(container)
        root.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        result_card = QFrame()
        result_card.setObjectName("subtlePanel")
        result_layout = QHBoxLayout(result_card)
        result_layout.setContentsMargins(16, 14, 16, 14)
        result_layout.setSpacing(16)

        result_meta = QVBoxLayout()
        result_meta.setContentsMargins(0, 0, 0, 0)
        result_meta.setSpacing(4)
        result_meta.addWidget(QLabel(qt_t("qwen3_tts.result_panel", "Selected Result")))
        self.result_status_label = QLabel(qt_t("qwen3_tts.ready", "Ready"))
        self.result_status_label.setObjectName("muted")
        self.result_path_label = QLabel("")
        self.result_path_label.setWordWrap(True)
        self.result_file_label = QLabel("")
        self.result_file_label.setWordWrap(True)
        result_meta.addWidget(self.result_status_label)
        result_meta.addWidget(self.result_path_label)
        # ... removed duplication ...

        root.addLayout(top_row)

        # ... removed duplication ...

        result_row = QHBoxLayout()
        result_row.setSpacing(8)
        self.play_btn = QPushButton(qt_t("qwen3_tts.play", "Play Audio"))
        self.play_btn.setProperty("buttonRole", "pill")
        self.open_file_btn = QPushButton(qt_t("qwen3_tts.open_file", "Open File"))
        self.open_file_btn.setProperty("buttonRole", "pill")
        self.open_folder_btn = QPushButton("📂")
        self.open_folder_btn.setProperty("buttonRole", "pill")
        self.rerun_btn = QPushButton("⟳ Generate This")
        self._accent_generate_button(self.rerun_btn)
        result_row.addWidget(self.play_btn, 0)
        result_row.addWidget(self.open_file_btn, 0)
        result_row.addWidget(self.open_folder_btn, 0)
        result_row.addWidget(self.rerun_btn, 0)
        result_layout.addLayout(result_row)
        root.addWidget(result_card, 0)

        composer_card = QFrame()
        composer_card.setObjectName("subtlePanel")
        composer_layout = QVBoxLayout(composer_card)
        composer_layout.setContentsMargins(16, 14, 16, 14)
        composer_layout.setSpacing(10)

        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(10)
        self.composer_profile_combo = QComboBox()
        self.composer_profile_combo.setObjectName("presetCombo")
        self.composer_tone_combo = QComboBox()
        self.composer_tone_combo.addItems(list(TONE_PRESETS.keys()))
        self.composer_language_combo = QComboBox()
        self.composer_language_combo.addItems(SUPPORTED_LANGUAGES)
        self.composer_device_combo = QComboBox()
        self.composer_device_combo.addItems(["auto", "cuda", "cpu"])
        control_row.addWidget(self.composer_profile_combo, 0)
        control_row.addWidget(self.composer_tone_combo, 0)
        control_row.addWidget(self.composer_language_combo, 0)
        control_row.addWidget(self.composer_device_combo, 0)
        control_row.addStretch(1)
        self.composer_count_label = QLabel("0 / 2000 chars")
        self.composer_count_label.setObjectName("muted")
        control_row.addWidget(self.composer_count_label, 0)
        composer_layout.addLayout(control_row)

        self.composer_text = QTextEdit()
        self.composer_text.setMinimumHeight(160)
        self.composer_text.setPlaceholderText(qt_t("qwen3_tts.compose_hint", "Enter text to generate audio..."))
        self.composer_text.setStyleSheet(
            f"""
            QTextEdit {{
                background: {p.field_bg};
                border: 1px solid {p.control_border};
                border-radius: 16px;
                padding: 12px 14px;
            }}
            QTextEdit:focus {{
                border: 1px solid {p.chip_border};
            }}
            """
        )
        composer_layout.addWidget(self.composer_text, 1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(10)
        self.save_message_btn = QPushButton(qt_t("qwen3_tts.save_message", "Save Selected"))
        self.save_message_btn.setProperty("buttonRole", "pill")
        self.update_message_btn = QPushButton(qt_t("qwen3_tts.update_message", "Update Current"))
        self.update_message_btn.setProperty("buttonRole", "pill")
        self.delete_message_btn = QPushButton(qt_t("qwen3_tts.delete_message", "Delete Message"))
        self.delete_message_btn.setProperty("buttonRole", "pill")
        self.generate_selected_btn = QPushButton("⟳ Generate This")
        self._accent_generate_button(self.generate_selected_btn)
        btn_row.addWidget(self.save_message_btn)
        btn_row.addWidget(self.update_message_btn)
        btn_row.addWidget(self.delete_message_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.generate_selected_btn, 0)
        composer_layout.addLayout(btn_row)
        root.addWidget(composer_card, 1)
        return container

    def _build_profile_dialog(self) -> None:
        self.profile_dialog = Qwen3TTSProfileDialog(self, self._accent_generate_button)
        self.profile_dialog.mode_combo.currentTextChanged.connect(self._on_editor_mode_changed)

    def _bind_actions(self) -> None:
        self.message_list.itemSelectionChanged.connect(self._on_message_selected)
        self.message_list.itemDoubleClicked.connect(self._on_message_double_clicked)
        self.composer_profile_combo.currentTextChanged.connect(self._on_composer_prefs_changed)
        self.composer_tone_combo.currentTextChanged.connect(self._on_composer_prefs_changed)
        self.composer_language_combo.currentTextChanged.connect(self._on_composer_prefs_changed)
        self.composer_device_combo.currentTextChanged.connect(self._on_composer_prefs_changed)
        self.composer_text.textChanged.connect(self._refresh_composer_metrics)
        self.save_message_btn.clicked.connect(self._save_message)
        self.update_message_btn.clicked.connect(self._update_selected_message)
        self.delete_message_btn.clicked.connect(self._delete_selected_message)
        self.generate_selected_btn.clicked.connect(self._generate_selected)
        self.generate_all_btn.clicked.connect(self._generate_all)
        self.rerun_btn.clicked.connect(self._regenerate_selected)
        self.play_btn.clicked.connect(self._play_selected_output)
        self.open_file_btn.clicked.connect(self._open_selected_output)
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        self.profile_dialog.ref_audio_browse_btn.clicked.connect(self._browse_ref_audio)
        self.profile_dialog.profile_combo.currentTextChanged.connect(self._on_editor_profile_selected)
        self.profile_dialog.save_btn.clicked.connect(self._save_editor_profile)
        self.profile_dialog.cancel_btn.clicked.connect(self.profile_dialog.close)
        self.profile_dialog.new_profile_btn.clicked.connect(self._start_new_profile)
        self.profile_dialog.delete_profile_btn.clicked.connect(self._delete_profile)
        self.edit_profile_btn.clicked.connect(self._open_profile_dialog)
        self.open_output_btn.clicked.connect(self._reveal_output_dir)

    def _refresh_all(self) -> None:
        self._refresh_profile_choices()
        self._refresh_composer_preferences()
        self._refresh_messages()
        self._load_editor_profile()
        self._sync_message_details()
        self._refresh_composer_metrics()
        self._refresh_runtime_status()

    def _refresh_runtime_status(self) -> None:
        self.runtime_status_badge.setText(self.service.state.status_text)
        self.asset_count_badge.setText(qt_t("comfyui.qt_shell.asset_count", "{count} messages", count=len(self.service.messages)))

    def _refresh_composer_preferences(self) -> None:
        self._updating_ui = True
        self.composer_tone_combo.setCurrentText(self.service.state.selected_tone)
        self.composer_language_combo.setCurrentText(self.service.state.selected_language)
        self.composer_device_combo.setCurrentText(self.service.state.selected_device)
        self._updating_ui = False

    def _refresh_composer_metrics(self) -> None:
        length = len(self.composer_text.toPlainText())
        self.composer_count_label.setText(f"{length} / 2000 chars")

    def _refresh_profile_choices(self) -> None:
        profiles = self.service.get_profile_choices()
        current_profile = self.service.state.selected_profile
        current_editor = self.profile_dialog.current_profile_name() if hasattr(self, "profile_dialog") else current_profile
        self._updating_ui = True
        self.composer_profile_combo.blockSignals(True)
        self.composer_profile_combo.clear()
        self.composer_profile_combo.addItems(profiles)
        if current_profile in profiles:
            self.composer_profile_combo.setCurrentText(current_profile)
        elif profiles:
            self.composer_profile_combo.setCurrentIndex(0)
            self.service.state.selected_profile = profiles[0]
        if hasattr(self, "profile_dialog"):
            self.profile_dialog.set_profile_choices(profiles, current_profile, current_editor)
        self.composer_profile_combo.blockSignals(False)
        self._updating_ui = False

    def _refresh_messages(self) -> None:
        selected_id = self.service.state.selected_message_id
        current_index = self.message_list.currentRow()
        self.message_list.blockSignals(True)
        self.message_list.clear()
        profiles = self.service.get_profile_choices()
        for message in self.service.messages:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, message.id)
            item.setToolTip(f"id: {message.id}\nstatus: {message.status}\ntext: {message.text}")
            if message.output:
                item.setToolTip(f"{item.toolTip()}\noutput: {message.output}")
            self.message_list.addItem(item)
            bubble = MessageBubbleWidget(
                message,
                profiles,
                selected=message.id == selected_id,
                expanded=message.id == self._expanded_message_id,
                media_enabled=self.player is not None,
            )
            bubble.select_requested.connect(self._select_message_from_bubble)
            bubble.expand_requested.connect(self._toggle_message_expand)
            bubble.apply_requested.connect(self._apply_message_changes)
            bubble.play_requested.connect(self._play_message_output)
            bubble.open_requested.connect(self._open_message_output)
            bubble.profile_requested.connect(self._open_profile_from_message)
            bubble.regenerate_requested.connect(self._regenerate_message)
            bubble.delete_requested.connect(self._delete_message_by_id)
            item.setSizeHint(bubble.sizeHint())
            self.message_list.setItemWidget(item, bubble)
        self.message_count_label.setText(str(len(self.service.messages)))
        if self.message_list.count() == 0:
            self.service.state.selected_message_id = None
            self._expanded_message_id = None
        else:
            target_row = 0
            if selected_id is not None:
                for row in range(self.message_list.count()):
                    item = self.message_list.item(row)
                    if item is not None and item.data(Qt.UserRole) == selected_id:
                        target_row = row
                        break
            elif current_index >= 0 and current_index < self.message_list.count():
                target_row = current_index
            self.message_list.setCurrentRow(target_row)
        self.message_list.blockSignals(False)
        self._refresh_message_widgets()
        self._refresh_result_panel()

    def _refresh_message_widgets(self) -> None:
        selected_id = self.service.state.selected_message_id
        profiles = self.service.get_profile_choices()
        for row in range(self.message_list.count()):
            item = self.message_list.item(row)
            if item is None:
                continue
            message_id = item.data(Qt.UserRole)
            message = self.service.message_by_id(message_id)
            if message is None:
                continue
            bubble = MessageBubbleWidget(
                message,
                profiles,
                selected=message.id == selected_id,
                expanded=message.id == self._expanded_message_id,
                media_enabled=self.player is not None,
            )
            bubble.select_requested.connect(self._select_message_from_bubble)
            bubble.expand_requested.connect(self._toggle_message_expand)
            bubble.apply_requested.connect(self._apply_message_changes)
            bubble.play_requested.connect(self._play_message_output)
            bubble.open_requested.connect(self._open_message_output)
            bubble.profile_requested.connect(self._open_profile_from_message)
            bubble.regenerate_requested.connect(self._regenerate_message)
            bubble.delete_requested.connect(self._delete_message_by_id)
            item.setSizeHint(bubble.sizeHint())
            self.message_list.setItemWidget(item, bubble)

    def _sync_message_details(self) -> None:
        selected = self.service.selected_message()
        self._updating_ui = True
        if selected is None:
            self.composer_text.setPlainText("")
            self._updating_ui = False
            self._refresh_message_widgets()
            self._refresh_result_panel()
            return
        if selected.profile in self.service.get_profile_choices():
            self.composer_profile_combo.setCurrentText(selected.profile)
        if selected.tone in [str(key) for key in TONE_PRESETS.keys()]:
            self.composer_tone_combo.setCurrentText(selected.tone)
        self.composer_text.setPlainText(selected.text)
        self._updating_ui = False
        self._refresh_message_widgets()
        self._refresh_composer_metrics()
        self._refresh_result_panel()

    def _refresh_result_panel(self) -> None:
        self._sync_result_button_states()
        message = self.service.selected_message()
        if message is None:
            self.selected_message_badge.setText("No message selected")
            self.result_status_label.setText("No message selected")
            self.result_path_label.setText("")
            self.result_file_label.setText("")
            return
        self.selected_message_badge.setText(f"{message.profile} · {status_text(message.status)}")
        self.result_status_label.setText(f"Status: {status_text(message.status)}")
        if message.output:
            output_path = Path(message.output)
            self.result_path_label.setText(f"Output: {output_path.parent}")
            self.result_file_label.setText(f"File: {output_path.name}")
            self.play_btn.setEnabled(self.player is not None)
            self.open_file_btn.setEnabled(True)
            self.rerun_btn.setEnabled(True)
        else:
            self.result_path_label.setText("Output: No output yet")
            self.result_file_label.setText("")
            self.play_btn.setEnabled(False)
            self.open_file_btn.setEnabled(False)
            self.rerun_btn.setEnabled(True)

    def _sync_result_button_states(self) -> None:
        is_selected = self.service.selected_message() is not None
        has_media = self.player is not None
        self.save_message_btn.setEnabled(not self._is_running)
        self.update_message_btn.setEnabled(not self._is_running and is_selected)
        self.delete_message_btn.setEnabled(not self._is_running and is_selected)
        self.generate_selected_btn.setEnabled(not self._is_running and is_selected)
        self.generate_all_btn.setEnabled(not self._is_running)
        self.play_btn.setEnabled(not self._is_running and has_media)
        self.rerun_btn.setEnabled(not self._is_running and is_selected)
        self.open_file_btn.setEnabled(not self._is_running and is_selected)

    def _on_message_selected(self) -> None:
        if self._updating_ui:
            return
        item = self.message_list.currentItem()
        if item is None:
            self.service.set_selected_message(None)
            self._sync_message_details()
            return
        message_id = item.data(Qt.UserRole)
        self.service.set_selected_message(message_id)
        self._sync_message_details()

    def _select_message_from_bubble(self, message_id: str) -> None:
        self.service.set_selected_message(message_id)
        for row in range(self.message_list.count()):
            item = self.message_list.item(row)
            if item is not None and item.data(Qt.UserRole) == message_id:
                self.message_list.setCurrentRow(row)
                break
        self._sync_message_details()

    def _toggle_message_expand(self, message_id: str) -> None:
        self._expanded_message_id = None if self._expanded_message_id == message_id else message_id
        self._refresh_message_widgets()

    def _apply_message_changes(self, message_id: str, profile: str, tone: str, text: str) -> None:
        self.service.update_message(message_id, profile=profile, tone=tone, text=text)
        self.service.set_selected_message(message_id)
        self.service.state.selected_profile = profile
        self.service.state.selected_tone = tone
        self.service.state.status_text = "Bubble changes applied."
        self._refresh_profile_choices()
        self._sync_message_details()
        self._refresh_messages()
        self._refresh_runtime_status()

    def _play_message_output(self, message_id: str) -> None:
        self.service.set_selected_message(message_id)
        self._sync_message_details()
        self._play_selected_output()

    def _open_message_output(self, message_id: str) -> None:
        self.service.set_selected_message(message_id)
        self._sync_message_details()
        self._open_selected_output()

    def _open_profile_from_message(self, message_id: str) -> None:
        self.service.set_selected_message(message_id)
        message = self.service.message_by_id(message_id)
        if message is not None:
            self.profile_dialog.select_profile(message.profile)
        self._open_profile_dialog()

    def _regenerate_message(self, message_id: str) -> None:
        self.service.set_selected_message(message_id)
        self._expanded_message_id = message_id
        self._sync_message_details()
        self._run_generation([message_id])

    def _delete_message_by_id(self, message_id: str) -> None:
        if self._expanded_message_id == message_id:
            self._expanded_message_id = None
        self.service.delete_message(message_id)
        if self.service.messages:
            self.service.set_selected_message(self.service.messages[0].id)
        self.service.state.status_text = "Message deleted."
        self._refresh_messages()
        self._refresh_runtime_status()

    def _on_message_double_clicked(self, item: QListWidgetItem) -> None:
        if item is None:
            return
        message_id = item.data(Qt.UserRole)
        self._toggle_message_expand(message_id)

    def _on_composer_prefs_changed(self) -> None:
        if self._updating_ui:
            return
        self.service.set_composer_preferences(
            self.composer_profile_combo.currentText(),
            self.composer_tone_combo.currentText(),
            self.composer_language_combo.currentText(),
            self.composer_device_combo.currentText(),
            self.service.state.output_dir or str(Path.home() / "Documents"),
        )

    def _sync_output_settings(self) -> None:
        output_dir = self.service.state.output_dir or str(Path.home() / "Documents")
        self.service.set_output_dir(output_dir)

    def _save_message(self) -> None:
        text = self.composer_text.toPlainText().strip()
        if not text:
            self.service.state.status_text = "Message text is required."
            self._refresh_runtime_status()
            return
        self._sync_output_settings()
        try:
            message = self.service.upsert_message(text)
        except ValueError as exc:
            self.service.state.status_text = str(exc)
            self._refresh_runtime_status()
            return
        message.profile = self.composer_profile_combo.currentText()
        message.tone = self.composer_tone_combo.currentText()
        self.service.set_selected_message(message.id)
        self.service.state.status_text = "Message saved."
        self._refresh_messages()
        self._scroll_to_message(message.id)

    def _update_selected_message(self) -> None:
        message = self.service.selected_message()
        if message is None:
            self._save_message()
            return
        self._sync_output_settings()
        self.service.update_message(
            message.id,
            profile=self.composer_profile_combo.currentText(),
            tone=self.composer_tone_combo.currentText(),
            text=self.composer_text.toPlainText(),
        )
        self.service.state.status_text = "Message updated."
        self._refresh_messages()

    def _delete_selected_message(self) -> None:
        message = self.service.selected_message()
        if message is None:
            return
        if self._expanded_message_id == message.id:
            self._expanded_message_id = None
        self.service.delete_message(message.id)
        self.service.state.status_text = "Message deleted."
        if self.service.messages:
            self.service.set_selected_message(self.service.messages[0].id)
        self._refresh_messages()

    def _scroll_to_message(self, message_id: str) -> None:
        for row in range(self.message_list.count()):
            item = self.message_list.item(row)
            if item is not None and item.data(Qt.UserRole) == message_id:
                self.message_list.setCurrentRow(row)
                return

    def _generate_selected(self) -> None:
        message = self.service.selected_message()
        if message is None:
            self.service.state.status_text = "Select a message first."
            self._refresh_runtime_status()
            return
        self._expanded_message_id = message.id
        self._run_generation([message.id])

    def _generate_all(self) -> None:
        self._expanded_message_id = None
        self._run_generation([message.id for message in self.service.messages])

    def _regenerate_selected(self) -> None:
        self._generate_selected()

    def _run_generation(self, target_ids: list[str]) -> None:
        if self._is_running:
            return
        if not target_ids:
            self.service.state.status_text = "No message lines found."
            self._refresh_runtime_status()
            return
        self._sync_output_settings()
        self._is_running = True
        self._sync_result_button_states()
        self.service.state.status_text = "Running..."
        self._refresh_runtime_status()

        def worker() -> None:
            ok, _payload, message, _active = self.service.run_jobs(target_ids, on_line=self._bridge.progress.emit)
            QTimer.singleShot(0, lambda: self._bridge.done.emit(ok, message))

        threading.Thread(target=worker, daemon=True).start()

    def _on_generation_progress(self, line: str) -> None:
        text = line.strip()
        if not text:
            return
        self.service.state.status_text = text
        QTimer.singleShot(0, self._refresh_runtime_status)

    def _on_generation_done(self, ok: bool, message: str) -> None:
        self._is_running = False
        if not message:
            message = "Done." if ok else "Generation failed."
        self.service.state.status_text = message
        self._sync_result_button_states()
        self._refresh_messages()
        self._refresh_result_panel()
        self._refresh_runtime_status()

    def _play_selected_output(self) -> None:
        if self.player is None:
            self.service.state.status_text = "Media playback is not available."
            self._refresh_runtime_status()
            return
        message = self.service.selected_message()
        if message is None or not message.output:
            self.service.state.status_text = "No output file."
            self._refresh_runtime_status()
            return
        output_path = Path(message.output)
        if not output_path.exists():
            self.service.state.status_text = "Output file is missing."
            self._refresh_runtime_status()
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(output_path)))
        self.player.play()
        self.service.state.status_text = "Playing."
        self._refresh_runtime_status()

    def _open_selected_output(self) -> None:
        message = self.service.selected_message()
        if message is None or not message.output:
            self.service.state.status_text = "No output to open."
            self._refresh_runtime_status()
            return
        self._open_path(Path(message.output), "file")

    def _open_output_folder(self) -> None:
        message = self.service.selected_message()
        if message is None:
            self.service.state.status_text = "No message selected."
            self._refresh_runtime_status()
            return
        if message.output:
            self._open_path(Path(message.output).parent, "folder")
            return
        self._open_path(self.service.active_output_dir(), "folder")

    def _reveal_output_dir(self) -> None:
        self._sync_output_settings()
        self.service.reveal_output_dir()

    def _open_path(self, target: Path, mode: str) -> None:
        try:
            target_str = str(target)
            if mode == "folder":
                target.mkdir(parents=True, exist_ok=True)
            os.startfile(target_str)  # noqa: PTH118
            self.service.state.status_text = "Opened."
        except Exception:
            self.service.state.status_text = "Failed to open target."
        self._refresh_runtime_status()

    def _start_new_profile(self) -> None:
        profile = self.service.add_profile_template()
        self._editing_profile_id = profile["id"]
        self.profile_dialog.set_template(profile)
        self._refresh_profile_quality()

    def _load_editor_profile(self) -> None:
        self._updating_ui = True
        name = self.profile_dialog.current_profile_name() or self.service.state.selected_profile
        profile = self.service.profile_by_name(name)
        self._editing_profile_id = profile.get("id") if profile else None
        if not profile:
            self._updating_ui = False
            return
        self.profile_dialog.load_profile(profile)
        self._updating_ui = False
        self._on_editor_mode_changed(self.profile_dialog.mode_combo.currentText())
        self._refresh_profile_quality()

    def _on_editor_profile_selected(self) -> None:
        if self._updating_ui:
            return
        self._load_editor_profile()

    def _on_editor_mode_changed(self, mode: str) -> None:
        self.profile_dialog.set_mode_visibility(mode)
        self._refresh_profile_quality()

    def _refresh_profile_quality(self) -> None:
        profile_name = self.profile_dialog.current_profile_name()
        profile = self.service.profile_by_name(profile_name)
        if profile is None or profile.get("mode") != "voice_clone":
            self.profile_dialog.set_quality_message("")
            return
        quality = self.service.profile_quality(profile_name)
        if quality is None:
            self.profile_dialog.set_quality_message("")
            return
        _status, message = quality
        self.profile_dialog.set_quality_message(message)

    def _browse_ref_audio(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            APP_TITLE,
            self.profile_dialog.browse_root(),
            "Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg *.aac)",
        )
        if file_path:
            self.profile_dialog.ref_audio.setText(file_path)
            self._refresh_profile_quality()

    def _open_profile_dialog(self) -> None:
        selected = self.service.selected_message()
        if selected is not None:
            self.profile_dialog.select_profile(selected.profile)
        self._load_editor_profile()
        self.profile_dialog.show()
        self.profile_dialog.raise_()
        self.profile_dialog.activateWindow()

    def _save_editor_profile(self) -> None:
        payload = self.profile_dialog.profile_payload()
        name = payload["name"] or "Profile"
        mode = payload["mode"]
        speaker = payload["speaker"]
        instruct = payload["instruct"]
        ref_audio = payload["ref_audio"]
        ref_text = payload["ref_text"]
        if not name:
            self.service.state.status_text = "Profile name is required."
            self._refresh_runtime_status()
            return
        if mode == "voice_clone" and not ref_audio:
            self.service.state.status_text = "Clone profile requires reference audio."
            self._refresh_runtime_status()
            return
        if mode == "voice_clone" and ref_audio and not Path(ref_audio).exists():
            self.service.state.status_text = "Reference audio file does not exist."
            self._refresh_runtime_status()
            return
        if mode == "voice_design" and not instruct:
            self.service.state.status_text = "Voice design profile requires a description."
            self._refresh_runtime_status()
            return
        ok = self.service.save_profile(self._editing_profile_id, name, mode, speaker, instruct, ref_audio, ref_text)
        if not ok:
            self.service.state.status_text = "Profile name already exists."
            self._refresh_runtime_status()
            return
        self.service.state.selected_profile = name
        self.service.state.inspector_profile_name = name
        self._refresh_profile_choices()
        self.profile_dialog.select_profile(name)
        self._load_editor_profile()
        self._refresh_messages()
        self.service.state.status_text = "Profile saved."
        self.profile_dialog.close()
        self._refresh_runtime_status()

    def _delete_profile(self) -> None:
        name = self.profile_dialog.current_profile_name()
        if not name:
            return
        ok = self.service.delete_profile(name)
        if not ok:
            self.service.state.status_text = "At least one profile must remain."
            self._refresh_runtime_status()
            return
        self._refresh_profile_choices()
        self._load_editor_profile()
        self._refresh_messages()
        self.service.state.status_text = "Profile deleted."
        self._refresh_runtime_status()

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


def start_app(targets: list[str] | None = None, app_root: str | Path | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    target: Path | None = None
    if targets:
        candidate = Path(targets[0])
        if candidate.exists():
            target = candidate
    service = Qwen3TTSQtService(target)
    root = Path(app_root) if app_root else Path(__file__).resolve().parents[3] / "ai" / APP_ID
    window = Qwen3TTSQtWindow(service, root, targets)
    window.show()
    return app.exec()
