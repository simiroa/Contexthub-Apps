import os
import re
import threading
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np

from .state import ChannelConfig, ExrMergeState

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

DEFAULT_MODE = "RGB"
KEYWORD_MAP = [
    ("beauty", ("beauty", "basecolor", "albedo", "diffuse", "color"), "RGB"),
    ("specular", ("specular", "spec"), "RGB"),
    ("reflection", ("reflection", "reflect"), "RGB"),
    ("shadow", ("shadow",), "RGB"),
    ("normal", ("normal", "nrm"), "RGB"),
    ("roughness", ("roughness", "rough"), "L"),
    ("metallic", ("metallic", "metalness", "metal"), "L"),
    ("ao", ("ao", "occlusion", "ambient"), "L"),
    ("opacity", ("alpha", "opacity", "mask"), "A"),
    ("height", ("height", "disp", "displacement"), "L"),
    ("emission", ("emission", "emissive"), "RGB"),
]


class ExrMergeService:
    def __init__(self) -> None:
        self.state = ExrMergeState()

    def get_missing_dependencies(self) -> List[str]:
        missing = []
        for module in ("cv2", "imageio", "OpenEXR", "Imath"):
            try:
                __import__(module)
            except Exception:
                missing.append(module)
        return missing

    def add_inputs(self, paths: List[str]) -> None:
        added = False
        for raw in paths:
            path = Path(raw)
            if not path.exists():
                continue
            if path in self.state.files:
                continue
            self.state.files.append(path)
            self.state.channels.append(self._build_channel_config(path))
            added = True
        if added:
            self.state.selected_index = 0 if self.state.selected_index < 0 else self.state.selected_index
            self._refresh_common_prefix()
        self._sync_status()

    def remove_selected(self) -> None:
        index = self.state.selected_index
        if 0 <= index < len(self.state.files):
            self.state.files.pop(index)
            self.state.channels.pop(index)
        if not self.state.files:
            self.state.selected_index = -1
        else:
            self.state.selected_index = min(index, len(self.state.files) - 1)
        self._refresh_common_prefix()
        self._sync_status()

    def clear_inputs(self) -> None:
        self.state.files.clear()
        self.state.channels.clear()
        self.state.selected_index = -1
        self.state.common_prefix = ""
        self._sync_status()

    def move_selected_up(self) -> bool:
        index = self.state.selected_index
        if index <= 0 or index >= len(self.state.files):
            return False
        self.state.files[index - 1], self.state.files[index] = self.state.files[index], self.state.files[index - 1]
        self.state.channels[index - 1], self.state.channels[index] = self.state.channels[index], self.state.channels[index - 1]
        self.state.selected_index = index - 1
        self._sync_status()
        return True

    def move_selected_down(self) -> bool:
        index = self.state.selected_index
        if index < 0 or index >= len(self.state.files) - 1:
            return False
        self.state.files[index + 1], self.state.files[index] = self.state.files[index], self.state.files[index + 1]
        self.state.channels[index + 1], self.state.channels[index] = self.state.channels[index], self.state.channels[index + 1]
        self.state.selected_index = index + 1
        self._sync_status()
        return True

    def set_selected_index(self, index: int) -> None:
        if 0 <= index < len(self.state.channels):
            self.state.selected_index = index
        elif not self.state.channels:
            self.state.selected_index = -1
        self._sync_status()

    def selected_channel(self) -> Optional[ChannelConfig]:
        index = self.state.selected_index
        if 0 <= index < len(self.state.channels):
            return self.state.channels[index]
        return None

    def update_channel(self, index: int, **changes: object) -> None:
        if not (0 <= index < len(self.state.channels)):
            return
        channel = self.state.channels[index]
        for key, value in changes.items():
            if hasattr(channel, key):
                setattr(channel, key, value)
        self._sync_status()

    def update_output_options(
        self,
        output_dir: str,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        self.state.output_options.output_dir = Path(output_dir).expanduser()
        self.state.output_options.file_prefix = file_prefix.strip() or "MultiLayer_Output"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    def reveal_output_dir(self) -> None:
        path = self.state.output_options.output_dir
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)

    def build_output_path(self) -> Path:
        base_dir = self.state.output_options.output_dir
        prefix = self.state.output_options.file_prefix.strip() or "MultiLayer_Output"
        path = base_dir / f"{prefix}.exr"
        counter = 2
        while path.exists():
            path = base_dir / f"{prefix}_{counter}.exr"
            counter += 1
        return path

    def export_exr(
        self,
        on_progress: Callable[[float, str], None],
        on_complete: Callable[[bool, str], None],
    ) -> None:
        missing = self.get_missing_dependencies()
        if missing:
            on_complete(False, f"Missing dependencies: {', '.join(missing)}")
            return

        def _task():
            try:
                import cv2
                import imageio
                import OpenEXR
                import Imath

                active_configs = [c for c in self.state.channels if c.enabled and c.source_file]
                if not active_configs:
                    on_complete(False, "No enabled layers to export.")
                    return

                self.state.is_exporting = True
                self.state.error_text = ""
                self.state.status_text = "Preparing EXR export..."
                output_path = self.build_output_path()

                def resolve_path(filename: str | None) -> Optional[Path]:
                    if not filename:
                        return None
                    for file_path in self.state.files:
                        if file_path.name == filename:
                            return file_path
                    return None

                first_path = resolve_path(active_configs[0].source_file)
                if not first_path:
                    on_complete(False, f"Could not find: {active_configs[0].source_file}")
                    return

                on_progress(0.0, "Loading reference image...")
                ref_img = imageio.imread(first_path)
                h, w = ref_img.shape[:2]
                final_planes = {}
                total = len(active_configs)

                for i, cfg in enumerate(active_configs):
                    on_progress((i + 0.1) / total, f"Processing {cfg.target_name}...")
                    file_path = resolve_path(cfg.source_file)
                    if not file_path:
                        continue
                    src = imageio.imread(file_path)
                    if src.shape[:2] != (h, w):
                        src = cv2.resize(src, (w, h), interpolation=cv2.INTER_LINEAR)

                    data = src.astype(np.float32)
                    if src.dtype == np.uint8:
                        data /= 255.0
                    elif src.dtype == np.uint16:
                        data /= 65535.0

                    if cfg.linear:
                        data = np.power(np.maximum(data, 0), 2.2)
                    if cfg.invert:
                        data = 1.0 - data

                    src_ch = 1 if len(data.shape) == 2 else data.shape[2]
                    layer = cfg.target_name or self._fallback_layer_name(file_path)
                    mode = cfg.mode

                    if mode == "RGB":
                        if src_ch == 1:
                            final_planes[f"{layer}.R"] = data
                            final_planes[f"{layer}.G"] = data
                            final_planes[f"{layer}.B"] = data
                        else:
                            final_planes[f"{layer}.R"] = data[:, :, 0]
                            final_planes[f"{layer}.G"] = data[:, :, 1] if src_ch > 1 else data[:, :, 0]
                            final_planes[f"{layer}.B"] = data[:, :, 2] if src_ch > 2 else data[:, :, 0]
                    elif mode == "RGBA":
                        if src_ch == 1:
                            final_planes[f"{layer}.R"] = data
                            final_planes[f"{layer}.G"] = data
                            final_planes[f"{layer}.B"] = data
                            final_planes[f"{layer}.A"] = np.ones((h, w), dtype=np.float32)
                        else:
                            final_planes[f"{layer}.R"] = data[:, :, 0]
                            final_planes[f"{layer}.G"] = data[:, :, 1] if src_ch > 1 else data[:, :, 0]
                            final_planes[f"{layer}.B"] = data[:, :, 2] if src_ch > 2 else data[:, :, 0]
                            final_planes[f"{layer}.A"] = data[:, :, 3] if src_ch > 3 else np.ones((h, w), dtype=np.float32)
                    elif mode == "L":
                        if src_ch >= 3:
                            final_planes[layer] = 0.299 * data[:, :, 0] + 0.587 * data[:, :, 1] + 0.114 * data[:, :, 2]
                        elif src_ch == 1:
                            final_planes[layer] = data
                        else:
                            final_planes[layer] = data[:, :, 0]
                    elif mode in ("R", "G", "B", "A"):
                        idx = {"R": 0, "G": 1, "B": 2, "A": 3}[mode]
                        final_planes[layer] = data[:, :, idx] if src_ch > idx else (data if src_ch == 1 else data[:, :, 0])

                    on_progress((i + 1) / total, f"Processed {layer}")

                on_progress(0.96, "Writing EXR file...")
                sorted_keys = sorted(final_planes.keys())
                header = OpenEXR.Header(w, h)
                header["compression"] = Imath.Compression(Imath.Compression.PIZ_COMPRESSION)
                exr_data = {}

                def _resolve_depth_for_plane(plane_name: str) -> str:
                    layer_name = plane_name.split(".", 1)[0]
                    for cfg in active_configs:
                        cfg_layer = cfg.target_name or self._fallback_layer_name(resolve_path(cfg.source_file) or Path(layer_name))
                        if cfg_layer == layer_name:
                            return cfg.depth
                    return "HALF"

                for key in sorted_keys:
                    depth = _resolve_depth_for_plane(key)
                    header["channels"][key] = Imath.Channel(self._pixel_type_from_depth(depth, Imath))
                    exr_data[key] = self._plane_bytes_for_depth(final_planes[key], depth)

                output = OpenEXR.OutputFile(str(output_path), header)
                output.writePixels(exr_data)
                output.close()

                self.state.output_path = output_path
                self.state.is_exporting = False
                self.state.progress = 1.0
                self.state.status_text = "EXR export complete"
                self.state.detail_text = output_path.name
                on_complete(True, str(output_path))
            except Exception as exc:
                logger.error(f"Export failed: {exc}")
                self.state.is_exporting = False
                self.state.error_text = str(exc)
                self.state.status_text = "Export failed"
                on_complete(False, str(exc))

        threading.Thread(target=_task, daemon=True).start()

    def _build_channel_config(self, path: Path) -> ChannelConfig:
        target_name, mode = self._suggest_target_name_and_mode(path)
        return ChannelConfig(
            source_file=path.name,
            target_name=target_name,
            mode=mode,
            depth="HALF",
            invert=False,
            linear=False,
            enabled=True,
        )

    def _suggest_target_name_and_mode(self, path: Path) -> tuple[str, str]:
        stem = path.stem.lower()
        sanitized = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
        for label, keywords, mode in KEYWORD_MAP:
            if any(keyword in stem for keyword in keywords):
                return label, mode
        if sanitized:
            return sanitized, DEFAULT_MODE
        return "layer", DEFAULT_MODE

    def _fallback_layer_name(self, path: Path) -> str:
        return re.sub(r"[^A-Za-z0-9_]+", "_", path.stem).strip("_") or "layer"

    def _pixel_type_from_depth(self, depth: str, Imath):
        depth_key = (depth or "HALF").upper()
        if depth_key == "FLOAT":
            return Imath.PixelType(Imath.PixelType.FLOAT)
        if depth_key == "UINT":
            return Imath.PixelType(Imath.PixelType.UINT)
        return Imath.PixelType(Imath.PixelType.HALF)

    def _plane_bytes_for_depth(self, plane: np.ndarray, depth: str) -> bytes:
        depth_key = (depth or "HALF").upper()
        clipped = np.clip(plane, 0.0, 1.0)
        if depth_key == "FLOAT":
            return clipped.astype(np.float32).tobytes()
        if depth_key == "UINT":
            return (clipped * np.iinfo(np.uint32).max).astype(np.uint32).tobytes()
        return clipped.astype(np.float16).tobytes()

    def _refresh_common_prefix(self) -> None:
        stems = [path.stem for path in self.state.files]
        if not stems:
            self.state.common_prefix = ""
            return
        self.state.common_prefix = os.path.commonprefix(stems).rstrip("_-. ")

    def _sync_status(self) -> None:
        count = len(self.state.channels)
        enabled = len([channel for channel in self.state.channels if channel.enabled])
        if count == 0:
            self.state.status_text = "Ready"
            self.state.detail_text = "Add source images to build EXR layers."
            return
        self.state.status_text = f"{enabled}/{count} layer{'s' if count != 1 else ''} enabled"
        selected = self.selected_channel()
        self.state.detail_text = selected.target_name if selected else ""
