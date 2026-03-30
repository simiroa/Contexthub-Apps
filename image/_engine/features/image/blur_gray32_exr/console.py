from __future__ import annotations

from pathlib import Path

from features.image.blur_gray32_exr.service import blur_to_gray32_exr, normalize_targets


def _echo(message: str) -> None:
    print(message, flush=True)


def run_blur_gray32_exr_console(targets: list[Path], radius: float) -> int:
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

    _echo("Blur Gray32 EXR started.")
    _echo(f"Files: {len(files)}")
    _echo(f"Blur radius: {radius:g}")
    _echo("Output: source folder / *_blur_gray32.exr")

    for index, source in enumerate(files, start=1):
        _echo(f"[{index}/{len(files)}] Blurring and converting: {source.name}")
        try:
            output_path = blur_to_gray32_exr(source, radius)
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
