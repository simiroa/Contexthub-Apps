from __future__ import annotations

import os
from pathlib import Path


def _candidate_shared_roots(app_root: Path) -> list[Path]:
    repo_root = app_root.parents[1]
    env_shared_runtime_root = os.environ.get("CTX_SHARED_RUNTIME_ROOT")
    return [
        Path(env_shared_runtime_root) if env_shared_runtime_root else None,
        app_root / "Runtimes" / "Shared",
        repo_root / "dev-tools" / "runtime" / "Shared",
        repo_root.parent / "Contexthub" / "Runtimes" / "Shared",
        app_root.parent.parent / "Contexthub" / "Runtimes" / "Shared",
    ]


def _candidate_runtime_roots(app_root: Path) -> list[Path]:
    repo_root = app_root.parents[1]
    env_runtime_root = os.environ.get("CTX_RUNTIME_ROOT")
    env_dev_runtime_root = os.environ.get("CTX_DEV_RUNTIME_ROOT")
    return [
        Path(env_runtime_root) if env_runtime_root else None,
        Path(env_dev_runtime_root) if env_dev_runtime_root else None,
        repo_root / "dev-tools" / "runtime",
        repo_root.parent / "Contexthub" / "Runtimes",
        app_root.parent.parent / "Contexthub" / "Runtimes",
    ]


def resolve_shared_runtime(app_root: str | Path) -> tuple[Path, Path]:
    app_root = Path(app_root).resolve()
    os.environ.setdefault("CTX_APP_ROOT", str(app_root))

    runtime_root: Path | None = None
    for candidate in _candidate_runtime_roots(app_root):
        if candidate is not None and candidate.exists():
            runtime_root = candidate.resolve()
            break

    if runtime_root is None:
        runtime_root = app_root.parents[1] / "dev-tools" / "runtime"

    shared_root: Path | None = None
    for candidate in _candidate_shared_roots(app_root):
        if candidate.exists():
            shared_root = candidate.resolve()
            break

    if shared_root is None:
        shared_root = runtime_root / "Shared"

    shared_package_root = shared_root / "contexthub"
    return shared_root, shared_package_root
