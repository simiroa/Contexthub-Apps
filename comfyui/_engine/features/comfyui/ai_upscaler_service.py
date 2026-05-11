from __future__ import annotations

import copy
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from features.comfyui.ai_upscaler_state import (
    AIUpscalerState,
    InputAsset,
    MODEL_CHOICES,
)
from features.comfyui import ai_upscaler_comfy_bridge as bridge


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


class AIUpscalerService:
    def __init__(self) -> None:
        self.state = AIUpscalerState()
        self.state.parameter_values = {
            "model": self.state.model_key,
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
        if self.state.input_assets and self.state.preview_path is None:
            self.state.preview_path = self.state.input_assets[0].path

    def remove_input_at(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            removed = self.state.input_assets.pop(index)
            if self.state.preview_path == removed.path:
                self.state.preview_path = self.state.input_assets[0].path if self.state.input_assets else None

    def clear_inputs(self) -> None:
        self.state.input_assets.clear()
        self.state.preview_path = None

    def set_preview_from_index(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            self.state.preview_path = self.state.input_assets[index].path

    # ---------- parameters ----------
    def update_parameter(self, key: str, value: Any) -> None:
        self.state.parameter_values[key] = value
        if key == "model":
            self.state.model_key = str(value)
        elif key == "scale":
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
        self.state.output_options.file_prefix = file_prefix.strip() or "upscaled"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    # ---------- paths ----------
    @staticmethod
    def workflows_dir() -> Path:
        engine_root = Path(__file__).resolve().parents[2]
        return engine_root / "assets" / "workflows" / "upscaler"

    def workflow_path_for(self, model_key: str | None = None) -> Path:
        key = model_key or self.state.model_key
        for k, _name, filename in MODEL_CHOICES:
            if k == key:
                return self.workflows_dir() / filename
        return self.workflows_dir() / f"{key}.json"

    def model_label(self, key: str) -> str:
        for k, label, _filename in MODEL_CHOICES:
            if k == key:
                return label
        return key

    def workflow_status(self) -> tuple[bool, str]:
        path = self.workflow_path_for()
        if not path.exists():
            return False, f"Missing: {path}"
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(path.stat().st_mtime))
        return True, f"OK — modified {ts}"

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
        if self.state.input_assets:
            return self.state.input_assets[0].path.parent / "upscaled"
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
    def _inject_workflow(
        workflow: dict[str, Any],
        input_name: str,
        output_prefix: str,
        scale: float | None,
        seed: int | None,
    ) -> tuple[dict[str, Any], list[str]]:
        wf = copy.deepcopy(workflow)
        warnings: list[str] = []

        load_done = False
        save_done = False
        scale_done = False
        seed_done = False

        for _node_id, node in wf.items():
            class_type = node.get("class_type", "")
            inputs = node.setdefault("inputs", {})
            if not load_done and class_type == "LoadImage":
                inputs["image"] = input_name
                load_done = True
                continue
            if not save_done and class_type == "SaveImage":
                inputs["filename_prefix"] = output_prefix
                save_done = True
                continue
            if scale is not None and not scale_done and "Upscale" in class_type:
                for field_name in ("scale_by", "upscale_by", "factor"):
                    if field_name in inputs:
                        inputs[field_name] = float(scale)
                        scale_done = True
                        break
            if seed is not None and not seed_done and class_type.startswith("KSampler"):
                if "seed" in inputs:
                    inputs["seed"] = int(seed)
                    seed_done = True

        if not load_done:
            warnings.append("No LoadImage node found — input image was not injected.")
        if not save_done:
            warnings.append("No SaveImage node found — output prefix was not injected.")
        if scale is not None and not scale_done:
            warnings.append("Scale field not found on any Upscale node — workflow default kept.")
        if seed is not None and not seed_done:
            warnings.append("Seed field not found on any KSampler node — workflow default kept.")
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

        if not self.state.input_assets:
            raise RuntimeError("No input images.")
        wf_path = self.workflow_path_for()
        if not wf_path.exists():
            raise RuntimeError(f"Workflow file not found: {wf_path}")
        try:
            workflow_template = json.loads(wf_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Workflow JSON is malformed: {exc}") from exc

        port = bridge.detect_server_port()
        if port is None:
            raise RuntimeError("ComfyUI server not reachable. Start it via the ComfyUI Dashboard app.")

        out_dir = self.resolve_output_dir()
        if out_dir is None:
            raise RuntimeError("Could not resolve output directory.")
        out_dir.mkdir(parents=True, exist_ok=True)

        scale_value: float | None
        try:
            scale_value = float(self.state.scale)
        except (TypeError, ValueError):
            scale_value = None
        seed_value = self.state.seed if self.state.use_seed else None

        produced: list[Path] = []
        for index, asset in enumerate(self.state.input_assets, start=1):
            emit(f"[{index}/{len(self.state.input_assets)}] Uploading {asset.path.name}…")
            server_name = bridge.upload_image(port, asset.path)

            prefix = f"{self.state.output_options.file_prefix}_{asset.path.stem}"
            workflow, warnings = self._inject_workflow(
                workflow_template, server_name, prefix, scale_value, seed_value
            )
            for w in warnings:
                emit(f"[warn] {w}")

            emit(f"[{index}/{len(self.state.input_assets)}] Queuing workflow…")
            results = bridge.run_workflow(workflow, progress_callback=progress_callback)
            if not results:
                emit(f"[{index}/{len(self.state.input_assets)}] No images returned.")
                continue
            for filename, payload in results:
                out_path = out_dir / filename
                stem = out_path.stem
                suffix = out_path.suffix
                counter = 1
                while out_path.exists():
                    out_path = out_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                out_path.write_bytes(payload)
                produced.append(out_path)
                emit(f"  -> {out_path}")

        if self.state.output_options.export_session_json:
            session_path = out_dir / "ai_upscaler_session.json"
            session_data = {
                "model_key": self.state.model_key,
                "model_label": self.model_label(self.state.model_key),
                "scale": self.state.scale,
                "seed": self.state.seed if self.state.use_seed else None,
                "inputs": [str(a.path) for a in self.state.input_assets],
                "outputs": [str(p) for p in produced],
                "output_options": {
                    **asdict(self.state.output_options),
                    "output_dir": str(self.state.output_options.output_dir or out_dir),
                },
            }
            session_path.write_text(json.dumps(session_data, indent=2, ensure_ascii=False), encoding="utf-8")
            emit(f"Session JSON: {session_path}")

        return {"output_dir": out_dir, "produced": produced}
