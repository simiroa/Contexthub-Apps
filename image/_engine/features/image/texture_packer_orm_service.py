import os
import re
import io
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

logger = setup_logger("texture_packer_service")

KEYWORD_PATTERNS = {
    "occlusion": ["*occlusion*", "*ao*", "*ambient*"],
    "roughness": ["*roughness*", "*rough*", "*gloss*"],
    "metallic": ["*metallic*", "*metal*", "*metalness*"],
    "smoothness": ["*smoothness*", "*smooth*"],
    "detail": ["*detail*", "*mask*"],
    "alpha": ["*alpha*", "*opacity*", "*transparent*"],
    "height": ["*height*", "*disp*"],
    "displacement": ["*displacement*", "*disp*"],
    "specular": ["*specular*", "*spec*"]
}

class TexturePackerService:
    def __init__(self):
        self._cancel_flag = False

    def auto_parse(self, target_path: Path, labels: Dict[str, str]) -> Dict[str, Path]:
        if not target_path: return {}
        search_dir = target_path.parent if target_path.is_file() else target_path
        base_name = target_path.stem if target_path.is_file() else ""
        base_name = re.sub(r'_(occlusion|roughness|metallic|ao|rough|metal|orm|base|albedo|diffuse|nrm|normal|mask).*', 
                           '', base_name, flags=re.IGNORECASE)
        img_exts = {'.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr'}
        results = {}
        for key, label in labels.items():
            if not label: continue
            label_lower = label.lower().strip()
            patterns = []
            for kw, pats in KEYWORD_PATTERNS.items():
                if kw in label_lower:
                    patterns.extend(pats)
            if not patterns:
                patterns = [f"*{label_lower}*"]
            for pattern in patterns:
                matches = list(search_dir.glob(f"{base_name}{pattern}"))
                matches = [m for m in matches if m.suffix.lower() in img_exts]
                if not matches:
                    matches = list(search_dir.glob(pattern))
                    matches = [m for m in matches if m.suffix.lower() in img_exts]
                if matches:
                    results[key] = matches[0]
                    break
        return results

    def pack_textures(self, slots: Dict[str, Optional[Path]], labels: Dict[str, str], output_path: Path, resize_size: Optional[Tuple[int, int]], on_complete: Callable[[bool, str], None]):
        def _task():
            try:
                target_size = resize_size
                if not target_size:
                    max_w, max_h = 0, 0
                    for p in slots.values():
                        if p:
                            with Image.open(p) as tmp:
                                w, h = tmp.size
                                if w > max_w: max_w = w
                                if h > max_h: max_h = h
                    if max_w == 0: raise ValueError("No textures loaded")
                    target_size = (max_w, max_h)
                final_channels = []
                keys = ['r', 'g', 'b', 'a']
                for key in keys:
                    path = slots.get(key)
                    label = labels.get(key, "").lower()
                    if path:
                        with Image.open(path) as img:
                            gray = img.convert('L')
                            # Check for inversion (passed via labels or extra dict if we want to be cleaner)
                            # Let's assume labels can contain metadata or just use a separate dict
                            if labels.get(f"{key}_invert"):
                                from PIL import ImageOps
                                gray = ImageOps.invert(gray)
                                
                            if gray.size != target_size:
                                gray = gray.resize(target_size, Image.Resampling.LANCZOS)
                            final_channels.append(gray)
                    else:
                        val = 0
                        if any(kw in label for kw in ["rough", "occlusion", "ao", "alpha", "opacity"]):
                            val = 255
                        final_channels.append(Image.new('L', target_size, val))
                has_alpha_input = (slots.get('a') is not None)
                if has_alpha_input:
                    mode = 'RGBA'
                    merged = Image.merge(mode, final_channels)
                else:
                    mode = 'RGB'
                    merged = Image.merge(mode, final_channels[:3])
                ext = output_path.suffix.lower()
                if ext == ".exr":
                    self._save_exr(merged, output_path, labels if has_alpha_input else {k: labels[k] for k in ['r','g','b']})
                else:
                    save_kwargs = {}
                    if ext in ['.jpg', '.jpeg']:
                        merged = merged.convert('RGB')
                        save_kwargs['quality'] = 95
                    merged.save(output_path, **save_kwargs)
                on_complete(True, str(output_path))
            except Exception as e:
                logger.error(f"Packing failed: {e}")
                on_complete(False, str(e))
        threading.Thread(target=_task, daemon=True).start()

    def _save_exr(self, img: Image.Image, path: Path, labels: Dict[str, str]):
        if not HAS_EXR: raise ImportError("OpenEXR not available")
        w, h = img.size
        header = OpenEXR.Header(w, h)
        header['compression'] = Imath.Compression(Imath.Compression.PIZ_COMPRESSION)
        channels = list(img.split())
        chan_data = {}
        names = ['R', 'G', 'B', 'A'] if len(channels) == 4 else ['R', 'G', 'B']
        slot_keys = ['r', 'g', 'b', 'a']
        for i, name in enumerate(names):
            header['channels'][name] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
            arr = np.array(channels[i], dtype=np.float32) / 255.0
            chan_data[name] = arr.tobytes()
            label = labels.get(slot_keys[i])
            if label:
                header[f"ContextUp_Channel_{name}"] = label
        out = OpenEXR.OutputFile(str(path), header)
        out.writePixels(chan_data)
        out.close()

    def get_preview_bytes(self, img_pil: Image.Image) -> bytes:
        buf = io.BytesIO()
        img_pil.save(buf, format="PNG")
        return buf.getvalue()
