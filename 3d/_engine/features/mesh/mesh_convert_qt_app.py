from __future__ import annotations

from pathlib import Path

from .mesh_qt_shared import MeshConvertWindow, launch_window


def start_app(app_root: str | Path, targets: list[str] | None = None) -> int:
    return launch_window(MeshConvertWindow, Path(app_root), targets)
