from __future__ import annotations

from pathlib import Path
from typing import Callable

from features.image.vectorizer.rigreader_vectorizer_state import RigreaderVectorizerState
from features.image.vectorizer.service import VectorizerService


class RigreaderVectorizerService:
    def __init__(self) -> None:
        self.state = RigreaderVectorizerState()
        self._core = VectorizerService(state=self.state)

    def get_ui_definition(self):
        return self._core.get_ui_definition()

    def get_workflow_names(self):
        return self._core.get_workflow_names()

    def select_workflow(self, name: str) -> None:
        self._core.select_workflow(name)
        self.state.status_text = f"Preset: {name}"
        self.state.status_level = "ready"

    def add_inputs(self, paths: list[str]) -> None:
        self._core.add_inputs(paths)
        if self.state.source_path is not None:
            self.state.status_text = f"Loaded: {self.state.source_path.name}"
            self.state.status_level = "ready"

    def remove_input_at(self, index: int) -> None:
        self._core.remove_input_at(index)

    def clear_inputs(self) -> None:
        self._core.clear_inputs()
        self.state.status_text = "Ready"
        self.state.status_level = "ready"

    def set_preview_from_index(self, index: int) -> None:
        self._core.set_preview_from_index(index)

    def get_source_pixmap(self):
        return self._core.get_source_pixmap()

    def get_preview_pixmap(self, uid: str):
        return self._core.get_preview_pixmap(uid)

    def get_anchor_preview_data(self, uid: str):
        return self._core.get_anchor_preview_data(uid)

    def update_parameter(self, key: str, value):
        self._core.update_parameter(key, value)

    def update_output_options(self, path: str, prefix: str, open_folder: bool, export_json: bool) -> None:
        self._core.update_output_options(path, prefix, open_folder, export_json)

    def reveal_output_dir(self) -> None:
        self._core.reveal_output_dir()

    def run_workflow(self, on_complete: Callable | None = None) -> tuple[bool, str, object]:
        self.state.status_text = "Vectorizing..."
        self.state.status_level = "warning"

        def _wrapped(success: bool, message: str) -> None:
            self.state.status_text = message
            self.state.status_level = "ready" if success else "error"
            if on_complete is not None:
                on_complete(success, message)

        return self._core.run_workflow(on_complete=_wrapped)
