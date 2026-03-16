from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from utils.external_tools import get_ffmpeg
from utils.files import get_safe_path
from utils.i18n import t


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def _echo(message: str) -> None:
    print(message, flush=True)


def _msg(key: str, default: str, **kwargs: object) -> str:
    message = t(key, default=default)
    if kwargs:
        try:
            return message.format(**kwargs)
        except Exception:
            return message
    return message


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


def _build_output_path(source: Path) -> Path:
    return get_safe_path(source.with_name(f"{source.stem}_mute{source.suffix}"))


def _run_single(ffmpeg: str, source: Path) -> tuple[bool, Path, str]:
    output_path = _build_output_path(source)
    cmd = [
        ffmpeg,
        "-i",
        str(source),
        "-c:v",
        "copy",
        "-an",
        "-y",
        str(output_path),
    ]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    except Exception as exc:
        return False, output_path, str(exc)

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "Unknown FFmpeg error"
        return False, output_path, detail
    return True, output_path, ""


def run_remove_audio_console(targets: list[Path], app_root: str | Path | None = None) -> int:
    del app_root

    files = _pick_supported(targets)
    if not files:
        _echo(_msg("remove_audio.console.no_targets", "No supported video files were provided."))
        return 1

    ffmpeg = get_ffmpeg()
    _echo(_msg("remove_audio.console.start", "Remove Audio started."))
    _echo(_msg("remove_audio.console.file_count", "Files: {count}", count=len(files)))
    _echo(_msg("remove_audio.console.output_rule", "Output: source folder / *_mute"))

    success = 0
    failures: list[str] = []

    for index, source in enumerate(files, start=1):
        _echo(
            _msg(
                "remove_audio.console.processing",
                "[{index}/{total}] Removing audio: {name}",
                index=index,
                total=len(files),
                name=source.name,
            )
        )
        ok, output_path, detail = _run_single(ffmpeg, source)
        if ok:
            success += 1
            _echo(
                _msg(
                    "remove_audio.console.done_one",
                    "Created: {path}",
                    path=str(output_path),
                )
            )
        else:
            failures.append(f"{source.name}: {detail}")
            _echo(
                _msg(
                    "remove_audio.console.failed_one",
                    "Failed: {name}",
                    name=source.name,
                )
            )

    _echo(
        _msg(
            "remove_audio.console.summary",
            "Finished: {success}/{total} succeeded.",
            success=success,
            total=len(files),
        )
    )

    if failures:
        _echo(_msg("remove_audio.console.failures", "Failures:"))
        for line in failures:
            _echo(f"  - {line}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(run_remove_audio_console([Path(arg) for arg in sys.argv[1:]]))
