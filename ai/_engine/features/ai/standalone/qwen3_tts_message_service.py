from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from features.ai.standalone.qwen3_tts_service import prefill_messages


INVALID_TEXT_MESSAGE = "Text is required."


@dataclass
class QTTSMessage:
    id: str
    role: str
    profile: str
    tone: str
    text: str
    status: str = "ready"
    output: str = ""


class Qwen3TTSMessageService:
    def __init__(self, default_text: str) -> None:
        self.default_text = default_text

    def load_initial_messages(self, target_path: Path | None, profiles: list[dict]) -> tuple[list[QTTSMessage], list[dict]]:
        safe_target = target_path if target_path and target_path.exists() else None
        messages, profiles = prefill_messages(safe_target, profiles, self.default_text)
        return [QTTSMessage(**item) for item in messages], profiles

    def sync_selected_message_id(self, messages: list[QTTSMessage], selected_id: str | None) -> str | None:
        if messages and selected_id is None:
            return messages[0].id
        return selected_id

    def message_by_id(self, messages: list[QTTSMessage], message_id: str | None) -> QTTSMessage | None:
        if not message_id:
            return None
        for message in messages:
            if message.id == message_id:
                return message
        return None

    def upsert_message(
        self,
        messages: list[QTTSMessage],
        selected_profile: str,
        selected_tone: str,
        text: str,
        message_id: str | None = None,
    ) -> tuple[QTTSMessage, list[QTTSMessage]]:
        text = (text or "").strip()
        if not text:
            raise ValueError(INVALID_TEXT_MESSAGE)

        if message_id:
            target = self.message_by_id(messages, message_id)
            if target:
                target.text = text
                target.profile = selected_profile
                target.role = selected_profile
                target.tone = selected_tone
                target.status = "ready"
                return target, messages

        message = QTTSMessage(
            id=f"msg_{len(messages)+1}",
            role=selected_profile,
            profile=selected_profile,
            tone=selected_tone,
            text=text,
        )
        messages.append(message)
        return message, messages

    def delete_message(self, messages: list[QTTSMessage], message_id: str) -> list[QTTSMessage]:
        return [message for message in messages if message.id != message_id]

    def update_message(
        self,
        messages: list[QTTSMessage],
        message_id: str,
        *,
        profile: str | None = None,
        tone: str | None = None,
        text: str | None = None,
    ) -> None:
        message = self.message_by_id(messages, message_id)
        if message is None:
            return
        if profile is not None:
            message.profile = profile
        if tone is not None:
            message.tone = tone
        if text is not None:
            message.text = text.strip()
        message.status = "ready"
