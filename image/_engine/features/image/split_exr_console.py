from __future__ import annotations

import threading
from pathlib import Path

from features.image.split_exr.service import SplitExrService


IMAGE_EXTENSIONS = {".exr"}


def _echo(message: str) -> None:
    print(message, flush=True)


def _pick_supported(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        path = target.resolve()
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if path in seen:
            continue
        seen.add(path)
        files.append(path)
    return files


def run_split_exr_console(targets: list[Path], output_format: str = "png") -> int:
    files = _pick_supported(targets)
    if not files:
        _echo("No supported EXR files were provided.")
        return 1

    service = SplitExrService()
    if not service.is_exr_supported():
        _echo("OpenEXR library missing.")
        return 2

    info, layers = service.analyze_file(files[0])
    if not layers:
        _echo(info or "No layers were detected.")
        return 2

    layer_configs = [
        {"name": layer["name"], "invert": False, "suffix": layer["default_suffix"]}
        for layer in layers
    ]

    done = threading.Event()
    result = {"success": 0, "errors": []}

    def on_progress(progress: float, message: str) -> None:
        _echo(message)

    def on_complete(success: int, errors: list[str]) -> None:
        result["success"] = success
        result["errors"] = errors
        done.set()

    _echo("Split EXR started.")
    _echo(f"Files: {len(files)}")
    _echo(f"Output: source folder / <name>_split / .{output_format.lower()}")

    service.run_batch_split(files, layer_configs, output_format.upper(), on_progress, on_complete)
    done.wait()

    _echo(f"Finished: {result['success']}/{len(files)} succeeded.")
    if result["errors"]:
        _echo("Failures:")
        for line in result["errors"]:
            _echo(f"  - {line}")
        return 2
    return 0
