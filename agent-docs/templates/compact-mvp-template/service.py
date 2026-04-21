from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, List, Optional
from .state import __APP_CLASS_NAME__State, InputAsset

class __APP_CLASS_NAME__Service:
    def __init__(self) -> None:
        self.state = __APP_CLASS_NAME__State()
        self._ui_definition = [
            {"key": "example_param", "label": "Example Parameter", "type": "choice", "options": ["Option A", "Option B"], "default": "Option A"},
            {"key": "enable_feature", "label": "Enable Feature", "type": "bool", "default": True},
        ]
        # Initialize defaults
        for item in self._ui_definition:
            if item["default"] is not None:
                self.state.parameter_values[item["key"]] = item["default"]

    def get_ui_definition(self) -> list[dict[str, Any]]:
        return list(self._ui_definition)

    def add_inputs(self, paths: list[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists(): continue
            if any(asset.path == path for asset in self.state.input_assets): continue
            
            self.state.input_assets.append(InputAsset(path=path))
                
        if self.state.input_assets and self.state.preview_path is None:
            self.state.preview_path = self.state.input_assets[0].path

    def update_parameter(self, key: str, value: Any) -> None:
        self.state.parameter_values[key] = value

    def run_workflow(self) -> tuple[bool, str, Path | None]:
        # Implement core processing logic here
        assets = self.state.input_assets
        if not assets: return False, "No items to process", None
        
        # Simulated success
        return True, f"Successfully processed {len(assets)} items", assets[0].path.parent
