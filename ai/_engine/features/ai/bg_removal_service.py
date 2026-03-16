from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from features.ai.bg_removal_state import BackgroundRemovalState, InputAsset
from utils.ai_runner import start_ai_script


class BackgroundRemovalService:
    def __init__(self) -> None:
        self.state = BackgroundRemovalState()
        self.state.parameter_values = {
            "model": "birefnet",
            "postprocess": "none",
            "transparent": True,
        }

    def get_ui_definition(self) -> list[dict[str, Any]]:
        return [
            {"key": "model", "label": "Model", "type": "choice", "options": ["birefnet", "inspyrenet", "rmbg"], "default": "birefnet"},
            {"key": "postprocess", "label": "Post-process", "type": "choice", "options": ["none", "smooth", "sharpen", "feather"], "default": "none"},
            {"key": "transparent", "label": "Transparent PNG output", "type": "bool", "default": True},
        ]

    def add_inputs(self, paths_list: list[str]) -> None:
        IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tga", ".tif", ".tiff"}
        for raw_path in paths_list:
            path = Path(raw_path)
            if not path.exists():
                continue
            
            candidates: list[Path] = []
            if path.is_dir():
                candidates = [item for item in path.iterdir() if item.suffix.lower() in IMAGE_EXTS]
            elif path.suffix.lower() in IMAGE_EXTS:
                candidates = [path]
                
            for item in candidates:
                if any(asset.path == item for asset in self.state.input_assets):
                    continue
                self.state.input_assets.append(InputAsset(path=item, kind="image"))
                
        if self.state.input_assets and self.state.preview_path is None:
            self.state.preview_path = self.state.input_assets[0].path

    def remove_input_at(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            removed = self.state.input_assets.pop(index)
            if self.state.preview_path == removed.path:
                self.state.preview_path = self.state.input_assets[0].path if self.state.input_assets else None

    def clear_inputs(self) -> None:
        self.state.input_assets.clear()
        self.state.preview_path = None

    def set_preview_from_index(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            self.state.preview_path = self.state.input_assets[index].path

    def update_parameter(self, key: str, value: Any) -> None:
        self.state.parameter_values[key] = value
        if key == "model":
            self.state.model = str(value)
        elif key == "postprocess":
            self.state.postprocess = str(value)
        elif key == "transparent":
            self.state.transparent = bool(value)

    def update_output_options(
        self,
        output_dir: str,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        self.state.output_options.output_dir = Path(output_dir) if output_dir else None
        self.state.output_options.file_prefix = file_prefix.strip()
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    def probe_runtime(self) -> tuple[str, str]:
        return ("Ready", "success")

    def reveal_output_dir(self) -> None:
        out_dir = self._resolve_output_dir()
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(out_dir)

    def _resolve_output_dir(self) -> Path | None:
        if self.state.output_options.output_dir:
            return self.state.output_options.output_dir
        if self.state.input_assets:
            return self.state.input_assets[0].path.parent
        return None

    def download_models(self):
        return start_ai_script(self.app_root, ["_engine/setup/download_models.py", "--bgrm"])

    def run_workflow(self, asset_path: Path) -> subprocess.Popen:
        args = [str(asset_path), "--model", self.state.model]
        if not self.state.transparent:
            args.append("--no-transparency")
        if self.state.postprocess != "none":
            args.extend(["--postprocess", self.state.postprocess])
        
        return start_ai_script("bg_removal.py", *args)
