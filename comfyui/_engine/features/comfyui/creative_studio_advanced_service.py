from __future__ import annotations

import json
import os
import webbrowser
from dataclasses import asdict
from pathlib import Path
from typing import Any

from features.comfyui.creative_studio_advanced_state import (
    CreativeStudioAdvancedState,
    InputAsset,
)
from features.comfyui.workflow_wrappers import WorkflowRegistry


class CreativeStudioAdvancedService:
    def __init__(self) -> None:
        self.registry = WorkflowRegistry()
        self.comfy_service = None
        self.state = CreativeStudioAdvancedState()
        self._checkpoint_options: list[str] = []
        self._apply_default_workflow()

    def _get_comfy_service(self):
        if self.comfy_service is not None:
            return self.comfy_service
        try:
            from manager.helpers.comfyui_service import ComfyUIService

            self.comfy_service = ComfyUIService()
            return self.comfy_service
        except Exception:
            self.comfy_service = None
            return None

    def _apply_default_workflow(self) -> None:
        names = self.registry.get_all_names()
        if not names:
            self.state.workflow_name = "No workflow presets"
            self.state.workflow_description = "No workflow presets are registered for this category."
            return

        wrapper = self.registry.get_by_name(names[0])
        if wrapper is None:
            return
        self.select_workflow(wrapper.name)

    def get_workflow_names(self) -> list[str]:
        return self.registry.get_all_names()

    def select_workflow(self, name: str) -> None:
        wrapper = self.registry.get_by_name(name)
        if wrapper is None:
            raise ValueError(f"Unknown workflow: {name}")

        self.state.workflow_name = wrapper.name
        self.state.workflow_description = wrapper.description
        self.state.parameter_values = {
            widget.key: widget.default for widget in wrapper.get_ui_definition() if widget.default is not None
        }

    def get_current_wrapper(self):
        return self.registry.get_by_name(self.state.workflow_name)

    def get_ui_definition(self):
        wrapper = self.get_current_wrapper()
        if wrapper is None:
            return []
        defs = wrapper.get_ui_definition()
        checkpoints = self.get_checkpoint_options()
        if checkpoints:
            for definition in defs:
                if definition.type == "ckpt":
                    definition.options = checkpoints
                    if not self.state.parameter_values.get(definition.key):
                        self.state.parameter_values[definition.key] = checkpoints[0]
        return defs

    def add_inputs(self, paths: list[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            if any(asset.path == path for asset in self.state.input_assets):
                continue
            kind = "image" if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"} else "file"
            self.state.input_assets.append(InputAsset(path=path, kind=kind))

        if self.state.input_assets and self.state.preview_path is None:
            self.state.preview_path = self.state.input_assets[0].path

    def remove_input_at(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            removed = self.state.input_assets.pop(index)
            if self.state.preview_path == removed.path:
                self.state.preview_path = self.state.input_assets[0].path if self.state.input_assets else None

    def set_preview_from_index(self, index: int) -> None:
        if 0 <= index < len(self.state.input_assets):
            self.state.preview_path = self.state.input_assets[index].path

    def update_parameter(self, key: str, value: Any) -> None:
        self.state.parameter_values[key] = value

    def update_output_options(
        self,
        output_dir: str,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        self.state.output_options.output_dir = Path(output_dir)
        self.state.output_options.file_prefix = file_prefix.strip() or "creative_studio"
        self.state.output_options.open_folder_after_run = open_folder_after_run
        self.state.output_options.export_session_json = export_session_json

    def probe_runtime(self) -> tuple[str, str]:
        comfy_service = self._get_comfy_service()
        if comfy_service is None:
            return ("ComfyUI runtime bridge is unavailable. GUI shell mode only.", "warning")
        try:
            running, port = comfy_service.is_running()
            if running:
                self._refresh_runtime_options()
                return (f"Connected to ComfyUI on port {port}.", "ready")
            return ("ComfyUI is not running yet. Start it before running a workflow.", "warning")
        except Exception as exc:
            return (f"ComfyUI probe failed: {exc}", "error")

    def ensure_runtime(self) -> tuple[bool, str]:
        comfy_service = self._get_comfy_service()
        if comfy_service is None:
            return False, "ComfyUI runtime bridge is unavailable in this environment."
        try:
            ok, port, started = comfy_service.ensure_running(start_if_missing=True)
            if ok:
                self._refresh_runtime_options()
                verb = "Started" if started else "Connected"
                return True, f"{verb} ComfyUI on port {port}."
            return False, "ComfyUI could not be started."
        except Exception as exc:
            return False, f"Failed to start ComfyUI: {exc}"

    def _refresh_runtime_options(self) -> None:
        comfy_service = self._get_comfy_service()
        if comfy_service is None:
            return
        options = comfy_service.client.get_input_options("CheckpointLoaderSimple", "ckpt_name")
        if options:
            self._checkpoint_options = options

    def get_checkpoint_options(self) -> list[str]:
        return self._checkpoint_options

    def _build_workflow_payload(self) -> dict[str, Any]:
        wrapper = self.get_current_wrapper()
        if wrapper is None:
            raise RuntimeError("No workflow preset selected.")

        values = dict(self.state.parameter_values)
        values["filename_prefix"] = self.state.output_options.file_prefix

        workflow_path = Path(__file__).resolve().parents[2] / wrapper.workflow_path
        workflow_json = None
        if workflow_path.exists():
            workflow_json = json.loads(workflow_path.read_text(encoding="utf-8"))

        payload = wrapper.apply_values(workflow_json, values)
        if payload is None and hasattr(wrapper, "build_default_workflow"):
            payload = wrapper.build_default_workflow(values)
        if payload is None:
            raise RuntimeError("Workflow payload could not be built.")
        return payload

    def build_session_payload(self) -> dict[str, Any]:
        return {
            "workflow": {
                "name": self.state.workflow_name,
                "description": self.state.workflow_description,
            },
            "inputs": [
                {"path": str(asset.path), "kind": asset.kind} for asset in self.state.input_assets
            ],
            "parameters": self.state.parameter_values,
            "output": asdict(self.state.output_options),
        }

    def export_session(self) -> Path:
        self.state.output_options.output_dir.mkdir(parents=True, exist_ok=True)
        payload = self.build_session_payload()
        export_path = self.state.output_options.output_dir / f"{self.state.output_options.file_prefix}_session.json"
        export_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return export_path

    def run_workflow(self) -> tuple[bool, str, Path | None]:
        session_path = self.export_session() if self.state.output_options.export_session_json else None
        if session_path is not None:
            return True, "GUI pilot mode: session JSON exported. Engine execution is intentionally deferred.", session_path
        return True, "GUI pilot mode: execution is deferred.", None

    def open_webui(self) -> None:
        comfy_service = self._get_comfy_service()
        if comfy_service is None:
            webbrowser.open("http://127.0.0.1:8188")
            return

        running, port = comfy_service.is_running()
        if not running:
            ok, port, _started = comfy_service.ensure_running(start_if_missing=True)
            if not ok:
                webbrowser.open("http://127.0.0.1:8188")
                return

        webbrowser.open(f"http://127.0.0.1:{port}")

    def reveal_output_dir(self) -> None:
        path = self.state.output_options.output_dir
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)
