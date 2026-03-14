import os
import math
import shutil
import tempfile
import subprocess
import threading
from pathlib import Path
from typing import List, Optional, Tuple, Callable
from PIL import Image

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
from utils.files import get_safe_path

logger = setup_logger("resize_pot_service")

class ResizePotService:
    def __init__(self):
        self.pkg_mgr = self._build_package_manager()
        self._cancel_flag = False

    def _build_package_manager(self):
        try:
            from manager.mgr_core.packages import PackageManager
            return PackageManager()
        except Exception:
            return None

    def cancel(self):
        self._cancel_flag = True

    def get_nearest_pot(self, val: int) -> int:
        if val <= 0: return 2
        return 2**round(math.log2(val))

    def run_resize_batch(self, 
                         files: List[Path], 
                         target_size: int,
                         mode: str,
                         force_square: bool,
                         save_to_folder: bool,
                         delete_original: bool,
                         on_progress: Callable[[float, str], None],
                         on_complete: Callable[[int, List[str]], None]):
        
        self._cancel_flag = False
        
        def _task():
            success = 0
            errors = []
            total = len(files)
            
            for i, path in enumerate(files):
                if self._cancel_flag:
                    break
                
                try:
                    on_progress(i / total, f"Processing: {path.name}")
                    
                    if not path.exists():
                        errors.append(f"{path.name}: File not found")
                        continue

                    # Output setup
                    out_dir = path.parent
                    if save_to_folder:
                        out_dir = path.parent / "Resized"
                        out_dir.mkdir(exist_ok=True)

                    if mode == "AI":
                        success_file = self._resize_ai(path, out_dir, target_size)
                        if success_file: success += 1
                        else: errors.append(f"{path.name}: AI conversion failed")
                    else:
                        self._resize_standard(path, out_dir, target_size, force_square)
                        success += 1

                    if delete_original and not self._cancel_flag:
                        try:
                            os.remove(path)
                        except Exception as e:
                            logger.error(f"Failed to delete original {path.name}: {e}")

                except Exception as e:
                    logger.error(f"Error processing {path.name}: {e}")
                    errors.append(f"{path.name}: {str(e)}")

            on_complete(success, errors)

        threading.Thread(target=_task, daemon=True).start()

    def _resize_standard(self, path: Path, out_dir: Path, target_size: int, force_square: bool):
        with Image.open(path) as img:
            if img.mode != "RGB": 
                img = img.convert("RGB")
            
            w, h = img.size
            
            if force_square:
                ratio = min(target_size/w, target_size/h)
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                
                res = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                new_img = Image.new("RGB", (target_size, target_size), (0, 0, 0))
                
                offset_x = (target_size - new_w) // 2
                offset_y = (target_size - new_h) // 2
                new_img.paste(res, (offset_x, offset_y))
                res = new_img
            else:
                ratio = w / h
                if w >= h:
                    nw = target_size
                    nh = self.get_nearest_pot(nw / ratio)
                else:
                    nh = target_size
                    nw = self.get_nearest_pot(nh * ratio)
                res = img.resize((nw, nh), Image.Resampling.LANCZOS)
            
            new_name = f"{path.stem}_{target_size}px{path.suffix}"
            save_path = get_safe_path(out_dir / new_name)
            res.save(save_path)

    def _resize_ai(self, path: Path, out_dir: Path, target_size: int) -> bool:
        if self.pkg_mgr is None:
            raise Exception("Package manager not available in this runtime.")

        esrgan_exe = self.pkg_mgr.get_tool_path("realesrgan-ncnn-vulkan")
        if not esrgan_exe or not esrgan_exe.exists():
            raise Exception("Real-ESRGAN tool not found. Please install via Manager -> Preferences.")

        with Image.open(path) as img:
            w, h = img.size
            longest = max(w, h)
            scale_needed = target_size / longest
            
            if scale_needed <= 1.0: scale = 1
            elif scale_needed <= 2.5: scale = 2
            else: scale = 4

        if scale == 1:
            dest_path = get_safe_path(out_dir / f"{path.stem}_ai1x{path.suffix}")
            shutil.copy(path, dest_path)
            return True

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            temp_output = temp_dir / f"{path.stem}.png"
            
            cmd = [
                str(esrgan_exe),
                "-i", str(path),
                "-o", str(temp_output),
                "-s", str(scale),
                "-n", "realesrgan-x4plus"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"AI Failed: {result.stderr}")
                return False
            
            if not temp_output.exists():
                return False
            
            dest_path = get_safe_path(out_dir / f"{path.stem}_ai{scale}x.png")
            shutil.move(str(temp_output), str(dest_path))
            return True
