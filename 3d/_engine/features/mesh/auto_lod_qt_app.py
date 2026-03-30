from __future__ import annotations

from pathlib import Path

from .auto_lod_qt_window import launch_auto_lod_window


def start_app(app_root: str | Path, targets: list[str] | None = None) -> int:
    return launch_auto_lod_window(Path(app_root), targets)
