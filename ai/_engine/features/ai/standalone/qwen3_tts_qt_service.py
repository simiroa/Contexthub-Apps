from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings

from features.ai.standalone.qwen3_tts_service import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_SPEAKERS,
    TONE_PRESETS,
    build_job,
    clone_quality_status,
    ensure_unique_profile_name,
    load_profiles,
    prefill_messages,
    profile_by_name,
    profile_names,
    run_jobs_sync,
    save_profiles,
)


DEFAULT_TEXT = "Hello from ContextHub. This is a quick voice test."
EMPTY_TARGET_MESSAGE = "No valid dialogue lines to generate."
RUN_SUCCESS_MESSAGE = "Speech generated successfully."
RUN_FAIL_MESSAGE = "Generation failed."
INVALID_TEXT_MESSAGE = "Text is required."
EMPTY_LINES_MESSAGE = "No valid dialogue lines to generate."


@dataclass
class QTTSMessage:
    id: str
    role: str
    profile: str
    tone: str
    text: str
    status: str = "ready"
    output: str = ""


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
        self.profiles = load_profiles()

        safe_target = target_path if target_path and target_path.exists() else None
        messages, self.profiles = prefill_messages(safe_target, self.profiles, DEFAULT_TEXT)
        self.messages = [QTTSMessage(**item) for item in messages]

        state_name = profile_names(self.profiles)[0]
        self.state = QTTSUiState()
        pref_profile = self._settings.value("profile_name", state_name, str) or state_name
        names = profile_names(self.profiles)
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

    @staticmethod
    def _slug(text: str) -> str:
        key = re.sub(r"[^A-Za-z0-9]+", "_", text.strip().lower())
        if not key:
            return "message"
        return key.strip("_")

    def save_prefs(self) -> None:
        self._settings.setValue("profile_name", self.state.selected_profile)
        self._settings.setValue("tone", self.state.selected_tone)
        self._settings.setValue("language", self.state.selected_language)
        self._settings.setValue("device", self.state.selected_device)
        self._settings.setValue("output_dir", self.state.output_dir)

    def _sync_selected_from_messages(self) -> None:
        if self.messages and self.state.selected_message_id is None:
            self.state.selected_message_id = self.messages[0].id

    def set_selected_message(self, message_id: str | None) -> None:
        if message_id is None:
            self.state.selected_message_id = None
            return
        if self.message_by_id(message_id) is not None:
            self.state.selected_message_id = message_id

    def selected_message(self) -> QTTSMessage | None:
        if self.state.selected_message_id is None:
            return None
        return self.message_by_id(self.state.selected_message_id)

    def selected_profile(self) -> dict | None:
        return self.profile_by_name(self.state.selected_profile)

    def get_profile_choices(self) -> list[str]:
        return profile_names(self.profiles)

    def profile_by_name(self, name: str) -> dict:
        return profile_by_name(self.profiles, name)

    def profile_quality(self, name: str):
        return clone_quality_status(self.profile_by_name(name))

    def message_by_id(self, message_id: str) -> QTTSMessage | None:
        for message in self.messages:
            if message.id == message_id:
                return message
        return None

    def active_output_dir(self) -> Path:
        if self.state.output_dir:
            return Path(self.state.output_dir)
        return Path.home() / "Documents"

    def upsert_message(self, text: str, message_id: str | None = None) -> QTTSMessage:
        text = (text or "").strip()
        if not text:
            raise ValueError(INVALID_TEXT_MESSAGE)

        if message_id:
            target = self.message_by_id(message_id)
            if target:
                target.text = text
                target.profile = self.state.selected_profile
                target.role = self.state.selected_profile
                target.tone = self.state.selected_tone
                target.status = "ready"
                target.output = target.output
                return target

        message = QTTSMessage(
            id=f"msg_{len(self.messages)+1}",
            role=self.state.selected_profile,
            profile=self.state.selected_profile,
            tone=self.state.selected_tone,
            text=text,
        )
        self.messages.append(message)
        self.state.selected_message_id = message.id
        self.save_prefs()
        return message

    def delete_message(self, message_id: str) -> None:
        self.messages = [message for message in self.messages if message.id != message_id]
        if self.state.selected_message_id == message_id:
            self.state.selected_message_id = self.messages[0].id if self.messages else None
        self._sync_selected_from_messages()

    def update_message(self, message_id: str, *, profile: str | None = None, tone: str | None = None, text: str | None = None) -> None:
        message = self.message_by_id(message_id)
        if message is None:
            return
        if profile is not None:
            message.profile = profile
        if tone is not None:
            message.tone = tone
        if text is not None:
            message.text = text.strip()
        message.status = "ready"
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
        return {
            "id": f"profile_{len(self.profiles) + 1}",
            "name": "New Profile",
            "mode": "custom_voice",
            "speaker": SUPPORTED_SPEAKERS[0],
            "instruct": TONE_PRESETS["natural"],
            "ref_audio": "",
            "ref_text": "",
            "x_vector_only": False,
        }

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
        name = (name or "").strip() or "Profile"
        if not ensure_unique_profile_name(self.profiles, name, profile_id):
            return False

        target = next((item for item in self.profiles if item["id"] == profile_id), None)
        if target is None:
            target = {
                "id": profile_id or f"profile_{len(self.profiles)+1}",
                "name": name,
                "mode": mode,
                "speaker": speaker,
                "instruct": instruct,
                "ref_audio": ref_audio,
                "ref_text": ref_text,
                "x_vector_only": False,
            }
            self.profiles.append(target)
        else:
            target.update(
                {
                    "name": name,
                    "mode": mode,
                    "speaker": speaker,
                    "instruct": instruct,
                    "ref_audio": ref_audio,
                    "ref_text": ref_text,
                },
            )
        save_profiles(self.profiles)
        self.state.selected_profile = name
        self.state.inspector_profile_name = name
        self.save_prefs()
        return True

    def profile_to_dict(self, profile_id: str) -> dict | None:
        for item in self.profiles:
            if item["id"] == profile_id:
                return item
        return None

    def delete_profile(self, name: str) -> bool:
        if len(self.profiles) <= 1:
            return False
        self.profiles = [item for item in self.profiles if item["name"] != name]
        names = profile_names(self.profiles)
        save_profiles(self.profiles)
        if self.state.selected_profile == name:
            self.state.selected_profile = names[0]
            self.state.inspector_profile_name = self.state.selected_profile
        self.save_prefs()
        return True

    def build_jobs(self, target_ids: list[str]) -> tuple[list[dict], list[QTTSMessage]]:
        jobs: list[dict] = []
        active_messages: list[QTTSMessage] = []
        for idx, message_id in enumerate(target_ids, start=1):
            message = self.message_by_id(message_id)
            if message is None:
                continue
            if not message.text.strip():
                continue
            job = build_job(message.__dict__, self.profiles, self.state.selected_device, self.state.selected_language)
            job["file_name"] = f"{idx:03d}_{self._slug(message.role)}.wav"
            jobs.append(job)
            active_messages.append(message)
        return jobs, active_messages

    def run_jobs(self, target_ids: list[str], on_line=None) -> tuple[bool, dict | None, str, list[QTTSMessage]]:
        try:
            jobs, active_messages = self.build_jobs(target_ids)
        except ValueError as exc:
            return False, None, str(exc), []
        if not jobs:
            return False, None, EMPTY_TARGET_MESSAGE, []
        for message in active_messages:
            message.status = "queued"
            message.output = ""
        ok, payload, stdout = run_jobs_sync(
            jobs,
            self.active_output_dir(),
            self.state.selected_device,
            on_line=on_line,
        )
        if ok and payload and isinstance(payload, dict):
            outputs = payload.get("outputs", [])
            for index, message in enumerate(active_messages):
                if index < len(outputs):
                    message.output = outputs[index].get("output", "")
                    message.status = "done"
            return True, payload, (stdout or RUN_SUCCESS_MESSAGE), active_messages
        for message in active_messages:
            message.status = "error"
        return False, None, (stdout or RUN_FAIL_MESSAGE), active_messages

    def reveal_output_dir(self) -> None:
        path = self.active_output_dir()
        path.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(path)  # noqa: PTH118
        except Exception:
            pass
