from __future__ import annotations

from pathlib import Path

from .mesh_service import MeshService


def _echo(message: str) -> None:
    print(message, flush=True)


def _pick_supported(targets: list[Path], allowed: set[str]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        path = target.resolve()
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() not in allowed:
            continue
        if path in seen:
            continue
        seen.add(path)
        files.append(path)
    return files


def _run_mode(mode: str, targets: list[Path], allowed: set[str], label: str) -> int:
    files = _pick_supported(targets, allowed)
    if not files:
        _echo(f"No supported {label} files were provided.")
        return 1

    service = MeshService()
    failures: list[str] = []
    success = 0

    _echo(f"{label} started.")
    _echo(f"Files: {len(files)}")

    def on_progress(current: int, total: int, filename: str) -> None:
        _echo(f"[{current}/{total}] Processing: {filename}")

    def on_complete(done: int, total: int, errors: list[str], _last_path: Path | None) -> None:
        nonlocal success, failures
        success = done
        failures = errors

    service.execute_mesh_task(mode, files, on_progress=on_progress, on_complete=on_complete)
    _echo(f"Finished: {success}/{len(files)} succeeded.")
    if failures:
        _echo("Failures:")
        for line in failures:
            _echo(f"  - {line}")
        return 2
    return 0


def run_extract_textures_console(targets: list[Path]) -> int:
    return _run_mode("extract", targets, {".fbx", ".glb", ".gltf"}, "Extract Textures")


def run_cad_to_obj_console(targets: list[Path]) -> int:
    return _run_mode("cad", targets, {".step", ".stp", ".iges", ".igs", ".brep"}, "CAD to OBJ")


def run_open_with_mayo_console(targets: list[Path]) -> int:
    return _run_mode("mayo", targets, {".step", ".stp", ".iges", ".igs", ".brep", ".stl", ".obj", ".fbx", ".glb", ".gltf"}, "Open with Mayo")
