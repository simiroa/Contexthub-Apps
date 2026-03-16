from __future__ import annotations

from pathlib import Path

from features.document.pdf_split.service import split_to_images, split_to_pages


def _echo(message: str) -> None:
    print(message, flush=True)


def _pick_supported(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        path = target.resolve()
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() != ".pdf":
            continue
        if path in seen:
            continue
        seen.add(path)
        files.append(path)
    return files


def run_pdf_split_console(targets: list[Path], output_format: str = "pdf") -> int:
    files = _pick_supported(targets)
    if not files:
        _echo("No supported PDF files were provided.")
        return 1

    success = 0
    failures: list[str] = []

    _echo("PDF Split started.")
    _echo(f"Files: {len(files)}")
    _echo(f"Output: source folder / <name>_split / {output_format.lower()}")

    for index, source in enumerate(files, start=1):
        out_dir = source.parent / f"{source.stem}_split"
        out_dir.mkdir(parents=True, exist_ok=True)
        _echo(f"[{index}/{len(files)}] Splitting PDF: {source.name}")

        try:
            if output_format.lower() == "pdf":
                results = split_to_pages(source, out_dir)
            else:
                fmt = "PNG" if output_format.lower() == "png" else "JPEG"
                results = split_to_images(source, out_dir, fmt=fmt)
            success += 1
            _echo(f"Created: {len(results)} page files in {out_dir}")
        except Exception as exc:
            failures.append(f"{source.name}: {exc}")
            _echo(f"Failed: {source.name}")

    _echo(f"Finished: {success}/{len(files)} succeeded.")
    if failures:
        _echo("Failures:")
        for line in failures:
            _echo(f"  - {line}")
        return 2
    return 0
