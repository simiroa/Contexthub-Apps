from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from features.ai.marigold_pbr_state import MarigoldPBRState, InputAsset
from core.paths import TOOLS_DIR
from core.settings import load_settings


class MarigoldPBRService:
    def __init__(self) -> None:
        self.state = MarigoldPBRState()
        self._workflow_names = ["Speed", "Balanced", "Quality"]
        
        # Categorized UI Definition
        self._ui_definition = [
            {
                "section": "Texture Maps",
                "items": [
                    {"key": "gen_depth", "label": "Depth Map", "type": "bool", "default": False},
                    {"key": "gen_normal", "label": "Normal Map", "type": "bool", "default": True},
                    {"key": "gen_albedo", "label": "Albedo Map", "type": "bool", "default": False},
                    {"key": "gen_roughness", "label": "Roughness Map", "type": "bool", "default": False},
                    {"key": "gen_metallicity", "label": "Metallicity Map", "type": "bool", "default": False},
                    {"key": "gen_orm", "label": "ORM Packed Map", "type": "bool", "default": False},
                ]
            },
            {
                "section": "Generation Quality",
                "items": [
                    {"key": "steps", "label": "Steps", "type": "int", "default": 20, "min": 1, "max": 100},
                    {"key": "ensemble", "label": "Ensemble Passes", "type": "int", "default": 3, "min": 1, "max": 20},
                    {"key": "processing_res", "label": "Internal Resolution", "type": "choice", "options": ["512", "768", "1024", "Native"], "default": "768"},
                ]
            },
            {
                "section": "Optimization & Flip",
                "items": [
                    {"key": "fp16", "label": "Use FP16 (VRAM Save)", "type": "bool", "default": True},
                    {"key": "flip_y", "label": "Flip Normal Y (DirectX)", "type": "bool", "default": False},
                    {"key": "invert_rough", "label": "Invert Roughness (Gloss)", "type": "bool", "default": False},
                ]
            }
        ]
        
        for section in self._ui_definition:
            for item in section["items"]:
                if "default" in item:
                    self.state.parameter_values[item["key"]] = item["default"]

    def get_workflow_names(self) -> list[str]:
        return list(self._workflow_names)

    def select_workflow(self, name: str) -> None:
        self.state.workflow_name = name
        if name == "Speed":
            self.state.workflow_description = "Fast generation (10 steps, 1 ensemble pass)."
            self.update_parameter("steps", 10)
            self.update_parameter("ensemble", 1)
            self.update_parameter("processing_res", "512")
        elif name == "Balanced":
            self.state.workflow_description = "Balanced speed and quality (20 steps, 3 ensemble passes)."
            self.update_parameter("steps", 20)
            self.update_parameter("ensemble", 3)
            self.update_parameter("processing_res", "768")
        elif name == "Quality":
            self.state.workflow_description = "High quality (50 steps, 5 ensemble passes)."
            self.update_parameter("steps", 50)
            self.update_parameter("ensemble", 5)
            self.update_parameter("processing_res", "Native")

    def get_ui_definition(self) -> list[dict[str, Any]]:
        return list(self._ui_definition)

    def add_inputs(self, paths: list[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                continue
            
            # Keep only the latest single image
            self.state.input_assets = [InputAsset(path=path, kind="image")]
            self.state.preview_path = path
            break

    def remove_input_at(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            self.state.input_assets.pop(index)
            self.state.preview_path = self.state.input_assets[0].path if self.state.input_assets else None

    def clear_inputs(self) -> None:
        self.state.input_assets.clear()
        self.state.preview_path = None

    def update_parameter(self, key: str, value: Any) -> None:
        self.state.parameter_values[key] = value

    def resolve_output_dir(self) -> Path | None:
        if self.state.output_options.output_dir is not None:
            return self.state.output_options.output_dir
        if not self.state.input_assets:
            return None
        return self.state.input_assets[0].path.parent

    def probe_runtime(self) -> tuple[str, str]:
        try:
            from setup.download_models import check_marigold_exists
            if check_marigold_exists():
                return ("Marigold models ready.", "ready")
            return ("Missing models. Click Run to download.", "warning")
        except Exception:
            return ("Ready to run.", "ready")

    def download_models(self, progress_callback=None) -> tuple[bool, str]:
        if progress_callback:
            progress_callback("Starting model download process...")
        
        setup_script = Path(__file__).resolve().parents[1] / "setup" / "download_models.py"
        python_exe = self._resolve_python()
        
        args = [python_exe, str(setup_script)]
        try:
            result = subprocess.run(args, capture_output=True, text=True, creationflags=0x08000000)
            if result.returncode != 0:
                return False, f"Download failed: {result.stderr or result.stdout}"
            return True, "Models installed successfully."
        except Exception as e:
            return False, f"Failed to start download: {e}"

    def reveal_output_dir(self) -> None:
        path = self.resolve_output_dir()
        if path is None:
            return
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)

    def run_workflow(self, progress_callback=None) -> tuple[bool, str, Path | None]:
        if not self.state.input_assets:
            return False, "Add an image first.", None
        
        params = self.state.parameter_values
        essential_maps = ["gen_depth", "gen_normal", "gen_albedo", "gen_roughness", "gen_metallicity", "gen_orm"]
        if not any(params.get(m, False) for m in essential_maps):
            return False, "Select at least one map to generate.", None

        inference_script = Path(__file__).resolve().parent / "standalone" / "marigold_inference.py"
        python_exe = self._resolve_python()
        
        asset = self.state.input_assets[0]
        if progress_callback:
            progress_callback(f"Generating PBR maps for {asset.path.name}...")
                
        args = [python_exe, str(inference_script), str(asset.path)]
        if params.get("gen_depth"): args.append("--depth")
        if params.get("gen_normal"): args.append("--normal")
        if params.get("gen_albedo"): args.append("--albedo")
        if params.get("gen_roughness"): args.append("--roughness")
        if params.get("gen_metallicity"): args.append("--metallicity")
        if params.get("gen_orm"): args.append("--orm")
        if params.get("flip_y"): args.append("--flip_y")
        if params.get("invert_rough"): args.append("--invert_roughness")
        
        res = params.get("processing_res", "768")
        if res != "Native": args.extend(["--res", str(res)])
        args.extend(["--ensemble", str(params.get("ensemble", 1))])
        args.extend(["--steps", str(params.get("steps", 10))])
        if params.get("fp16"): args.append("--fp16")

        try:
            result = subprocess.run(args, capture_output=True, text=True, creationflags=0x08000000)
            if result.returncode != 0:
                return False, f"Inference failed: {result.stderr or result.stdout}", None
        except Exception as e:
            return False, f"Launch error: {e}", None

        if self.state.output_options.open_folder_after_run:
            self.reveal_output_dir()
        return True, "Successfully generated PBR maps.", self.resolve_output_dir()

    def _resolve_python(self) -> str:
        settings = load_settings()
        env_path = settings.get("AI_CONDA_ENV_PATH")
        if env_path:
            candidate = Path(env_path) / "python.exe"
            if candidate.exists():
                return str(candidate)
        embedded = TOOLS_DIR / "python" / "python.exe"
        if embedded.exists():
            return str(embedded)
        return sys.executable
