from __future__ import annotations

import json
import os
import math
import shutil
import tempfile
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, List, Optional, Tuple, Callable
from PIL import Image

from features.image.resize_power_of_2_state import ResizePowerOf2State, InputAsset
from contexthub.ui.qt.shell import qt_t

class ResizePowerOf2Service:
    def __init__(self) -> None:
        self.state = ResizePowerOf2State()
        self._workflow_names = ["POT Resize"]
        self._ui_definition = [
            {"key": "target_size", "label": qt_t("pot.target_size", "Target Longest Side"), "type": "choice", "options": ["256", "512", "1024", "2048", "4096"], "default": "1024"},
            {"key": "mode", "label": qt_t("pot.mode", "Upscale Mode"), "type": "choice", "options": ["Standard", "AI (Real-ESRGAN)"], "default": "Standard"},
            {"key": "force_square", "label": qt_t("pot.force_square", "Force Square (Padding)"), "type": "bool", "default": True},
            {"key": "delete_original", "label": qt_t("pot.delete_original", "Delete Original"), "type": "bool", "default": False},
        ]
        for item in self._ui_definition:
            if item["default"] is not None:
                self.state.parameter_values[item["key"]] = item["default"]
        
        self.pkg_mgr = self._build_package_manager()

    def _build_package_manager(self):
        try:
            from manager.mgr_core.packages import PackageManager
            return PackageManager()
        except: return None

    def get_workflow_names(self) -> list[str]:
        return list(self._workflow_names)

    def select_workflow(self, name: str) -> None:
        self.state.workflow_name = name

    def get_ui_definition(self) -> list[dict[str, Any]]:
        return list(self._ui_definition)

    def add_inputs(self, paths: list[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists(): continue
            if any(asset.path == path for asset in self.state.input_assets): continue
            self.state.input_assets.append(InputAsset(path=path, kind="image"))
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

    def update_output_options(self, output_dir: str, file_prefix: str, open_folder_after_run: bool, export_session_json: bool):
        self.state.output_options.output_dir = Path(output_dir) if output_dir.strip() else None
        self.state.output_options.file_prefix = file_prefix.strip() or "resized"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    def resolve_output_dir(self) -> Path | None:
        if self.state.output_options.output_dir: return self.state.output_options.output_dir
        if not self.state.input_assets: return None
        return self.state.input_assets[0].path.parent

    def get_nearest_pot(self, val: int) -> int:
        if val <= 0: return 2
        return 2**round(math.log2(val))

    def _resize_standard(self, path: Path, out_dir: Path, target_size: int, force_square: bool):
        with Image.open(path) as img:
            rgb = img.convert("RGB")
            w, h = rgb.size
            if force_square:
                ratio = min(target_size/w, target_size/h)
                nw, nh = int(w * ratio), int(h * ratio)
                res = rgb.resize((nw, nh), Image.Resampling.LANCZOS)
                new_img = Image.new("RGB", (target_size, target_size), (0, 0, 0))
                new_img.paste(res, ((target_size - nw)//2, (target_size - nh)//2))
                res = new_img
            else:
                ratio = w / h
                if w >= h:
                    nw = target_size
                    nh = self.get_nearest_pot(nw / ratio)
                else:
                    nh = target_size
                    nw = self.get_nearest_pot(nh * ratio)
                res = rgb.resize((nw, nh), Image.Resampling.LANCZOS)
            
            save_path = out_dir / f"{path.stem}_{target_size}px{path.suffix}"
            res.save(save_path)

    def _resize_ai(self, path: Path, out_dir: Path, target_size: int) -> bool:
        if not self.pkg_mgr: return False
        exe = self.pkg_mgr.get_tool_path("realesrgan-ncnn-vulkan")
        if not exe or not exe.exists(): return False

        with Image.open(path) as img:
            w, h = img.size
            scale_needed = target_size / max(w, h)
            scale = 4 if scale_needed > 2.5 else (2 if scale_needed > 1.0 else 1)

        if scale == 1:
            shutil.copy(path, out_dir / f"{path.stem}_ai1x{path.suffix}")
            return True

        with tempfile.TemporaryDirectory() as tmp:
            tmp_out = Path(tmp) / "out.png"
            cmd = [str(exe), "-i", str(path), "-o", str(tmp_out), "-s", str(scale), "-n", "realesrgan-x4plus"]
            if subprocess.run(cmd, capture_output=True).returncode == 0 and tmp_out.exists():
                shutil.move(str(tmp_out), out_dir / f"{path.stem}_ai{scale}x.png")
                return True
        return False

    def run_workflow(self) -> tuple[bool, str, Path | None]:
        files = [a.path for a in self.state.input_assets]
        if not files: return False, "No items", None
        
        target_dir = self.resolve_output_dir()
        if target_dir: target_dir.mkdir(parents=True, exist_ok=True)
        
        params = self.state.parameter_values
        t_size = int(params.get("target_size", "1024"))
        is_ai = "AI" in str(params.get("mode", "Standard"))
        f_square = bool(params.get("force_square", True))
        del_orig = bool(params.get("delete_original", False))

        success = 0
        for p in files:
            try:
                out = target_dir or p.parent
                if is_ai:
                    if self._resize_ai(p, out, t_size): success += 1
                else:
                    self._resize_standard(p, out, t_size, f_square)
                    success += 1
                if del_orig: os.remove(p)
            except: continue

        return True, f"Done: {success}/{len(files)}", target_dir

    def reveal_output_dir(self):
        p = self.resolve_output_dir()
        if p and p.exists() and os.name == "nt": os.startfile(p)
    
    def export_session(self) -> Path:
        out = self.resolve_output_dir() or Path.cwd()
        out.mkdir(parents=True, exist_ok=True)
        path = out / "pot_resize_session.json"
        path.write_text(json.dumps(asdict(self.state), default=str, indent=2))
        return path
