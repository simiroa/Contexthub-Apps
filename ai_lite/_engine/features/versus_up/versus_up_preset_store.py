from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class VersusUpPresetStore:
    def load(self, presets_file: Path) -> list[dict[str, Any]]:
        if not presets_file.exists():
            return []
        try:
            payload = json.loads(presets_file.read_text(encoding="utf-8"))
            return list(payload.get("presets", []) or [])
        except Exception:
            return []

    def save(self, presets_file: Path, presets: list[dict[str, Any]]) -> None:
        presets_file.write_text(json.dumps({"presets": presets}, indent=2, ensure_ascii=False), encoding="utf-8")
