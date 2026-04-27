from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HEX_COLOR_RE = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b")
RGB_COLOR_RE = re.compile(r"\brgba?\s*\(")

ALLOWED_COLOR_OWNERS = {
    Path("dev-tools/Runtimes/Shared/contexthub/ui/qt/shell.py"),
}

EXEMPT_COLOR_OWNERS = {
    Path("ai_lite/_engine/features/tools/ai_text_lab_qt_app.py"): "approved legacy exception; kept separate from the shared theme contract",
    Path("ai/_engine/features/ai/subtitle_qc_qt_app.py"): "needs a near-full rewrite; keep as approved exception until rebuilt",
    Path("ai_lite/_engine/features/versus_up/versus_up_qt_widgets.py"): "needs a near-full rewrite; keep as approved exception until rebuilt",
}

SKIP_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "Diagnostics",
    "dev-tools",
}


@dataclass(frozen=True)
class CheckMessage:
    level: str
    path: Path
    line: int
    message: str


def _iter_manifest_paths() -> list[Path]:
    return sorted(REPO_ROOT.rglob("manifest.json"))


def _iter_python_paths() -> list[Path]:
    paths: list[Path] = []
    for path in REPO_ROOT.rglob("*.py"):
        rel = path.relative_to(REPO_ROOT)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        paths.append(path)
    return sorted(paths)


def check_manifest_shared_theme() -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    for path in _iter_manifest_paths():
        rel = path.relative_to(REPO_ROOT)
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            messages.append(CheckMessage("ERROR", rel, 1, f"manifest parse failed: {exc}"))
            continue

        ui = data.get("ui") or {}
        shared_theme = ui.get("shared_theme")
        if shared_theme and shared_theme != "contexthub":
            messages.append(
                CheckMessage(
                    "ERROR",
                    rel,
                    1,
                    f"Qt shared theme must be 'contexthub', found '{shared_theme}'",
                )
            )
    return messages


def check_raw_color_drift() -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    for path in _iter_python_paths():
        rel = path.relative_to(REPO_ROOT)
        if rel in ALLOWED_COLOR_OWNERS:
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        if "setStyleSheet(" not in text:
            continue

        exempt_reason = EXEMPT_COLOR_OWNERS.get(rel)
        if exempt_reason:
            matches = 0
            for line in text.splitlines():
                if "setStyleSheet(" not in line and not HEX_COLOR_RE.search(line) and not RGB_COLOR_RE.search(line):
                    continue
                if HEX_COLOR_RE.search(line) or RGB_COLOR_RE.search(line):
                    matches += 1
            if matches:
                messages.append(
                    CheckMessage(
                        "EXEMPT",
                        rel,
                        1,
                        f"{matches} raw color hits skipped: {exempt_reason}",
                    )
                )
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            if "setStyleSheet(" not in line and not HEX_COLOR_RE.search(line) and not RGB_COLOR_RE.search(line):
                continue
            if HEX_COLOR_RE.search(line):
                color = HEX_COLOR_RE.search(line).group(0)
                messages.append(
                    CheckMessage(
                        "WARN",
                        rel,
                        line_no,
                        f"raw hex color inside stylesheet-heavy file: {color}",
                    )
                )
            if RGB_COLOR_RE.search(line):
                token = RGB_COLOR_RE.search(line).group(0).strip()
                messages.append(
                    CheckMessage(
                        "WARN",
                        rel,
                        line_no,
                        f"raw rgb/rgba color inside stylesheet-heavy file: {token}",
                    )
                )
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Qt GUI shared theme contract.")
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Return a non-zero exit code when raw color drift warnings are found.",
    )
    parser.add_argument(
        "--show-exemptions",
        action="store_true",
        help="Print approved legacy exceptions in addition to drift warnings.",
    )
    args = parser.parse_args()

    errors = check_manifest_shared_theme()
    warnings = check_raw_color_drift()

    for msg in errors + warnings:
        if msg.level == "EXEMPT" and not args.show_exemptions:
            continue
        print(f"{msg.level} {msg.path}:{msg.line} {msg.message}")

    exempt_count = sum(1 for msg in warnings if msg.level == "EXEMPT")
    warning_count = sum(1 for msg in warnings if msg.level == "WARN")
    print(
        f"Summary: errors={len(errors)} warnings={warning_count} exemptions={exempt_count} "
        f"fail_on_warning={'yes' if args.fail_on_warning else 'no'}"
    )

    if errors:
        return 1
    if warning_count and args.fail_on_warning:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
