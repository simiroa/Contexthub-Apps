from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from features.ai.upscale_state import UpscaleState, InputAsset
from utils import paths
from utils.ai_runner import start_ai_script


class UpscaleService:
    def __init__(self) -> None:
        self.state = UpscaleState()
        self.state.parameter_values = {
            "scale": "4",
            "face_enhance": False,
            "use_tile": False,
        }

    def get_ui_definition(self) -> list[dict[str, Any]]:
        return [
            {"key": "scale", "label": "Scale", "type": "choice", "options": ["2", "4"], "default": "4"},
            {"key": "face_enhance", "label": "Face Enhance (GFPGAN)", "type": "bool", "default": False},
            {"key": "use_tile", "label": "Use Tiling for low VRAM", "type": "bool", "default": False},
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
        if key == "scale":
            self.state.scale = str(value)
        elif key == "face_enhance":
            self.state.face_enhance = bool(value)
        elif key == "use_tile":
            self.state.use_tile = bool(value)

    def update_output_options(
        self,
        output_dir: str,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        self.state.output_options.output_dir = Path(output_dir) if output_dir else None
        self.state.output_options.file_prefix = file_prefix.strip() or "upscaled"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    def probe_runtime(self) -> tuple[str, str]:
        model_root = self._realesrgan_dir()
        model = model_root / "RealESRGAN_x4plus.pth"
        gfpgan = model_root / "GFPGANv1.4.pth"
        if model.exists() and gfpgan.exists():
            return "Models ready", "success"
        if model.exists():
            return "ESRGAN ready", "success"
        return "Models missing", "warning"

    def _realesrgan_dir(self) -> Path:
        model_root = getattr(paths, "REALESRGAN_DIR", None)
        if model_root:
            return Path(model_root)
        engine_root = Path(__file__).resolve().parents[3]
        return engine_root / "resources" / "ai_models" / "realesrgan"

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

    def download_models(self) -> subprocess.Popen:
        script = Path(__file__).resolve().parents[2] / "setup" / "download_models.py"
        return subprocess.Popen(
            [sys.executable, str(script), "--upscale"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def run_workflow(self) -> subprocess.Popen:
        args = [str(asset.path) for asset in self.state.input_assets]
        args.extend(["--scale", self.state.scale])
        if self.state.face_enhance:
            args.append("--face-enhance")
        if self.state.use_tile:
            args.extend(["--tile", "512"])
        
        out_dir = self._resolve_output_dir()
        if out_dir:
            args.extend(["--output", str(out_dir)])

        return start_ai_script("upscale.py", *args)
