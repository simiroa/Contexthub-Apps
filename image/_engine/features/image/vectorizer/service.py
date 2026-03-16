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
from .state import LayerStateEntry, VectorizerState
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

try:
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtCore import Qt
except ImportError:
    QImage = QPixmap = None

logger = setup_logger("vectorizer_service")

try:
    from features.image.vectorizer.psd_parser import parse_psd, get_flat_layer_list
    HAS_PSD_TOOLS = True
except Exception:
    parse_psd = None
    get_flat_layer_list = None
    HAS_PSD_TOOLS = False

class VectorizerService:
    def __init__(self, state: VectorizerState | None = None):
        self._temp_dir = Path(tempfile.mkdtemp(prefix="vectorizer_flet_"))
        self.state = state or VectorizerState()

    def get_ui_definition(self) -> List[Dict]:
        return [
            {"key": "show_comparison", "label": "Enable Split Comparison", "type": "bool", "default": False},
            {"key": "speckle", "label": "Speckle Filter", "type": "int", "default": 4, "min": 0, "max": 100},
            {"key": "color_precision", "label": "Color Precision", "type": "int", "default": 6, "min": 1, "max": 8},
            {"key": "corner_threshold", "label": "Corner Threshold", "type": "int", "default": 60, "min": 0, "max": 100},
            {"key": "remove_bg", "label": "Remove Background (AI)", "type": "bool", "default": True},
            {"key": "use_anchor", "label": "Estimate Rigging Anchors", "type": "bool", "default": True},
            {"key": "gen_jsx", "label": "Generate AE Script (JSX)", "type": "bool", "default": True},
        ]

    def update_parameter(self, key: str, value: any):
        if hasattr(self.state, key):
            setattr(self.state, key, value)

    def get_workflow_names(self) -> List[str]:
        return ["Character Rig", "Flat Vector", "Logo Tracing"]

    def select_workflow(self, name: str):
        self.state.workflow_name = name
        if name == "Character Rig":
            self.state.use_anchor = True
            self.state.gen_jsx = True
            self.state.remove_bg = True
        elif name == "Flat Vector":
            self.state.use_anchor = False
            self.state.gen_jsx = False
            self.state.remove_bg = False
            self.state.color_precision = 8

    def add_inputs(self, paths: List[str]):
        if not paths: return
        # Force single source logic: only take the last one dropped/picked
        p = Path(paths[-1])
        self.state.source_path = p
        self.state.input_assets.clear()
        
        new_layers = self.load_files([p])
        self.state.input_assets.extend(new_layers)
        
        if self.state.input_assets:
            self.state.preview_uid = self.state.input_assets[0].uid

    def remove_input_at(self, index: int):
        # In single-input mode, this might just remove the layer from list 
        # or we might disable it if it's the only source
        if 0 <= index < len(self.state.input_assets):
            self.state.input_assets.pop(index)

    def clear_inputs(self):
        self.state.source_path = None
        self.state.input_assets.clear()
        self.state.preview_uid = None

    def set_preview_from_index(self, index: int):
        assets = self.state.output_assets if self.state.current_mode == "output" else self.state.input_assets
        if 0 <= index < len(assets):
            self.state.preview_uid = assets[index].uid

    def get_source_pixmap(self) -> Optional[QPixmap]:
        if not QPixmap or not self.state.source_path: return None
        return QPixmap(str(self.state.source_path))

    def get_preview_pixmap(self, uid: str) -> Optional[QPixmap]:
        if not QPixmap: return None
        
        # Check output assets first if in output mode
        assets = self.state.input_assets + self.state.output_assets
        for asset in assets:
            if asset.uid == uid:
                if isinstance(asset.data, Path):
                    path = asset.data
                    if path.suffix.lower() == '.svg':
                        # Basic SVG rendering for preview
                        # Note: In real production, we'd use QSvgRenderer
                        # For now, we'll try to load as image or return None
                        # ComparativePreviewWidget handles Pixmap, so we need a render.
                        try:
                            from PySide6.QtSvg import QSvgRenderer
                            from PySide6.QtGui import QPainter, QImage
                            renderer = QSvgRenderer(str(path))
                            if not renderer.isValid(): return None
                            img = QImage(asset.width or 512, asset.height or 512, QImage.Format_RGBA8888)
                            img.fill(Qt.transparent)
                            p = QPainter(img)
                            renderer.render(p)
                            p.end()
                            return QPixmap.fromImage(img)
                        except Exception:
                            return None
                    return QPixmap(str(path))
                elif hasattr(asset.data, 'image') and asset.data.image:
                    # PSD Layer case: Isolated viewing
                    pil_img = asset.data.image
                    if pil_img.mode != "RGBA":
                        pil_img = pil_img.convert("RGBA")
                    data = pil_img.tobytes("raw", "RGBA")
                    qimg = QImage(data, pil_img.size[0], pil_img.size[1], QImage.Format_RGBA8888)
                    return QPixmap.fromImage(qimg)
        return None

    def get_anchor_preview_data(self, uid: str) -> Optional[Dict]:
        """Returns anchor point position for visualization."""
        if not self.state.use_anchor: return None
        # We need the asset to get the name for estimation
        assets = self.state.input_assets + self.state.output_assets
        for asset in assets:
            if asset.uid == uid:
                anchor = estimate_anchor_point(asset.name, 0, 0, asset.width, asset.height)
                return {"x": anchor.x, "y": anchor.y, "name": anchor.duik_name}
        return None

    def update_output_options(self, path, prefix, open_folder, export_json):
        self.state.output_options.output_dir = path
        self.state.output_options.file_prefix = prefix
        self.state.output_options.open_folder_after_run = open_folder
        self.state.output_options.export_session_json = export_json

    def reveal_output_dir(self):
        if self.state.output_options.output_dir:
            os.startfile(self.state.output_options.output_dir)

    def run_workflow(self, on_complete: Callable = None) -> tuple[bool, str, any]:
        # Convert state to dict for run_vectorization
        config = {
            "filter_speckle": self.state.speckle,
            "color_precision": self.state.color_precision,
            "corner_threshold": self.state.corner_threshold,
        }
        options = {
            "remove_bg": self.state.remove_bg,
            "use_anchor": self.state.use_anchor,
            "gen_jsx": self.state.gen_jsx,
        }
        
        selected_layers = [a for a in self.state.input_assets if a.selected]
        if not selected_layers:
            return False, "No layers selected", None
            
        output_path = Path(self.state.output_options.output_dir or "vect_output")
        self.state.is_processing = True
        
        def _local_complete(success, message):
            self.state.is_processing = False
            if success:
                # Populate output_assets
                self.state.output_assets.clear()
                for layer in selected_layers:
                    svg_path = output_path / f"{layer.name}.svg"
                    if svg_path.exists():
                        self.state.output_assets.append(LayerStateEntry(
                            uid=f"res_{layer.uid}",
                            name=layer.name,
                            display_name=f"{layer.name}.svg",
                            width=layer.width,
                            height=layer.height,
                            data=svg_path
                        ))
                self.state.current_mode = "output"
                if self.state.output_assets:
                    self.state.preview_uid = self.state.output_assets[0].uid
            if on_complete:
                on_complete(success, message)

        self.run_vectorization(
            selected_layers,
            output_path,
            config,
            options,
            lambda p, t: setattr(self.state, 'progress', p),
            _local_complete
        )
        return True, "Processing started", None

    def load_files(self, paths: List[Path]) -> List[LayerStateEntry]:
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
