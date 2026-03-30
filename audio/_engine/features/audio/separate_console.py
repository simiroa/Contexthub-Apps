from __future__ import annotations

from pathlib import Path

from features.audio.audio_toolbox_service import run_console_task
from features.audio.audio_toolbox_state import TASK_EXTRACT_BGM, TASK_EXTRACT_VOICE

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


def run_separate_console(targets: list[Path], stem_kind: str) -> int:
    if stem_kind not in {"voice", "bgm"}:
        raise ValueError("stem_kind must be 'voice' or 'bgm'")
    return run_console_task(
        TASK_EXTRACT_VOICE if stem_kind == "voice" else TASK_EXTRACT_BGM,
        _pick_supported(targets),
    )
