from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings

from features.ai.standalone.qwen3_tts_generation_service import EMPTY_TARGET_MESSAGE, Qwen3TTSGenerationService
from features.ai.standalone.qwen3_tts_message_service import QTTSMessage, Qwen3TTSMessageService
from features.ai.standalone.qwen3_tts_profile_service import Qwen3TTSProfileService
from features.ai.standalone.qwen3_tts_service import SUPPORTED_LANGUAGES, profile_names


DEFAULT_TEXT = "Hello from ContextHub. This is a quick voice test."
INVALID_TEXT_MESSAGE = "Text is required."


@dataclass
class QTTSUiState:
    selected_message_id: str | None = None
    selected_profile: str = ""
    selected_tone: str = "natural"
    selected_language: str = "Auto"
    selected_device: str = "cuda"
    output_dir: str = ""
    status_text: str = "Ready"
    inspector_profile_name: str | None = None


class Qwen3TTSQtService:
    def __init__(self, target_path: Path | None = None) -> None:
        self._settings = QSettings("Contexthub", "qwen3_tts")
        self._message_service = Qwen3TTSMessageService(DEFAULT_TEXT)
        self._profile_service = Qwen3TTSProfileService()
        self._generation_service = Qwen3TTSGenerationService()

        self.profiles = self._profile_service.load_profiles()
        self.messages, self.profiles = self._message_service.load_initial_messages(target_path, self.profiles)

        state_name = profile_names(self.profiles)[0]
        self.state = QTTSUiState()
        pref_profile = self._settings.value("profile_name", state_name, str) or state_name
        names = self.get_profile_choices()
        if pref_profile not in names:
            pref_profile = names[0]
        self.state.selected_profile = pref_profile
        self.state.selected_tone = self._settings.value("tone", "natural", str) or "natural"
        self.state.selected_language = self._settings.value("language", "Auto", str) or "Auto"
        self.state.selected_device = self._settings.value("device", "cuda", str) or "cuda"
        self.state.output_dir = self._settings.value("output_dir", str(Path.home() / "Documents"), str) or str(Path.home() / "Documents")
        if self.state.selected_language not in SUPPORTED_LANGUAGES:
            self.state.selected_language = "Auto"
        self.state.inspector_profile_name = self.state.selected_profile
        self._sync_selected_from_messages()

    def save_prefs(self) -> None:
        self._settings.setValue("profile_name", self.state.selected_profile)
        self._settings.setValue("tone", self.state.selected_tone)
        self._settings.setValue("language", self.state.selected_language)
        self._settings.setValue("device", self.state.selected_device)
        self._settings.setValue("output_dir", self.state.output_dir)

    def _sync_selected_from_messages(self) -> None:
        self.state.selected_message_id = self._message_service.sync_selected_message_id(self.messages, self.state.selected_message_id)

    def set_selected_message(self, message_id: str | None) -> None:
        if message_id is None:
            self.state.selected_message_id = None
            return
        if self.message_by_id(message_id) is not None:
            self.state.selected_message_id = message_id

    def selected_message(self) -> QTTSMessage | None:
        return self.message_by_id(self.state.selected_message_id)

    def selected_profile(self) -> dict | None:
        return self.profile_by_name(self.state.selected_profile)

    def get_profile_choices(self) -> list[str]:
        return self._profile_service.get_profile_choices(self.profiles)

    def profile_by_name(self, name: str) -> dict:
        return self._profile_service.profile_by_name(self.profiles, name)

    def profile_quality(self, name: str):
        return self._profile_service.profile_quality(self.profiles, name)

    def message_by_id(self, message_id: str | None) -> QTTSMessage | None:
        return self._message_service.message_by_id(self.messages, message_id)

    def active_output_dir(self) -> Path:
        if self.state.output_dir:
            return Path(self.state.output_dir)
        return Path.home() / "Documents"

    def upsert_message(self, text: str, message_id: str | None = None) -> QTTSMessage:
        message, self.messages = self._message_service.upsert_message(
            self.messages,
            self.state.selected_profile,
            self.state.selected_tone,
            text,
            message_id,
        )
        self.state.selected_message_id = message.id
        self.save_prefs()
        return message

    def delete_message(self, message_id: str) -> None:
        self.messages = self._message_service.delete_message(self.messages, message_id)
        if self.state.selected_message_id == message_id:
            self.state.selected_message_id = self.messages[0].id if self.messages else None
        self._sync_selected_from_messages()

    def update_message(self, message_id: str, *, profile: str | None = None, tone: str | None = None, text: str | None = None) -> None:
        self._message_service.update_message(self.messages, message_id, profile=profile, tone=tone, text=text)
        self.save_prefs()

    def set_composer_preferences(self, profile: str, tone: str, language: str, device: str, output_dir: str) -> None:
        self.state.selected_profile = profile
        self.state.selected_tone = tone
        self.state.selected_language = language
        self.state.selected_device = device
        self.state.output_dir = output_dir
        self.save_prefs()

    def set_output_dir(self, output_dir: str) -> None:
        self.state.output_dir = output_dir
        self.save_prefs()

    def add_profile_template(self) -> dict:
        return self._profile_service.add_profile_template(self.profiles)

    def save_profile(
        self,
        profile_id: str | None,
        name: str,
        mode: str,
        speaker: str,
        instruct: str,
        ref_audio: str,
        ref_text: str,
    ) -> bool:
        ok, self.profiles = self._profile_service.save_profile(
            self.profiles,
            profile_id,
            name,
            mode,
            speaker,
            instruct,
            ref_audio,
            ref_text,
        )
        if not ok:
            return False
        self.state.selected_profile = name.strip() or "Profile"
        self.state.inspector_profile_name = self.state.selected_profile
        self.save_prefs()
        return True

    def profile_to_dict(self, profile_id: str) -> dict | None:
        return self._profile_service.profile_to_dict(self.profiles, profile_id)

    def delete_profile(self, name: str) -> bool:
        ok, self.profiles = self._profile_service.delete_profile(self.profiles, name)
        if not ok:
            return False
        names = self.get_profile_choices()
        if self.state.selected_profile == name:
            self.state.selected_profile = names[0]
            self.state.inspector_profile_name = self.state.selected_profile
        self.save_prefs()
        return True

    def build_jobs(self, target_ids: list[str]) -> tuple[list[dict], list[QTTSMessage]]:
        return self._generation_service.build_jobs(
            self.messages,
            self.profiles,
            self.state.selected_device,
            self.state.selected_language,
            target_ids,
        )

    def run_jobs(self, target_ids: list[str], on_line=None) -> tuple[bool, dict | None, str, list[QTTSMessage]]:
        try:
            return self._generation_service.run_jobs(
                self.messages,
                self.profiles,
                self.state.selected_device,
                self.state.selected_language,
                self.active_output_dir(),
                target_ids,
                on_line=on_line,
            )
        except ValueError as exc:
            return False, None, str(exc), []
        except Exception:
            return False, None, EMPTY_TARGET_MESSAGE, []

    def reveal_output_dir(self) -> None:
        self._generation_service.reveal_output_dir(self.active_output_dir())
