from __future__ import annotations

import json
import os
import webbrowser
from dataclasses import asdict
from pathlib import Path
from typing import Any

from features.comfyui.creative_studio_z_state import CreativeStudioZState
from features.comfyui.core.wrappers import registry


class CreativeStudioZService:
    def __init__(self) -> None:
        self.wrapper = registry.get_by_key("z_turbo")
        self.state = CreativeStudioZState()
        self.state.parameter_values = {
            "prompt": "",
            "resolution": "1024x1024",
            "steps": 4,
            "cfg": 2.0,
            "batch_size": 1,
            "seed": -1,
            "upscale": False,
            "rembg": False,
            "save_ico": False,
        }
        if self.wrapper is not None:
            self.state.workflow_name = self.wrapper.name
            self.state.workflow_description = self.wrapper.description

    def get_title(self) -> str:
        return self.wrapper.name if self.wrapper else "Creative Studio Z"

    def get_description(self) -> str:
        return self.wrapper.description if self.wrapper else "Fast image workspace."

    def get_ui_definition(self):
        return self.wrapper.get_ui_definition() if self.wrapper else []

    def update_parameter(self, key: str, value: Any) -> None:
        self.state.parameter_values[key] = value

    def update_output_options(self, output_dir: str, prefix: str, open_after: bool, export_json: bool) -> None:
        self.state.output_options.output_dir = Path(output_dir)
        self.state.output_options.file_prefix = prefix.strip() or "z_turbo"
        self.state.output_options.open_folder_after_run = open_after
        self.state.output_options.export_session_json = export_json

    def build_session_payload(self) -> dict[str, Any]:
        return {
            "workflow": {
                "name": self.state.workflow_name or self.get_title(),
                "description": self.state.workflow_description or self.get_description(),
            },
            "parameters": self.state.parameter_values,
            "output": asdict(self.state.output_options),
        }

    def export_session(self) -> Path:
        self.state.output_options.output_dir.mkdir(parents=True, exist_ok=True)
        payload = self.build_session_payload()
        export_path = self.state.output_options.output_dir / f"{self.state.output_options.file_prefix}_session.json"
        export_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self._remember_file(export_path)
        return export_path

    def run_workflow(self) -> tuple[bool, str, Path | None]:
        path = self.export_session() if self.state.output_options.export_session_json else None
        if path is not None:
            return True, "Fast workspace pilot mode: session exported for Z-Turbo.", path
        return True, "Fast workspace pilot mode: no export requested.", None

    def open_webui(self) -> None:
        webbrowser.open("http://127.0.0.1:8188")

    def reveal_output_dir(self) -> None:
        self.state.output_options.output_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(self.state.output_options.output_dir)

    def _remember_file(self, path: Path) -> None:
        self.state.preview_path = path
        self.state.recent_files = [path] + [item for item in self.state.recent_files if item != path]
        self.state.recent_files = self.state.recent_files[:20]

    def clear_recent_file(self, index: int) -> None:
        if 0 <= index < len(self.state.recent_files):
            removed = self.state.recent_files.pop(index)
            if self.state.preview_path == removed:
                self.state.preview_path = self.state.recent_files[0] if self.state.recent_files else None
