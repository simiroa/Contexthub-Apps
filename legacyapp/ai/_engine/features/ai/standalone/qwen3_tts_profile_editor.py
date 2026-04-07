from __future__ import annotations

from pathlib import Path

from features.ai.standalone.qwen3_tts_service import SUPPORTED_SPEAKERS
from contexthub.ui.qt.shell import qt_t

try:
    from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for qwen3_tts.") from exc


class Qwen3TTSProfileDialog(QDialog):
    def __init__(self, parent, accent_button) -> None:
        super().__init__(parent)
        self.setWindowTitle("Profile Editor")
        self.resize(720, 720)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.profile_combo.setObjectName("presetCombo")
        header_row.addWidget(self.profile_combo, 1)
        self.new_profile_btn = QPushButton(qt_t("qwen3_tts.new_profile", "New Profile"))
        self.new_profile_btn.setProperty("buttonRole", "pill")
        self.delete_profile_btn = QPushButton(qt_t("qwen3_tts.delete_profile", "Delete Profile"))
        self.delete_profile_btn.setProperty("buttonRole", "pill")
        header_row.addWidget(self.new_profile_btn)
        header_row.addWidget(self.delete_profile_btn)
        layout.addLayout(header_row)

        self.profile_name = QLineEdit()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["custom_voice", "voice_clone", "voice_design"])
        self.speaker_combo = QComboBox()
        self.speaker_combo.addItems(SUPPORTED_SPEAKERS)
        self.instruct_edit = QTextEdit()
        self.instruct_edit.setMinimumHeight(100)
        self.ref_audio = QLineEdit()
        self.ref_audio_browse_btn = QPushButton(qt_t("qwen3_tts.browse", "Browse"))
        self.ref_audio_browse_btn.setProperty("buttonRole", "pill")
        self.ref_text = QTextEdit()
        self.ref_text.setMinimumHeight(90)
        self.profile_quality = QLabel("")
        self.profile_quality.setWordWrap(True)
        self.profile_quality.setObjectName("muted")

        self.profile_name_label = QLabel("Profile Name")
        self.mode_label = QLabel("Mode")
        self.speaker_label = QLabel("Speaker")
        self.instruction_label = QLabel("Instruction")
        self.ref_audio_label = QLabel("Clone Ref Audio")
        self.ref_text_label = QLabel("Clone Ref Text")
        layout.addWidget(self.profile_name_label)
        layout.addWidget(self.profile_name)
        layout.addWidget(self.mode_label)
        layout.addWidget(self.mode_combo)
        layout.addWidget(self.speaker_label)
        layout.addWidget(self.speaker_combo)
        layout.addWidget(self.instruction_label)
        layout.addWidget(self.instruct_edit)

        ref_audio_row = QHBoxLayout()
        ref_audio_row.addWidget(self.ref_audio, 1)
        ref_audio_row.addWidget(self.ref_audio_browse_btn)
        layout.addWidget(self.ref_audio_label)
        layout.addLayout(ref_audio_row)
        layout.addWidget(self.ref_text_label)
        layout.addWidget(self.ref_text)
        layout.addWidget(self.profile_quality)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.cancel_btn = QPushButton(qt_t("common.cancel", "Cancel"))
        self.cancel_btn.setProperty("buttonRole", "pill")
        self.save_btn = QPushButton("Save Profile")
        accent_button(self.save_btn)
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.save_btn)
        layout.addLayout(footer)

    def set_profile_choices(self, profiles: list[str], current_profile: str, current_editor: str | None = None) -> None:
        current_editor = current_editor or current_profile
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(profiles)
        if current_editor in profiles:
            self.profile_combo.setCurrentText(current_editor)
        elif current_profile in profiles:
            self.profile_combo.setCurrentText(current_profile)
        self.profile_combo.blockSignals(False)

    def load_profile(self, profile: dict) -> None:
        self.profile_name.setText(profile.get("name", ""))
        self.mode_combo.setCurrentText(profile.get("mode", "custom_voice"))
        self.speaker_combo.setCurrentText(profile.get("speaker", SUPPORTED_SPEAKERS[0]))
        self.instruct_edit.setPlainText(profile.get("instruct", ""))
        self.ref_audio.setText(profile.get("ref_audio", ""))
        self.ref_text.setPlainText(profile.get("ref_text", ""))

    def set_template(self, profile: dict) -> None:
        self.load_profile(profile)
        self.ref_audio.clear()
        self.ref_text.clear()

    def profile_payload(self) -> dict[str, str]:
        return {
            "name": self.profile_name.text().strip(),
            "mode": self.mode_combo.currentText(),
            "speaker": self.speaker_combo.currentText(),
            "instruct": self.instruct_edit.toPlainText().strip(),
            "ref_audio": self.ref_audio.text().strip(),
            "ref_text": self.ref_text.toPlainText().strip(),
        }

    def set_mode_visibility(self, mode: str) -> None:
        is_clone = mode == "voice_clone"
        is_design = mode == "voice_design"
        self.speaker_label.setVisible(not is_design)
        self.speaker_combo.setVisible(not is_design)
        self.ref_audio_label.setVisible(is_clone)
        self.ref_audio.setVisible(is_clone)
        self.ref_audio_browse_btn.setVisible(is_clone)
        self.ref_text_label.setVisible(is_clone)
        self.ref_text.setVisible(is_clone)

    def set_quality_message(self, message: str) -> None:
        self.profile_quality.setText(message)

    def current_profile_name(self) -> str:
        return self.profile_combo.currentText().strip()

    def select_profile(self, name: str) -> None:
        self.profile_combo.setCurrentText(name)

    def browse_root(self) -> str:
        return str(Path.home())
