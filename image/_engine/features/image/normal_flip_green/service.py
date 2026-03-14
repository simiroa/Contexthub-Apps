import os
from pathlib import Path
from typing import List, Optional, Tuple, Callable
import threading
import numpy as np
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

logger = setup_logger("normal_flip_service")

class NormalFlipService:
    def flip_green_batch(self, 
                         files: List[Path], 
                         on_progress: Callable[[float, str], None],
                         on_complete: Callable[[int, List[str]], None]):
        
        def _task():
            count = 0
            errors = []
            total = len(files)
            
            for i, path in enumerate(files):
                try:
                    on_progress(i / total, f"Processing: {path.name}")
                    
                    if not path.exists():
                        errors.append(f"{path.name}: File not found")
                        continue

                    img = Image.open(path)
                    
                    # Ensure RGB/RGBA
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGBA' if 'A' in img.mode else 'RGB')
                    
                    arr = np.array(img)
                    
                    # Flip Green channel (index 1)
                    # Support both 8-bit and 16-bit
                    if arr.dtype == np.uint8:
                        arr[:, :, 1] = 255 - arr[:, :, 1]
                    elif arr.dtype == np.uint16:
                        arr[:, :, 1] = 65535 - arr[:, :, 1]
                    else:
                        # Fallback for floats or other types
                        max_val = np.max(arr[:, :, 1])
                        arr[:, :, 1] = max_val - arr[:, :, 1]
                    
                    result = Image.fromarray(arr)
                    out_path = path.parent / f"{path.stem}_flipped{path.suffix}"
                    result.save(out_path)
                    
                    logger.info(f"Saved: {out_path}")
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to flip {path.name}: {e}")
                    errors.append(f"{path.name}: {str(e)}")

            on_complete(count, errors)

        threading.Thread(target=_task, daemon=True).start()
