from __future__ import annotations

import json
import os
import io
import threading
import numpy as np
from dataclasses import asdict
from pathlib import Path
from typing import Any, List, Optional, Tuple, Callable, Dict
from PIL import Image, ImageEnhance

try:
    from scipy.ndimage import sobel
except ImportError:
    sobel = None

from features.image.simple_normal_roughness_state import SimpleNormalRoughnessState, InputAsset
from contexthub.ui.qt.shell import qt_t

class SimpleNormalRoughnessService:
    def __init__(self) -> None:
        self.state = SimpleNormalRoughnessState()
        self._workflow_names = ["Default PBR"]
        self._ui_definition = [
            {"key": "preview_mode", "label": qt_t("pbr.preview_mode", "Preview Mode"), "type": "choice", "options": ["Original", "Normal", "Roughness"], "default": "Normal"},
            {"key": "save_mode", "label": qt_t("pbr.save_mode", "Save Mode"), "type": "choice", "options": ["Normal", "Roughness", "Both"], "default": "Normal"},
            {"key": "normal_strength", "label": qt_t("pbr.normal_strength", "Normal Strength"), "type": "float", "default": 1.0},
            {"key": "normal_flip_g", "label": qt_t("pbr.normal_flip_g", "Flip Green (DirectX)"), "type": "bool", "default": False},
            {"key": "roughness_contrast", "label": qt_t("pbr.roughness_contrast", "Roughness Contrast"), "type": "float", "default": 1.0},
            {"key": "roughness_invert", "label": qt_t("pbr.roughness_invert", "Roughness Invert"), "type": "bool", "default": False},
        ]
        for item in self._ui_definition:
            if item["default"] is not None:
                self.state.parameter_values[item["key"]] = item["default"]
        
        self._cancel_flag = False

    def get_workflow_names(self) -> list[str]:
        return list(self._workflow_names)

    def select_workflow(self, name: str) -> None:
        self.state.workflow_name = name

    def get_ui_definition(self) -> list[dict[str, Any]]:
        return list(self._ui_definition)

    def add_inputs(self, paths: list[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            if any(asset.path == path for asset in self.state.input_assets):
                continue
            kind = "image"
            self.state.input_assets.append(InputAsset(path=path, kind=kind))
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

    def update_output_options(
        self,
        output_dir: str,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        self.state.output_options.output_dir = Path(output_dir) if output_dir.strip() else None
        self.state.output_options.file_prefix = file_prefix.strip() or "pbr"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    def resolve_output_dir(self) -> Path | None:
        if self.state.output_options.output_dir is not None:
            return self.state.output_options.output_dir
        if not self.state.input_assets:
            return None
        return self.state.input_assets[0].path.parent

    def generate_maps(self, img_pil: Image.Image) -> Tuple[Image.Image, Image.Image]:
        params = self.state.parameter_values
        n_str = float(params.get('normal_strength', 1.0))
        n_flip = bool(params.get('normal_flip_g', False))
        r_con = float(params.get('roughness_contrast', 1.0))
        r_invert = bool(params.get('roughness_invert', False))

        gray = img_pil.convert('L')
            
        # === Roughness ===
        if r_con != 1.0:
            enhancer = ImageEnhance.Contrast(gray)
            img_con = enhancer.enhance(r_con)
        else:
            img_con = gray
            
        arr_r = np.array(img_con, dtype=np.float32) / 255.0
        rough_arr_norm = arr_r if r_invert else (1.0 - arr_r)
        rough_arr = (rough_arr_norm * 255).astype(np.uint8)
        rough_img = Image.fromarray(rough_arr).convert("RGB")
        
        # === Normal ===
        arr_n = np.array(gray, dtype=np.float32) / 255.0
        if sobel:
            dx = sobel(arr_n, axis=1)
            dy = sobel(arr_n, axis=0)
        else:
            dx = np.gradient(arr_n, axis=1)
            dy = np.gradient(arr_n, axis=0)
            
        dx *= n_str
        dy *= n_str
        if n_flip:
            dy = -dy
            
        dz = np.ones_like(arr_n)
        length = np.sqrt(dx*dx + dy*dy + dz*dz)
        np.place(length, length==0, 1)
        
        nx = (dx / length + 1) * 0.5 * 255
        ny = (dy / length + 1) * 0.5 * 255
        nz = (dz / length + 1) * 0.5 * 255
        
        norm_arr = np.stack([nx, ny, nz], axis=-1).astype(np.uint8)
        norm_img = Image.fromarray(norm_arr).convert("RGB")
        
        return norm_img, rough_img

    def get_processed_preview(self, path: Path) -> Image.Image:
        mode = self.state.parameter_values.get("preview_mode", "Normal")
        with Image.open(path) as img:
            rgb = img.convert("RGB")
            if mode == "Original":
                return rgb
            norm, rough = self.generate_maps(rgb)
            return norm if mode == "Normal" else rough

    def reveal_output_dir(self) -> None:
        path = self.resolve_output_dir()
        if path is None: return
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt": os.startfile(path)

    def run_workflow(self) -> tuple[bool, str, Path | None]:
        files = [a.path for a in self.state.input_assets]
        if not files:
            return False, "No files to process.", None
        
        output_dir = self.resolve_output_dir()
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        success = 0
        total = len(files)
        save_mode = self.state.parameter_values.get("save_mode", "Normal")

        for path in files:
            try:
                with Image.open(path) as img:
                    norm, rough = self.generate_maps(img.convert("RGB"))
                    target_dir = output_dir or path.parent
                    
                    if save_mode in {"Normal", "Both"}:
                        norm.save(target_dir / f"{path.stem}_normal.png")
                    if save_mode in {"Roughness", "Both"}:
                        rough.save(target_dir / f"{path.stem}_roughness.png")
                    success += 1
            except Exception:
                continue
        
        if self.state.output_options.open_folder_after_run and output_dir:
            self.reveal_output_dir()

        return True, f"Processed {success}/{total} files.", output_dir

    def export_session(self) -> Path:
        output_dir = self.resolve_output_dir() or Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)
        export_path = output_dir / f"{self.state.output_options.file_prefix}_session.json"
        
        payload = {
            "workflow": {"name": self.state.workflow_name},
            "inputs": [str(a.path) for a in self.state.input_assets],
            "parameters": self.state.parameter_values,
        }
        export_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return export_path
