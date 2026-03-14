import os
import io
import threading
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple, Callable, Dict
from PIL import Image, ImageEnhance
try:
    from scipy.ndimage import sobel
except ImportError:
    sobel = None

try:
    from core.logger import setup_logger
except ModuleNotFoundError:
    try:
        from contexthub.core.logger import setup_logger
    except ModuleNotFoundError:
        import logging

        def setup_logger(name: str):
            logger = logging.getLogger(name)
            if not logger.handlers:
                logging.basicConfig(level=logging.INFO)
            return logger

logger = setup_logger("simple_pbr_service")

class SimplePbrService:
    def __init__(self):
        self._cancel_flag = False

    def generate_maps(self, 
                     img_pil: Image.Image, 
                     params: Dict) -> Tuple[Image.Image, Image.Image]:
        """Core logic: Returns (normal_pil, roughness_pil)"""
        n_str = params.get('normal_strength', 1.0)
        n_flip = params.get('normal_flip_g', False)
        r_con = params.get('roughness_contrast', 1.0)
        r_invert = params.get('roughness_invert', False)

        # Convert to gray for base
        gray = img_pil.convert('L')
            
        # === Roughness ===
        if r_con != 1.0:
            enhancer = ImageEnhance.Contrast(gray)
            img_con = enhancer.enhance(r_con)
        else:
            img_con = gray
            
        arr_r = np.array(img_con, dtype=np.float32) / 255.0
        
        # Invert logic: default depth (1.0 - Gray) or inverted (Gray)
        rough_arr_norm = arr_r if r_invert else (1.0 - arr_r)
        rough_arr = (rough_arr_norm * 255).astype(np.uint8)
        rough_img = Image.fromarray(rough_arr)
        
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
            dy = -dy # Flip Green (Y-axis)
            
        dz = np.ones_like(arr_n)
        length = np.sqrt(dx*dx + dy*dy + dz*dz)
        np.place(length, length==0, 1)
        
        nx = (dx / length + 1) * 0.5 * 255
        ny = (dy / length + 1) * 0.5 * 255
        nz = (dz / length + 1) * 0.5 * 255
        
        norm_arr = np.stack([nx, ny, nz], axis=-1).astype(np.uint8)
        norm_img = Image.fromarray(norm_arr)
        
        return norm_img, rough_img

    def get_preview_bytes(self, img_pil: Image.Image, format="PNG") -> bytes:
        buf = io.BytesIO()
        img_pil.save(buf, format=format)
        return buf.getvalue()

    def run_batch_save(self,
                        files: List[Path],
                        params: Dict,
                        mode: str, # "Normal" or "Roughness"
                        on_progress: Callable[[float, str], None],
                        on_complete: Callable[[int, List[str]], None]):
        
        self._cancel_flag = False
        
        def _task():
            success = 0
            errors = []
            total = len(files)
            
            for i, path in enumerate(files):
                if self._cancel_flag: break
                try:
                    on_progress(i / total, f"Processing: {path.name}")
                    with Image.open(path) as img:
                        norm, rough = self.generate_maps(img.convert("RGB"), params)
                        
                        if mode == "Normal":
                            out_path = path.parent / f"{path.stem}_normal.png"
                            norm.save(out_path)
                        elif mode == "Roughness":
                            out_path = path.parent / f"{path.stem}_roughness.png"
                            rough.save(out_path)
                        
                        success += 1
                except Exception as e:
                    logger.error(f"Failed to process {path.name}: {e}")
                    errors.append(f"{path.name}: {e}")
            
            on_complete(success, errors)

        threading.Thread(target=_task, daemon=True).start()
