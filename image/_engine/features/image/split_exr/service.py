import os
import threading
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
from PIL import Image
try:
    import OpenEXR
    import Imath
    HAS_EXR = True
except ImportError:
    HAS_EXR = False

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

logger = setup_logger("split_exr_service")

class SplitExrService:
    def __init__(self):
        self._cancel_flag = False

    def is_exr_supported(self) -> bool:
        return HAS_EXR

    def analyze_file(self, path: Path) -> Tuple[str, List[Dict]]:
        """
        Analyze the first file to get layer configuration.
        Returns (info_text, layers_info)
        """
        if not path.exists():
            return "File not found", []
            
        suffix = path.suffix.lower()
        if suffix == ".exr":
            if not HAS_EXR:
                return "OpenEXR library missing", []
            return self._analyze_exr(path)
        else:
            return self._analyze_generic(path)

    def _analyze_exr(self, path: Path) -> Tuple[str, List[Dict]]:
        try:
            exr_file = OpenEXR.InputFile(str(path))
            header = exr_file.header()
            dw = header['dataWindow']
            w = dw.max.x - dw.min.x + 1
            h = dw.max.y - dw.min.y + 1
            
            channels = list(header['channels'].keys())
            layer_groups = self._group_channels_to_layers(channels)
            
            layers_info = []
            for name, chans in layer_groups.items():
                layers_info.append({
                    "name": name,
                    "channels": chans,
                    "default_suffix": f"_{name.replace('/', '_')}"
                })
                
            info = f"EXR | {w}x{h} | {len(layers_info)} Layers"
            return info, layers_info
        except Exception as e:
            logger.error(f"EXR analyze failed: {e}")
            return f"Error: {e}", []

    def _analyze_generic(self, path: Path) -> Tuple[str, List[Dict]]:
        try:
            with Image.open(path) as img:
                w, h = img.size
                bands = img.getbands()
                
                name_map = {'R': 'Red', 'G': 'Green', 'B': 'Blue', 'A': 'Alpha', 'L': 'Gray', 'P': 'Palette'}
                layers_info = []
                for band in bands:
                    name = name_map.get(band, band)
                    layers_info.append({
                        "name": name,
                        "channels": [band],
                        "default_suffix": f"_{name}"
                    })
                
                info = f"{img.format} | {w}x{h} | {len(bands)} Channels"
                return info, layers_info
        except Exception as e:
            logger.error(f"Generic analyze failed: {e}")
            return f"Error: {e}", []

    def _group_channels_to_layers(self, channels: List[str]) -> Dict[str, List[str]]:
        layers = {}
        for chan in channels:
            parts = chan.split('.')
            layer_name = ".".join(parts[:-1]) if len(parts) > 1 else "Main"
            if layer_name not in layers:
                layers[layer_name] = []
            layers[layer_name].append(chan)
        return layers

    def run_batch_split(self, 
                       files: List[Path], 
                       layer_configs: List[Dict], # {name, invert, suffix}
                       format_ext: str,
                       on_progress: Callable[[float, str], None],
                       on_complete: Callable[[int, List[str]], None]):
        
        self._cancel_flag = False
        
        def _task():
            success = 0
            errors = []
            total = len(files)
            
            for i, f_path in enumerate(files):
                if self._cancel_flag: break
                try:
                    on_progress(i / total, f"Splitting: {f_path.name}")
                    
                    out_dir = f_path.parent / f"{f_path.stem}_split"
                    out_dir.mkdir(exist_ok=True)
                    
                    if f_path.suffix.lower() == ".exr":
                        self._split_exr(f_path, layer_configs, out_dir, format_ext)
                    else:
                        self._split_generic(f_path, layer_configs, out_dir, format_ext)
                        
                    success += 1
                except Exception as e:
                    logger.error(f"Failed to split {f_path.name}: {e}")
                    errors.append(f"{f_path.name}: {e}")
            
            on_complete(success, errors)

        threading.Thread(target=_task, daemon=True).start()

    def _split_exr(self, path: Path, configs: List[Dict], out_dir: Path, out_format: str):
        exr_file = OpenEXR.InputFile(str(path))
        header = exr_file.header()
        dw = header['dataWindow']
        w = dw.max.x - dw.min.x + 1
        h = dw.max.y - dw.min.y + 1
        
        # We need to find channels for this specific file too
        f_channels = list(header['channels'].keys())
        f_layer_map = self._group_channels_to_layers(f_channels)
        
        for cfg in configs:
            layer_name = cfg['name']
            if layer_name not in f_layer_map: continue
            
            channels = f_layer_map[layer_name]
            do_invert = cfg['invert']
            suffix = cfg['suffix']
            
            # Sort channels
            def chan_sort_key(name):
                s = name.split('.')[-1]
                return {'R':0, 'G':1, 'B':2, 'A':3}.get(s, 99)
            
            sorted_chans = sorted(channels, key=chan_sort_key)
            pt = Imath.PixelType(Imath.PixelType.FLOAT)
            bytes_list = exr_file.channels(sorted_chans, pt)
            
            out_base = f"{path.stem}{suffix}"
            
            if out_format.lower() == "exr":
                new_header = OpenEXR.Header(w, h)
                chan_data = {}
                for idx, old_name in enumerate(sorted_chans):
                    s_name = old_name.split('.')[-1]
                    new_header['channels'][s_name] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
                    chan_data[s_name] = bytes_list[idx]
                out = OpenEXR.OutputFile(str(out_dir / f"{out_base}.exr"), new_header)
                out.writePixels(chan_data)
                out.close()
            else:
                arrays = []
                for b in bytes_list:
                    arr = np.frombuffer(b, dtype=np.float32).reshape(h, w)
                    arrays.append(arr)
                
                if len(arrays) == 1: img = arrays[0]
                elif len(arrays) >= 3: img = np.dstack(arrays[:3])
                else: img = np.dstack([arrays[0], arrays[1], np.zeros_like(arrays[0])])
                
                if do_invert: img = 1.0 - img
                img = np.nan_to_num(img)
                img = np.power(np.clip(img, 0, 1), 1/2.2) * 255
                pil_img = Image.fromarray(img.astype(np.uint8))
                pil_img.save(out_dir / f"{out_base}.{out_format.lower()}")

    def _split_generic(self, path: Path, configs: List[Dict], out_dir: Path, out_format: str):
        with Image.open(path) as img:
            img.load()
            bands = img.split()
            band_names = img.getbands()
            band_dict = {n: b for n, b in zip(band_names, bands)}
            
            # Note: Generic split logic expects a one-to-one mapping for now (R -> Red)
            # which is what our analyze_generic creates.
            for cfg in configs:
                # For generic, cfg['channels'] index 0 is our best bet
                # Need to map back Layer name to Band key if channels not provided in cfg
                layer_name = cfg['name']
                do_invert = cfg['invert']
                suffix = cfg['suffix']
                
                # In state, we should store band key in cfg. 
                # For now, let's look it up or assume it's there.
                band_key = cfg.get('channel_key')
                if not band_key:
                    # Fallback mapping
                    map_inv = {'Red':'R', 'Green':'G', 'Blue':'B', 'Alpha':'A', 'Gray':'L'}
                    band_key = map_inv.get(layer_name, layer_name[0] if layer_name else None)
                
                if band_key in band_dict:
                    band_img = band_dict[band_key]
                    if do_invert:
                        band_img = Image.eval(band_img, lambda x: 255 - x)
                    out_base = f"{path.stem}{suffix}"
                    band_img.save(out_dir / f"{out_base}.{out_format.lower()}")
