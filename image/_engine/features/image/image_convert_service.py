from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any, List, Optional, Tuple, Callable
import multiprocessing

from PIL import Image, ImageOps

from features.image.image_convert_state import ImageConvertState, InputAsset


class ImageConvertService:
    def __init__(self) -> None:
        self.state = ImageConvertState()
        self.executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
        
        self._formats = ["PNG", "JPG", "WEBP", "BMP", "ICO", "EXR"]
        self._ui_definition = [
            {
                "key": "target_format", 
                "label": "Output Format", 
                "type": "choice", 
                "options": self._formats, 
                "default": "PNG"
            },
            {
                "key": "resize_enabled", 
                "label": "Enable Resizing", 
                "type": "choice", 
                "options": ["Disable", "Enable"], 
                "default": "Disable"
            },
            {
                "key": "resize_size", 
                "label": "Long Edge Size", 
                "type": "string", 
                "default": "1024"
            },
            {
                "key": "delete_original", 
                "label": "Delete Original", 
                "type": "choice", 
                "options": ["No", "Yes"], 
                "default": "No"
            },
        ]
        
        for item in self._ui_definition:
            if item["default"] is not None:
                self.state.parameter_values[item["key"]] = item["default"]

    def get_workflow_names(self) -> list[str]:
        return ["Standard Conversion"]

    def select_workflow(self, name: str) -> None:
        self.state.workflow_name = name
        self.state.workflow_description = "Convert images to various formats with optional long-edge resizing."

    def get_ui_definition(self) -> list[dict[str, Any]]:
        return list(self._ui_definition)

    def add_inputs(self, paths: list[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            if any(asset.path == path for asset in self.state.input_assets):
                continue
            kind = "image" if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".ico", ".exr"} else "file"
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
        self.state.output_options.output_dir = Path(output_dir)
        self.state.output_options.file_prefix = file_prefix.strip() or "convert"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    def reveal_output_dir(self) -> None:
        path = self.state.output_options.output_dir
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)

    def build_session_payload(self) -> dict[str, Any]:
        return {
            "workflow": {
                "name": self.state.workflow_name,
                "description": self.state.workflow_description,
            },
            "inputs": [{"path": str(asset.path), "kind": asset.kind} for asset in self.state.input_assets],
            "parameters": self.state.parameter_values,
            "output": asdict(self.state.output_options),
        }

    def export_session(self) -> Path:
        self.state.output_options.output_dir.mkdir(parents=True, exist_ok=True)
        export_path = self.state.output_options.output_dir / f"{self.state.output_options.file_prefix}_session.json"
        export_path.write_text(json.dumps(self.build_session_payload(), indent=2, ensure_ascii=False), encoding="utf-8")
        return export_path

    def run_workflow(self, on_progress: Callable[[float, int, int], None], on_complete: Callable[[int, List[str]], None]) -> tuple[bool, str, Path | None]:
        if not self.state.input_assets:
            return False, "No input files.", None
            
        session_path = self.export_session() if self.state.output_options.export_session_json else None
        
        files = [asset.path for asset in self.state.input_assets]
        target_fmt = str(self.state.parameter_values.get("target_format", "PNG"))
        resize_enabled = self.state.parameter_values.get("resize_enabled") == "Enable"
        try:
            resize_size = int(self.state.parameter_values.get("resize_size", "1024")) if resize_enabled else None
        except ValueError:
            resize_size = None
            
        delete_original = self.state.parameter_values.get("delete_original") == "Yes"
        
        def _task():
            total = len(files)
            success_count = 0
            errors = []
            
            pil_fmt = target_fmt.lower()
            if pil_fmt == "jpg":
                pil_fmt = "jpeg"
            
            worker_args = []
            for src in files:
                out_dir = self.state.output_options.output_dir
                out_dir.mkdir(parents=True, exist_ok=True)
                
                new_ext = ".jpg" if pil_fmt == "jpeg" else f".{pil_fmt}"
                new_path = out_dir / src.with_suffix(new_ext).name
                if new_path == src:
                    new_path = out_dir / f"{src.stem}_converted{new_ext}"
                
                worker_args.append((src, pil_fmt, resize_size, new_path))

            completed = 0
            futures = [self.executor.submit(self._convert_single, args) for args in worker_args]
            
            for i, future in enumerate(futures):
                src_path = worker_args[i][0]
                result_success, error_msg = future.result()
                completed += 1
                
                if result_success:
                    success_count += 1
                    if delete_original and src_path.exists():
                        try:
                            os.remove(src_path)
                        except Exception as e:
                            errors.append(f"Delete failed: {src_path.name} ({e})")
                else:
                    errors.append(error_msg)
                
                on_progress(completed / total, completed, total)
            
            on_complete(success_count, errors)

        threading.Thread(target=_task, daemon=True).start()
        return True, "Processing...", session_path

    def _convert_single(self, args) -> Tuple[bool, Optional[str]]:
        path, target_fmt, resize_size, out_path = args
        try:
            img = Image.open(path)
            img.load()

            if target_fmt in ['jpeg', 'bmp'] and img.mode in ('RGBA', 'LA', 'P'):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if 'A' in img.getbands():
                    bg.paste(img, mask=img.split()[-1])
                else:
                    bg.paste(img)
                img = bg
            elif target_fmt in ['jpeg', 'bmp'] and img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            if target_fmt == "ico" and (img.size[0] > 256 or img.size[1] > 256):
                img = ImageOps.contain(img, (256, 256), method=Image.Resampling.LANCZOS)
            
            if resize_size:
                w, h = img.size
                if w >= h:
                    new_w, new_h = resize_size, int(h * (resize_size / w))
                else:
                    new_h, new_w = resize_size, int(w * (resize_size / h))
                if new_w > 0 and new_h > 0:
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            save_kwargs = {}
            if target_fmt == "jpeg":
                save_kwargs['quality'] = 95
                save_kwargs['optimize'] = True
            elif target_fmt == "webp":
                save_kwargs['quality'] = 90
                save_kwargs['method'] = 6
            elif target_fmt == "exr":
                return self._save_exr(img, out_path)
            
            img.save(out_path, **save_kwargs)
            return True, None
            
        except Exception as e:
            return False, f"{path.name}: {e}"

    def _save_exr(self, img: Image.Image, out_path: Path) -> Tuple[bool, Optional[str]]:
        try:
            import OpenEXR
            import Imath
            import numpy as np
            
            img_rgb = img.convert('RGB') if img.mode != 'RGB' else img
            arr = np.array(img_rgb, dtype=np.float32) / 255.0
            arr = np.power(arr, 2.2) 
            
            h, w = arr.shape[:2]
            header = OpenEXR.Header(w, h)
            header['compression'] = Imath.Compression(Imath.Compression.PIZ_COMPRESSION)
            header['channels']['R'] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
            header['channels']['G'] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
            header['channels']['B'] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
            
            exr_out = OpenEXR.OutputFile(str(out_path), header)
            exr_out.writePixels({
                'R': arr[:,:,0].tobytes(),
                'G': arr[:,:,1].tobytes(),
                'B': arr[:,:,2].tobytes()
            })
            exr_out.close()
            return True, None
        except Exception as e:
            return False, f"EXR error: {e}"
