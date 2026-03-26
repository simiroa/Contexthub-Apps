from __future__ import annotations

import json
from pathlib import Path


class VersusUpSettingsService:
    def load_settings(self, settings_file: Path, state) -> None:
        if not settings_file.exists():
            return
        try:
            data = json.loads(settings_file.read_text(encoding="utf-8"))
        except Exception:
            return
        state.ollama_host = str(data.get("ollama_host", state.ollama_host))
        state.vision_model = str(data.get("vision_model", state.vision_model))
        state.classifier_model = str(data.get("classifier_model", state.classifier_model))
        output_dir = str(data.get("output_dir", "")).strip()
        state.output_options.output_dir = Path(output_dir) if output_dir else None
        state.output_options.file_prefix = str(data.get("file_prefix", state.output_options.file_prefix))

    def save_settings(self, settings_file: Path, state) -> None:
        payload = {
            "ollama_host": state.ollama_host,
            "vision_model": state.vision_model,
            "classifier_model": state.classifier_model,
            "output_dir": str(state.output_options.output_dir) if state.output_options.output_dir else "",
            "file_prefix": state.output_options.file_prefix,
        }
        settings_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
