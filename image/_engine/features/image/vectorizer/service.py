import os
import gc
import tempfile
import threading
from pathlib import Path
from typing import List, Optional, Callable, Dict
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
from .state import LayerStateEntry
from features.image.vectorizer.vectorizer_core import vectorize_image, DEFAULT_CONFIG
from features.image.vectorizer.anchor_estimator import estimate_anchor_point
from features.image.vectorizer.svg_builder import (
    build_structured_svg,
    build_metadata_json,
    build_ae_jsx_script,
    parse_svg_document,
    save_individual_svgs,
    LayerSVG
)

logger = setup_logger("vectorizer_service")

try:
    from features.image.vectorizer.psd_parser import parse_psd, get_flat_layer_list
    HAS_PSD_TOOLS = True
except Exception:
    parse_psd = None
    get_flat_layer_list = None
    HAS_PSD_TOOLS = False

class VectorizerService:
    def __init__(self):
        self._temp_dir = Path(tempfile.mkdtemp(prefix="vectorizer_flet_"))

    def get_missing_dependencies(self) -> List[str]:
        missing = []
        if not HAS_PSD_TOOLS:
            missing.append("psd_tools")
        try:
            import vtracer  # noqa: F401
        except Exception:
            missing.append("vtracer")
        return missing

    def load_files(self, paths: List[Path]) -> List[LayerStateEntry]:
        results = []
        for path in paths:
            if not path.exists(): continue
            ext = path.suffix.lower()
            
            if ext in ('.psd', '.psb'):
                if not HAS_PSD_TOOLS or parse_psd is None or get_flat_layer_list is None:
                    logger.error("PSD support unavailable: install psd_tools to load PSD/PSB files.")
                    continue
                try:
                    psd_data = parse_psd(path, include_hidden=False)
                    flat = get_flat_layer_list(psd_data)
                    for layer in flat:
                        results.append(LayerStateEntry(
                            uid=layer.uid,
                            name=layer.name,
                            display_name=layer.path if hasattr(layer, 'path') else layer.name,
                            width=layer.width,
                            height=layer.height,
                            data=layer,
                            is_text=getattr(layer, 'is_text', False),
                            is_smart_object=getattr(layer, 'is_smart_object', False)
                        ))
                except Exception as e:
                    logger.error(f"PSD Parse Error: {e}")
            else:
                try:
                    with Image.open(path) as img:
                        w, h = img.size
                        results.append(LayerStateEntry(
                            uid=str(path),
                            name=path.stem,
                            display_name=path.name,
                            width=w,
                            height=h,
                            data=path
                        ))
                except Exception as e:
                    logger.error(f"Image Load Error: {e}")
        return results

    def run_vectorization(self, 
                          selected_layers: List[LayerStateEntry],
                          output_dir: Path,
                          config: Dict,
                          options: Dict,
                          on_progress: Callable[[float, str], None],
                          on_complete: Callable[[bool, str], None]):
        
        def _task():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                total = len(selected_layers)
                prepared = []

                # Phase 1: Preparation
                for i, layer in enumerate(selected_layers):
                    on_progress((i * 0.4) / total, f"Preparing: {layer.name}")
                    
                    if hasattr(layer.data, 'image') and layer.data.image:
                        img = layer.data.image
                        ox, oy = layer.data.offset_x, layer.data.offset_y
                        w, h = layer.data.width, layer.data.height
                        parent_uid = getattr(layer.data, 'parent_uid', None)
                    else:
                        img = Image.open(layer.data)
                        ox, oy = 0, 0
                        w, h = img.size
                        parent_uid = None

                    if options.get("remove_bg") and img.mode not in ('RGBA', 'LA'):
                        on_progress((i * 0.4) / total, f"Removing BG: {layer.name}")
                        try:
                            from rembg import remove
                            img = remove(img)
                        except Exception as e:
                            logger.error(f"Rembg failed: {e}")

                    safe_uid = layer.uid.replace("/", "_").replace("\\", "_").replace(":", "_")
                    temp_png = self._temp_dir / f"{safe_uid}.png"
                    img.save(temp_png, format="PNG")
                    
                    prepared.append({
                        'uid': layer.uid,
                        'name': layer.name,
                        'temp_png': temp_png,
                        'offset_x': ox,
                        'offset_y': oy,
                        'width': w,
                        'height': h,
                        'parent_uid': parent_uid,
                        'vector_mask_d': getattr(layer.data, 'vector_mask_d', None)
                    })
                    gc.collect()

                # Phase 2: Vectorization & Analysis
                final_layers = []
                for i, layer_data in enumerate(prepared):
                    on_progress(0.4 + (i * 0.5) / total, f"Tracing: {layer_data['name']}")
                    
                    if layer_data.get('vector_mask_d'):
                        # Shape layer extraction
                        svg_content = self._get_shape_svg(layer_data)
                    else:
                        # VTracer tracing
                        svg_content = vectorize_image(layer_data['temp_png'], config=config)

                    paths, _, _ = parse_svg_document(svg_content, layer_data['width'], layer_data['height'])

                    if options.get("use_anchor"):
                        anchor = estimate_anchor_point(layer_data['name'], layer_data['offset_x'], layer_data['offset_y'], layer_data['width'], layer_data['height'])
                        ax, ay = anchor.x, anchor.y
                        duik_name = anchor.duik_name
                    else:
                        ax = layer_data['offset_x'] + (layer_data['width'] / 2)
                        ay = layer_data['offset_y'] + (layer_data['height'] / 2)
                        duik_name = None

                    final_layers.append(LayerSVG(
                        name=layer_data['name'],
                        uid=layer_data['uid'],
                        path=layer_data['name'],
                        offset_x=layer_data['offset_x'],
                        offset_y=layer_data['offset_y'],
                        width=layer_data['width'],
                        height=layer_data['height'],
                        anchor_x=ax,
                        anchor_y=ay,
                        is_group=False,
                        duik_name=duik_name,
                        parent_uid=layer_data['parent_uid'],
                        svg_paths=paths
                    ))

                # Phase 3: Finalize
                on_progress(0.9, "Saving results...")
                save_individual_svgs(final_layers, output_dir)
                
                if options.get("gen_jsx"):
                    build_ae_jsx_script(final_layers, output_dir / "setup_rig.jsx")
                
                build_metadata_json(final_layers, output_dir / "metadata.json")
                
                on_complete(True, f"Success: Vectorized {total} layers.")
            except Exception as e:
                logger.error(f"Vectorization failed: {e}")
                on_complete(False, str(e))

        threading.Thread(target=_task, daemon=True).start()

    def _get_shape_svg(self, layer_data):
        # Simplified shape extraction logic from legacy GUI
        w, h = layer_data['width'], layer_data['height']
        ox, oy = layer_data['offset_x'], layer_data['offset_y']
        d = layer_data['vector_mask_d']
        return f'<svg width="{w}" height="{h}"><g transform="translate({-ox}, {-oy})"><path d="{d}" fill="#000000" /></g></svg>'
