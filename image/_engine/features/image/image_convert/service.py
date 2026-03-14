import os
from pathlib import Path
from typing import List, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from PIL import Image, ImageOps
import threading

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

logger = setup_logger("image_convert_service")

class ImageConvertService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())

    def convert_batch(self, 
                      files: List[Path], 
                      target_fmt: str, 
                      resize_size: Optional[int], 
                      save_to_folder: bool, 
                      delete_original: bool,
                      on_progress: Callable[[float, int, int], None],
                      on_complete: Callable[[int, List[str]], None]):
        
        def _task():
            total = len(files)
            success_count = 0
            errors = []
            
            # Prepare format string for PIL
            pil_fmt = target_fmt.lower()
            if pil_fmt == "jpg":
                pil_fmt = "jpeg"
            
            # Prepare output directories and paths
            worker_args = []
            for src in files:
                out_dir = src.parent
                if save_to_folder:
                    out_dir = src.parent / "Converted_Images"
                    out_dir.mkdir(exist_ok=True)
                
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

    def _convert_single(self, args) -> Tuple[bool, Optional[str]]:
        path, target_fmt, resize_size, out_path = args
        try:
            img = Image.open(path)
            img.load()

            # Handle alpha for matching formats
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
            
            # Save
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
            arr = np.power(arr, 2.2) # To linear
            
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
