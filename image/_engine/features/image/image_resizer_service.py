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

from features.image.image_resizer_state import ImageResizerState, InputAsset
from contexthub.ui.qt.shell import qt_t

class ImageResizerService:
    def __init__(self) -> None:
        self.state = ImageResizerState()
        self._workflow_names = ["Image Resize"]
        self._ui_definition = [
            {"key": "mode", "label": "Upscale Method", "type": "choice", "options": ["Lanczos (High-Q)", "Bicubic (Sharp)", "Linear (Fast)", "Nearest (Pixel)", "AI (Real-ESRGAN)"], "default": "Lanczos (High-Q)"},
            {"key": "target_type", "label": "Target Type", "type": "choice", "options": ["Ratio", "Custom", "Po2"], "default": "Po2"},
            {"key": "scale_factor", "label": "Scale Factor", "type": "choice", "options": ["0.25", "0.5", "1.0", "2.0", "4.0"], "default": "1.0"},
            {"key": "custom_width", "label": "Width", "type": "string", "default": "1024"},
            {"key": "custom_height", "label": "Height", "type": "string", "default": "1024"},
            {"key": "aspect_locked", "label": "Link Aspect", "type": "bool", "default": True},
            {"key": "po2_size", "label": "POT Size", "type": "choice", "options": ["256", "512", "1024", "2048", "4096"], "default": "1024"},
            {"key": "force_square", "label": "Square 1:1", "type": "bool", "default": True},
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

    def _pad_edge(self, img: Image.Image, target_size: int) -> Image.Image:
        """Pads image to square using Edge Extrapolation (repeating edge pixels)."""
        w, h = img.size
        # Case: Already target size
        if w == target_size and h == target_size:
            return img

        # Determine scaling to fit
        ratio = min(target_size / w, target_size / h)
        nw, nh = int(w * ratio), int(h * ratio)
        # Use simple biliear for this intermediate step to keep edges clean
        res = img.resize((nw, nh), Image.Resampling.BILINEAR)
        
        # Create base canvas (filled with edge color or transparent)
        new_img = Image.new(img.mode, (target_size, target_size))
        
        # Paste centered
        ox, oy = (target_size - nw) // 2, (target_size - nh) // 2
        new_img.paste(res, (ox, oy))
        
        # Edge Extrapolation (Repeat 1px boundaries)
        # 1. Top/Bottom
        if oy > 0:
            top_edge = res.crop((0, 0, nw, 1)).resize((nw, oy), Image.Resampling.NEAREST)
            new_img.paste(top_edge, (ox, 0))
            bot_edge = res.crop((0, nh-1, nw, nh)).resize((nw, target_size - (oy + nh)), Image.Resampling.NEAREST)
            new_img.paste(bot_edge, (ox, oy + nh))
            
        # 2. Left/Right (including the corners we just filled above)
        if ox > 0:
            # We need to extend everything to the left/right
            left_strip = new_img.crop((ox, 0, ox + 1, target_size)).resize((ox, target_size), Image.Resampling.NEAREST)
            new_img.paste(left_strip, (0, 0))
            right_strip = new_img.crop((ox + nw - 1, 0, ox + nw, target_size)).resize((target_size - (ox + nw), target_size), Image.Resampling.NEAREST)
            new_img.paste(right_strip, (ox + nw, 0))
            
        return new_img

    def get_processed_preview_pil(self, path: Path, params: dict) -> Image.Image:
        """Generates a processed PIL image for preview purposes based on current params."""
        mode_str = str(params.get("mode", ""))
        target_type = str(params.get("target_type", "Po2"))
        force_square = bool(params.get("force_square", True))

        resample_map = {
            "Nearest": Image.Resampling.NEAREST,
            "Linear": Image.Resampling.BILINEAR,
            "Bicubic": Image.Resampling.BICUBIC,
            "Lanczos": Image.Resampling.LANCZOS,
        }
        resample = Image.Resampling.LANCZOS
        for k, v in resample_map.items():
            if k in mode_str:
                resample = v
                break

        with Image.open(path) as img:
            rgb = img.convert("RGBA" if "A" in img.mode else "RGB")
            w, h = rgb.size
            
            if target_type == "Ratio":
                factor = float(params.get("scale_factor", "1.0"))
                nw, nh = int(w * factor), int(h * factor)
            elif target_type == "Custom":
                nw = int(params.get("custom_width", "1024"))
                nh = int(params.get("custom_height", "1024"))
            else: # Po2
                t_size = int(params.get("po2_size", "1024"))
                if force_square:
                    rgb = self._pad_edge(rgb, t_size)
                    nw, nh = t_size, t_size
                else:
                    ratio = w / h
                    if w >= h:
                        nw = t_size
                        nh = self.get_nearest_pot(nw / ratio)
                    else:
                        nh = t_size
                        nw = self.get_nearest_pot(nh * ratio)
            
            # Skip redundant resize if dimensions match exactly (prevents potential noise at 1.0 factor)
            if nw == w and nh == h and not force_square:
                return rgb
                
            return rgb.resize((nw, nh), resample)

    def _resize_standard(self, path: Path, out_dir: Path, params: dict):
        res = self.get_processed_preview_pil(path, params)
        nw, nh = res.size
        save_ext = ".png" if "A" in res.mode else ".jpg"
        save_path = out_dir / f"{path.stem}_{nw}x{nh}{save_ext}"
        res.save(save_path, quality=95 if save_ext == ".jpg" else None)

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
                    # AI logic works with max side for now
                    if self._resize_ai(p, out, 2048): # Fixed for logic simplicity
                         success += 1
                else:
                    self._resize_standard(p, out, params)
                    success += 1
                if del_orig: os.remove(p)
            except:
                import traceback
                traceback.print_exc()
                continue

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
