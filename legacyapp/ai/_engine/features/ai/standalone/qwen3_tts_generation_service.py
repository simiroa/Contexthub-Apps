from __future__ import annotations

import os
import re
from pathlib import Path

from features.ai.standalone.qwen3_tts_service import build_job, run_jobs_sync


EMPTY_TARGET_MESSAGE = "No valid dialogue lines to generate."
RUN_SUCCESS_MESSAGE = "Speech generated successfully."
RUN_FAIL_MESSAGE = "Generation failed."


class Qwen3TTSGenerationService:
    @staticmethod
    def slug(text: str) -> str:
        key = re.sub(r"[^A-Za-z0-9]+", "_", text.strip().lower())
        if not key:
            return "message"
        return key.strip("_")

    def build_jobs(
        self,
        messages: list,
        profiles: list[dict],
        selected_device: str,
        selected_language: str,
        target_ids: list[str],
    ) -> tuple[list[dict], list]:
        jobs: list[dict] = []
        active_messages: list = []
        indexed = {message.id: message for message in messages}
        for idx, message_id in enumerate(target_ids, start=1):
            message = indexed.get(message_id)
            if message is None or not message.text.strip():
                continue
            job = build_job(message.__dict__, profiles, selected_device, selected_language)
            job["file_name"] = f"{idx:03d}_{self.slug(message.role)}.wav"
            jobs.append(job)
            active_messages.append(message)
        return jobs, active_messages

    def run_jobs(
        self,
        messages: list,
        profiles: list[dict],
        selected_device: str,
        selected_language: str,
        output_dir: Path,
        target_ids: list[str],
        on_line=None,
    ) -> tuple[bool, dict | None, str, list]:
        jobs, active_messages = self.build_jobs(messages, profiles, selected_device, selected_language, target_ids)
        if not jobs:
            return False, None, EMPTY_TARGET_MESSAGE, []
        for message in active_messages:
            message.status = "queued"
            message.output = ""
        ok, payload, stdout = run_jobs_sync(jobs, output_dir, selected_device, on_line=on_line)
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

    def reveal_output_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(path)  # noqa: PTH118
        except Exception:
            pass
