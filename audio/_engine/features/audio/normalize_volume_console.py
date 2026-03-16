from __future__ import annotations

from pathlib import Path

from features.audio.normalize_service import AudioNormalizeService


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
    files = _pick_supported(targets)
    if not files:
        _echo("No supported audio files were provided.")
        return 1

    service = AudioNormalizeService()
    result = {"success": 0, "total": len(files), "errors": [], "last_output": None}

    def on_progress(current: int, total: int, name: str) -> None:
        _echo(f"[{current + 1}/{total}] Normalizing volume: {name}")

    def on_complete(success: int, total: int, errors: list[str], last_output: Path | None) -> None:
        result["success"] = success
        result["total"] = total
        result["errors"] = errors
        result["last_output"] = last_output

    _echo("Normalize Volume started.")
    _echo(f"Files: {len(files)}")
    _echo("Output: source folder / *_normalized")
    service.normalize_audio(files, on_progress=on_progress, on_complete=on_complete)

    if result["last_output"] is not None:
        _echo(f"Last output: {result['last_output']}")
    _echo(f"Finished: {result['success']}/{result['total']} succeeded.")
    if result["errors"]:
        _echo("Failures:")
        for line in result["errors"]:
            _echo(f"  - {line}")
        return 2
    return 0
