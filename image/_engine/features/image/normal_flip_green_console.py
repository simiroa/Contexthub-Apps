from __future__ import annotations

from pathlib import Path

from features.image.normal_flip_green.service import flip_green_file, normalize_targets


def _echo(message: str) -> None:
    print(message, flush=True)


def run_normal_flip_green_console(targets: list[Path]) -> int:
    files, skipped = normalize_targets(targets)
    if not files:
        _echo("No supported image files were provided.")
        if skipped:
            _echo("Skipped:")
            for line in skipped:
                _echo(f"  - {line}")
        return 1

    success = 0
    failures: list[str] = []

    _echo("Normal Flip Green started.")
    _echo(f"Files: {len(files)}")
    _echo("Output: source folder / *_flipped")

    for index, source in enumerate(files, start=1):
        _echo(f"[{index}/{len(files)}] Flipping green channel: {source.name}")
        try:
            output_path = flip_green_file(source)
            success += 1
            _echo(f"Created: {output_path}")
        except Exception as exc:
            failures.append(f"{source.name}: {exc}")
            _echo(f"Failed: {source.name}")

    if skipped:
        _echo("Skipped:")
        for line in skipped:
            _echo(f"  - {line}")

    _echo(f"Finished: {success}/{len(files)} succeeded.")
    if failures:
        _echo("Failures:")
        for line in failures:
            _echo(f"  - {line}")
        return 2
    return 0
