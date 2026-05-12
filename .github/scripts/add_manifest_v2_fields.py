"""Idempotently add HUB_CONTRACT.md §4.2 forward-compatible fields to every
manifest.json in this repo.

The fields are optional placeholders today; hub may treat missing entries as
unconstrained. See HUB_CONTRACT.md for the full schema.

Run: ``python .github/scripts/add_manifest_v2_fields.py``
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXCLUDE_DIRS = {".git", ".github", "dist", "__pycache__", "dev-tools", "agent-docs"}

DEFAULTS = {
    "compatibility": {
        "engine_min": "1.0.0",
        "engine_max": None,
        "hub_min": "1.0.0",
        "os": ["windows"],
    },
    "dependencies": {
        "external_binaries": [],
        "python_packages": [],
        "models": [],
    },
    "lifecycle": {
        "ready_signal": "stdout:[ctx] window_ready",
        "graceful_shutdown_timeout_ms": 3000,
    },
    "permissions": {
        "filesystem": "user-files",
        "network": "none",
    },
}


def merge_defaults(existing: dict, defaults: dict) -> bool:
    """Set defaults[key] only when absent. Returns True if anything changed."""
    changed = False
    for key, value in defaults.items():
        if key not in existing:
            existing[key] = value
            changed = True
        elif isinstance(value, dict) and isinstance(existing[key], dict):
            if merge_defaults(existing[key], value):
                changed = True
    return changed


def main() -> int:
    manifests = []
    for path in REPO_ROOT.rglob("manifest.json"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        manifests.append(path)

    updated = 0
    for manifest_path in sorted(manifests):
        try:
            text = manifest_path.read_text(encoding="utf-8-sig")
            data = json.loads(text)
        except Exception as exc:
            print(f"SKIP {manifest_path.relative_to(REPO_ROOT)}: {exc}", file=sys.stderr)
            continue

        changed = merge_defaults(data, DEFAULTS)
        if not changed:
            continue

        # Preserve trailing newline; pretty-print with 2-space indent like the
        # existing manifests.
        manifest_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        updated += 1
        print(f"UPDATED {manifest_path.relative_to(REPO_ROOT)}")

    print(f"\n{updated}/{len(manifests)} manifest(s) updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
