from __future__ import annotations

from pathlib import Path

from features.audio.audio_toolbox_service import run_console_task
from features.audio.audio_toolbox_state import TASK_NORMALIZE_VOLUME


AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".wma"}


def _echo(message: str) -> None:
    print(message, flush=True)


def _pick_supported(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        path = target.resolve()
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        if path in seen:
            continue
        seen.add(path)
        files.append(path)
    return files


def run_normalize_volume_console(targets: list[Path]) -> int:
    return run_console_task(TASK_NORMALIZE_VOLUME, _pick_supported(targets))
