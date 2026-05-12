from __future__ import annotations

import copy
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from features.comfyui import ai_upscaler_comfy_bridge as bridge
from features.comfyui.image_enhancer_state import (
    IMAGE_EXTS,
    EnhanceLayer,
    ImageEnhancerState,
    InputAsset,
    WORKFLOW_CHOICES,
)


class ImageEnhancerService:
    def __init__(self) -> None:
        self.state = ImageEnhancerState()
        self.state.parameter_values = {
            "scale": self.state.scale,
            "seed": self.state.seed,
            "use_seed": self.state.use_seed,
        }

    # ---------- inputs ----------
    def add_inputs(self, paths_list: list[str]) -> None:
        for raw_path in paths_list:
            path = Path(raw_path)
            if not path.exists():
                continue
            if path.is_dir():
                candidates = [p for p in path.iterdir() if p.suffix.lower() in IMAGE_EXTS]
            elif path.suffix.lower() in IMAGE_EXTS:
                candidates = [path]
            else:
                continue
            for item in candidates:
                if any(asset.path == item for asset in self.state.input_assets):
                    continue
                self.state.input_assets.append(InputAsset(path=item, kind="image"))
        if self.state.input_assets:
            if self.state.selected_input_index < 0:
                self.select_input(0)
            elif self.state.preview_path is None:
                self.select_input(min(self.state.selected_input_index, len(self.state.input_assets) - 1))

    def remove_input_at(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            removed = self.state.input_assets.pop(index)
            if self.state.preview_path == removed.path:
                if self.state.input_assets:
                    self.select_input(max(0, min(index, len(self.state.input_assets) - 1)))
                else:
                    self.state.preview_path = None
                    self.state.selected_input_index = -1
                    self.state.active_mask_path = None

    def clear_inputs(self) -> None:
        self.state.input_assets.clear()
        self.state.preview_path = None
        self.state.selected_input_index = -1
        self.state.active_mask_path = None

    def select_input(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            self.state.selected_input_index = index
            self.state.preview_path = self.state.input_assets[index].path
            self.state.active_mask_path = self.state.input_assets[index].mask_path

    def current_input(self) -> InputAsset | None:
        if 0 <= self.state.selected_input_index < len(self.state.input_assets):
            return self.state.input_assets[self.state.selected_input_index]
        if self.state.input_assets:
            return self.state.input_assets[0]
        return None

    def set_input_mask(self, index: int, mask_path: Path | None) -> None:
        if 0 <= index < len(self.state.input_assets):
            self.state.input_assets[index].mask_path = mask_path
            if index == self.state.selected_input_index:
                self.state.active_mask_path = mask_path

    def mask_path_for_input(self, index: int) -> Path | None:
        if not (0 <= index < len(self.state.input_assets)):
            return None
        asset = self.state.input_assets[index]
        out_dir = self.resolve_output_dir() or asset.path.parent / "enhanced"
        mask_dir = out_dir / ".masks"
        return mask_dir / f"{asset.path.stem}_mask.png"

    # ---------- layers ----------
    def add_layer(self, name: str = "Detail Layer") -> None:
        self.state.layers.append(EnhanceLayer(name=name))
        self.state.selected_layer_index = len(self.state.layers) - 1

    def duplicate_layer(self, index: int) -> None:
        if 0 <= index < len(self.state.layers):
            layer = copy.deepcopy(self.state.layers[index])
            layer.name = f"{layer.name} Copy"
            self.state.layers.insert(index + 1, layer)
            self.state.selected_layer_index = index + 1

    def remove_layer(self, index: int) -> None:
        if 0 <= index < len(self.state.layers) and len(self.state.layers) > 1:
            self.state.layers.pop(index)
            self.state.selected_layer_index = max(0, min(index, len(self.state.layers) - 1))

    def move_layer(self, index: int, delta: int) -> None:
        new_index = index + delta
        if not (0 <= index < len(self.state.layers)):
            return
        if not (0 <= new_index < len(self.state.layers)):
            return
        layer = self.state.layers.pop(index)
        self.state.layers.insert(new_index, layer)
        self.state.selected_layer_index = new_index

    def selected_layer(self) -> EnhanceLayer | None:
        if 0 <= self.state.selected_layer_index < len(self.state.layers):
            return self.state.layers[self.state.selected_layer_index]
        return None

    def update_layer(self, index: int, key: str, value: Any) -> None:
        if not (0 <= index < len(self.state.layers)):
            return
        layer = self.state.layers[index]
        if hasattr(layer, key):
            current = getattr(layer, key)
            if isinstance(current, bool):
                setattr(layer, key, bool(value))
            elif isinstance(current, float):
                try:
                    setattr(layer, key, float(value))
                except (TypeError, ValueError):
                    pass
            else:
                setattr(layer, key, value)

    # ---------- parameters ----------
    def update_parameter(self, key: str, value: Any) -> None:
        self.state.parameter_values[key] = value
        if key == "scale":
            self.state.scale = str(value)
        elif key == "seed":
            try:
                self.state.seed = int(value)
            except (TypeError, ValueError):
                self.state.seed = 0
        elif key == "use_seed":
            self.state.use_seed = bool(value)

    def update_output_options(
        self,
        output_dir: str,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        self.state.output_options.output_dir = Path(output_dir) if output_dir else None
        self.state.output_options.file_prefix = file_prefix.strip() or "enhanced"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    # ---------- paths ----------
    @staticmethod
    def workflows_dir() -> Path:
        engine_root = Path(__file__).resolve().parents[2]
        return engine_root / "assets" / "workflows" / "enhancer"

    def workflow_path_for(self, workflow_key: str | None = None) -> Path:
        key = workflow_key or "global"
        for k, _label, filename in WORKFLOW_CHOICES:
            if k == key:
                return self.workflows_dir() / filename
        return self.workflows_dir() / f"{key}.json"

    def workflow_label(self, key: str) -> str:
        for workflow_key, label, _filename in WORKFLOW_CHOICES:
            if workflow_key == key:
                return label
        return key

    def workflow_status(self) -> tuple[bool, str]:
        enabled_layers = [layer for layer in self.state.layers if layer.enabled]
        if not enabled_layers:
            return False, "No enabled layers."
        missing = []
        for layer in enabled_layers:
            path = self.workflow_path_for(layer.workflow_key)
            if not path.exists():
                missing.append(f"{layer.name}: {path.name}")
        if missing:
            return False, "Missing workflow(s): " + ", ".join(missing)
        return True, f"OK — {len(enabled_layers)} enabled layer(s) ready"

    def reveal_workflows_dir(self) -> None:
        d = self.workflows_dir()
        d.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(d)  # type: ignore[attr-defined]
        except Exception:
            pass

    def resolve_output_dir(self) -> Path | None:
        if self.state.output_options.output_dir:
            return self.state.output_options.output_dir
        current = self.current_input()
        if current is not None:
            return current.path.parent / "enhanced"
        return None

    def reveal_output_dir(self) -> None:
        out_dir = self.resolve_output_dir()
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.startfile(out_dir)  # type: ignore[attr-defined]
            except Exception:
                pass

    # ---------- runtime probe ----------
    def probe_runtime(self) -> tuple[str, str]:
        if not bridge.is_server_alive():
            return "ComfyUI offline", "warning"
        ok, _ = self.workflow_status()
        if not ok:
            return "Workflow missing", "warning"
        return "Ready", "success"

    # ---------- workflow injection ----------
    @staticmethod
    def _patch_first_input(inputs: dict[str, Any], keys: tuple[str, ...], value: Any) -> bool:
        for key in keys:
            if key in inputs:
                inputs[key] = value
                return True
        return False

    @classmethod
    def _inject_workflow(
        cls,
        workflow: dict[str, Any],
        input_name: str,
        output_prefix: str,
        scale: float | None,
        seed: int | None,
        mask_name: str | None,
        strength: float | None,
        layer_name: str,
    ) -> tuple[dict[str, Any], list[str]]:
        wf = copy.deepcopy(workflow)
        warnings: list[str] = []

        load_done = False
        save_done = False
        scale_done = False
        seed_done = False
        mask_done = False
        strength_done = False
        meta_done = False

        for _node_id, node in wf.items():
            class_type = node.get("class_type", "")
            inputs = node.setdefault("inputs", {})

            if not load_done and class_type == "LoadImage":
                inputs["image"] = input_name
                load_done = True
                continue

            if mask_name and not mask_done and ("Mask" in class_type or "mask" in class_type.lower()):
                if cls._patch_first_input(inputs, ("image", "mask", "mask_image", "mask_path"), mask_name):
                    mask_done = True

            if not save_done and class_type == "SaveImage":
                inputs["filename_prefix"] = output_prefix
                save_done = True
                continue

            if scale is not None and not scale_done and "Upscale" in class_type:
                if cls._patch_first_input(inputs, ("scale_by", "upscale_by", "factor", "scale"), float(scale)):
                    scale_done = True

            if seed is not None and not seed_done and class_type.startswith("KSampler"):
                if cls._patch_first_input(inputs, ("seed", "noise_seed"), int(seed)):
                    seed_done = True

            if strength is not None and not strength_done:
                if cls._patch_first_input(
                    inputs,
                    ("strength", "denoise", "blend", "opacity", "weight", "detail_strength"),
                    float(strength),
                ):
                    strength_done = True

            if not meta_done:
                if cls._patch_first_input(inputs, ("title", "label", "name", "pass_name"), layer_name):
                    meta_done = True

        if not load_done:
            warnings.append("No LoadImage node found — input image was not injected.")
        if not save_done:
            warnings.append("No SaveImage node found — output prefix was not injected.")
        if mask_name and not mask_done:
            warnings.append("Mask field not found on any mask node — workflow default kept.")
        if scale is not None and not scale_done:
            warnings.append("Scale field not found on any Upscale node — workflow default kept.")
        if seed is not None and not seed_done:
            warnings.append("Seed field not found on any KSampler node — workflow default kept.")
        if strength is not None and not strength_done:
            warnings.append("Strength field not found on any layer node — workflow default kept.")
        return wf, warnings

    # ---------- run ----------
    def run(
        self,
        log: Callable[[str], None] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        def emit(msg: str) -> None:
            if log:
                log(msg)
            else:
                print(msg)

        current = self.current_input()
        if current is None:
            raise RuntimeError("No input image selected.")

        enabled_layers = [layer for layer in self.state.layers if layer.enabled]
        if not enabled_layers:
            raise RuntimeError("No enabled layers.")

        out_dir = self.resolve_output_dir()
        if out_dir is None:
            raise RuntimeError("Could not resolve output directory.")
        out_dir.mkdir(parents=True, exist_ok=True)

        port = bridge.detect_server_port()
        if port is None:
            raise RuntimeError("ComfyUI server not reachable. Start it via the ComfyUI Dashboard app.")

        scale_value: float | None
        try:
            scale_value = float(self.state.scale)
        except (TypeError, ValueError):
            scale_value = None
        seed_value = self.state.seed if self.state.use_seed else None

        current_path = current.path
        staging_dir = out_dir / ".staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        produced: list[Path] = []
        layer_records: list[dict[str, Any]] = []

        for layer_index, layer in enumerate(enabled_layers, start=1):
            wf_path = self.workflow_path_for(layer.workflow_key)
            if not wf_path.exists():
                raise RuntimeError(f"Workflow file not found: {wf_path}")
            try:
                workflow_template = json.loads(wf_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Workflow JSON is malformed: {exc}") from exc

            emit(f"[{layer_index}/{len(enabled_layers)}] Uploading {current_path.name} for {layer.name}…")
            input_name = bridge.upload_image(port, current_path)

            mask_name = None
            if layer.use_mask and current.mask_path and current.mask_path.exists():
                mask_name = bridge.upload_image(port, current.mask_path)
            elif layer.use_mask and current.mask_path:
                emit(f"[warn] Missing mask file for {current.path.name} — running without it.")

            prefix = f"{self.state.output_options.file_prefix}_{current.path.stem}_{layer_index:02d}_{layer.name.replace(' ', '_').lower()}"
            workflow, warnings = self._inject_workflow(
                workflow_template,
                input_name,
                prefix,
                scale_value,
                seed_value,
                mask_name,
                layer.strength,
                layer.name,
            )
            for warning in warnings:
                emit(f"[warn] {warning}")

            emit(f"[{layer_index}/{len(enabled_layers)}] Queuing {layer.name}…")
            results = bridge.run_workflow(workflow, progress_callback=progress_callback)
            if not results:
                emit(f"[{layer_index}/{len(enabled_layers)}] No images returned.")
                continue

            layer_output_paths: list[str] = []
            first_temp_path: Path | None = None
            for output_index, (filename, payload) in enumerate(results, start=1):
                out_path = out_dir / filename
                stem = out_path.stem
                suffix = out_path.suffix
                counter = 1
                while out_path.exists():
                    out_path = out_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                out_path.write_bytes(payload)
                produced.append(out_path)
                layer_output_paths.append(str(out_path))
                emit(f"  -> {out_path}")
                if first_temp_path is None:
                    first_temp_path = staging_dir / f"{prefix}{suffix or '.png'}"
                    first_temp_path.write_bytes(payload)

            layer_records.append(
                {
                    "name": layer.name,
                    "workflow_key": layer.workflow_key,
                    "enabled": layer.enabled,
                    "strength": layer.strength,
                    "outputs": layer_output_paths,
                }
            )

            if first_temp_path is not None and layer_index < len(enabled_layers):
                current_path = first_temp_path

        if self.state.output_options.export_session_json:
            session_path = out_dir / "image_enhancer_session.json"
            session_data = {
                "selected_input": str(current.path),
                "mask_path": str(current.mask_path) if current.mask_path else None,
                "layers": [
                    {
                        **asdict(layer),
                        "workflow_label": self.workflow_label(layer.workflow_key),
                    }
                    for layer in self.state.layers
                ],
                "outputs": [str(p) for p in produced],
                "output_options": {
                    **asdict(self.state.output_options),
                    "output_dir": str(self.state.output_options.output_dir or out_dir),
                },
                "runtime": {
                    "scale": self.state.scale,
                    "seed": self.state.seed if self.state.use_seed else None,
                    "input_count": len(self.state.input_assets),
                },
                "layer_results": layer_records,
            }
            session_path.write_text(json.dumps(session_data, indent=2, ensure_ascii=False), encoding="utf-8")
            emit(f"Session JSON: {session_path}")

        return {"output_dir": out_dir, "produced": produced}
