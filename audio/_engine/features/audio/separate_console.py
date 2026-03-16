from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


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
    files = _pick_supported(targets)
    if not files:
        _echo("No supported audio files were provided.")
        return 1

    if stem_kind not in {"voice", "bgm"}:
        raise ValueError("stem_kind must be 'voice' or 'bgm'")

    model = "htdemucs"
    desired_stem = "vocals.wav" if stem_kind == "voice" else "no_vocals.wav"
    output_suffix = "_voice.wav" if stem_kind == "voice" else "_bgm.wav"
    label = "Extract Voice" if stem_kind == "voice" else "Extract BGM"

    success = 0
    failures: list[str] = []

    _echo(f"{label} started.")
    _echo(f"Files: {len(files)}")
    _echo(f"Output: source folder / *{output_suffix}")

    for index, source in enumerate(files, start=1):
        _echo(f"[{index}/{len(files)}] Separating: {source.name}")
        temp_root = source.parent / "Separated_Audio"
        cmd = [
            sys.executable,
            "-m",
            "demucs",
            "-n",
            model,
            "--two-stems=vocals",
            "-o",
            str(temp_root),
            str(source),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "Demucs failed"
            failures.append(f"{source.name}: {detail}")
            _echo(f"Failed: {source.name}")
            continue

        produced = temp_root / model / source.stem / desired_stem
        if not produced.exists():
            failures.append(f"{source.name}: Output stem not found")
            _echo(f"Failed: {source.name}")
            continue

        final_path = source.with_name(f"{source.stem}{output_suffix}")
        shutil.copy2(produced, final_path)
        success += 1
        _echo(f"Created: {final_path}")

    _echo(f"Finished: {success}/{len(files)} succeeded.")
    if failures:
        _echo("Failures:")
        for line in failures:
            _echo(f"  - {line}")
        return 2
    return 0
