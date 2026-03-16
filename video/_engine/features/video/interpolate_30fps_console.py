from __future__ import annotations

import subprocess
from pathlib import Path

from utils.external_tools import get_ffmpeg
from utils.files import get_safe_path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def _echo(message: str) -> None:
    print(message, flush=True)


def _pick_supported(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        path = target.resolve()
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if path in seen:
            continue
        seen.add(path)
        files.append(path)
    return files


def _output_path(source: Path) -> Path:
    return get_safe_path(source.with_name(f"{source.stem}_30fps.mp4"))


def run_interpolate_30fps_console(targets: list[Path]) -> int:
    files = _pick_supported(targets)
    if not files:
        _echo("No supported video files were provided.")
        return 1

    ffmpeg = get_ffmpeg()
    success = 0
    failures: list[str] = []

    _echo("Interpolate 30fps started.")
    _echo(f"Files: {len(files)}")
    _echo("Output: source folder / *_30fps.mp4")

    for index, source in enumerate(files, start=1):
        _echo(f"[{index}/{len(files)}] Interpolating: {source.name}")
        output_path = _output_path(source)
        cmd = [
            ffmpeg,
            "-i",
            str(source),
            "-filter:v",
            "minterpolate=fps=30:mi_mode=mci",
            "-y",
            str(output_path),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        if completed.returncode == 0:
            success += 1
            _echo(f"Created: {output_path}")
        else:
            detail = completed.stderr.strip() or completed.stdout.strip() or "Unknown FFmpeg error"
            failures.append(f"{source.name}: {detail}")
            _echo(f"Failed: {source.name}")

    _echo(f"Finished: {success}/{len(files)} succeeded.")
    if failures:
        _echo("Failures:")
        for line in failures:
            _echo(f"  - {line}")
        return 2
    return 0
