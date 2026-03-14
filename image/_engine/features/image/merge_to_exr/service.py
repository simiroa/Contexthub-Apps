import os
from pathlib import Path
from typing import List, Optional, Tuple, Callable, Dict
import threading
import numpy as np
from PIL import Image

from .state import ChannelConfig
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

logger = setup_logger("merge_to_exr_service")

class ExrMergeService:
    def get_missing_dependencies(self) -> List[str]:
        missing = []
        for module in ("cv2", "imageio", "OpenEXR", "Imath"):
            try:
                __import__(module)
            except Exception:
                missing.append(module)
        return missing

    def export_exr(self, 
                   base_dir: Path,
                   channels: List[ChannelConfig], 
                   all_files: List[Path],
                   on_progress: Callable[[float, str], None],
                   on_complete: Callable[[bool, str], None]):
        
        def _task():
            try:
                import cv2
                import imageio
                import OpenEXR
                import Imath
                
                active_configs = [c for c in channels if c.enabled and c.source_file]
                if not active_configs:
                    on_complete(False, "No layers defined or enabled.")
                    return

                on_progress(0.0, "Loading reference...")
                
                # Helper to find file path from filename
                def resolve_path(filename):
                    for f in all_files:
                        if f.name == filename:
                            return f
                    return None

                first_path = resolve_path(active_configs[0].source_file)
                if not first_path:
                    on_complete(False, f"Could not find: {active_configs[0].source_file}")
                    return

                # Load reference for dimensions
                ref_img = imageio.imread(first_path)
                h, w = ref_img.shape[:2]
                
                final_planes = {}
                total = len(active_configs)
                
                for i, cfg in enumerate(active_configs):
                    on_progress((i + 0.1) / total, f"Processing {cfg.target_name}...")
                    
                    f_path = resolve_path(cfg.source_file)
                    if not f_path: continue
                    
                    src = imageio.imread(f_path)
                    if src.shape[:2] != (h, w):
                        src = cv2.resize(src, (w, h), interpolation=cv2.INTER_LINEAR)
                    
                    # Normalize
                    data = src.astype(np.float32)
                    if src.dtype == np.uint8: 
                        data /= 255.0
                    elif src.dtype == np.uint16: 
                        data /= 65535.0
                    
                    if cfg.linear: 
                        data = np.power(np.maximum(data, 0), 2.2)
                    if cfg.invert: 
                        data = 1.0 - data
                    
                    # Map channels
                    mode = cfg.mode
                    layer = cfg.target_name
                    src_ch = 1 if len(data.shape) == 2 else data.shape[2]
                    
                    if mode == "RGB":
                        if src_ch == 1:
                            final_planes[f"{layer}.R"] = data
                            final_planes[f"{layer}.G"] = data
                            final_planes[f"{layer}.B"] = data
                        else:
                            final_planes[f"{layer}.R"] = data[:,:,0]
                            final_planes[f"{layer}.G"] = data[:,:,1] if src_ch > 1 else data[:,:,0]
                            final_planes[f"{layer}.B"] = data[:,:,2] if src_ch > 2 else data[:,:,0]
                    elif mode == "RGBA":
                        if src_ch == 1:
                            final_planes[f"{layer}.R"] = data
                            final_planes[f"{layer}.G"] = data
                            final_planes[f"{layer}.B"] = data
                            final_planes[f"{layer}.A"] = np.ones((h, w), dtype=np.float32)
                        else:
                            final_planes[f"{layer}.R"] = data[:,:,0]
                            final_planes[f"{layer}.G"] = data[:,:,1] if src_ch > 1 else data[:,:,0]
                            final_planes[f"{layer}.B"] = data[:,:,2] if src_ch > 2 else data[:,:,0]
                            final_planes[f"{layer}.A"] = data[:,:,3] if src_ch > 3 else np.ones((h, w), dtype=np.float32)
                    elif mode == "L":
                        if src_ch >= 3:
                            lum = 0.299*data[:,:,0] + 0.587*data[:,:,1] + 0.114*data[:,:,2]
                            final_planes[layer] = lum
                        elif src_ch == 1:
                            final_planes[layer] = data
                        else:
                            final_planes[layer] = data[:,:,0]
                    elif mode in ("R", "G", "B", "A"):
                        idx = {'R':0, 'G':1, 'B':2, 'A':3}.get(mode, 0)
                        plane = data[:,:,idx] if src_ch > idx else (data if src_ch==1 else data[:,:,0])
                        final_planes[layer] = plane

                    on_progress((i + 1) / total, f"Processed {layer}")

                # Save EXR
                on_progress(0.95, "Writing EXR file...")
                sorted_keys = sorted(final_planes.keys())
                header = OpenEXR.Header(w, h)
                header['compression'] = Imath.Compression(Imath.Compression.PIZ_COMPRESSION)
                
                exr_data = {}
                for key in sorted_keys:
                    header['channels'][key] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
                    exr_data[key] = final_planes[key].tobytes()
                
                out_path = base_dir / "MultiLayer_Output.exr"
                out = OpenEXR.OutputFile(str(out_path), header)
                out.writePixels(exr_data)
                out.close()
                
                on_complete(True, str(out_path))

            except Exception as e:
                logger.error(f"Export failed: {e}")
                on_complete(False, str(e))

        threading.Thread(target=_task, daemon=True).start()
