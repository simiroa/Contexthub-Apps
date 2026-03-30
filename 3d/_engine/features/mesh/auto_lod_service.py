from __future__ import annotations

from pathlib import Path
from typing import Callable

from contexthub.utils.files import get_safe_path


class AutoLodService:
    def __init__(self) -> None:
        self.current_process = None
        self.cancel_flag = False

    def _pymeshlab_available(self) -> bool:
        try:
            import pymeshlab  # noqa: F401
        except Exception:
            return False
        return True

    def get_dependency_status(self) -> dict[str, str | bool | None]:
        if not self._pymeshlab_available():
            return {
                "available": False,
                "title": "Dependency Missing",
                "detail": "Auto LOD requires pymeshlab in the 3D runtime. Install the 3D app requirements before running generation.",
                "path": "pymeshlab",
            }
        return {
            "available": True,
            "title": "Ready",
            "detail": "pymeshlab is available in the 3D runtime.",
            "path": "pymeshlab",
        }

    def execute_task(
        self,
        input_paths: list[Path],
        on_progress: Callable[[int, int, str], None] | None = None,
        on_complete: Callable[[int, int, list[str], list[Path]], None] | None = None,
        **options: object,
    ) -> None:
        if not self._pymeshlab_available():
            raise RuntimeError("pymeshlab is not installed in the 3D runtime.")
        self.cancel_flag = False
        total = len(input_paths)
        success = 0
        errors: list[str] = []
        result_paths: list[Path] = []

        for index, path in enumerate(input_paths):
            if self.cancel_flag:
                break
            if on_progress:
                on_progress(index + 1, total, path.name)
            try:
                result_paths = self._run_lod(
                    path,
                    ratio=float(options.get("ratio", 0.5)),
                    lod_count=int(options.get("lod_count", 3)),
                    preserve_uv=bool(options.get("preserve_uv", True)),
                    preserve_normal=bool(options.get("preserve_normal", True)),
                    preserve_boundary=bool(options.get("preserve_boundary", True)),
                )
                success += 1
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")

        if on_complete:
            on_complete(success, total, errors, result_paths)

    def _run_lod(
        self,
        path: Path,
        ratio: float,
        lod_count: int,
        preserve_uv: bool = True,
        preserve_normal: bool = True,
        preserve_boundary: bool = True,
    ) -> list[Path]:
        _ = (preserve_uv, preserve_normal, preserve_boundary)
        out_dir = get_safe_path(path.parent / f"{path.stem}_lod")
        out_dir.mkdir(exist_ok=True)
        result_paths: list[Path] = []
        for level in range(1, max(1, lod_count) + 1):
            level_ratio = max(min(ratio, 0.95), 0.05) ** level
            suffix = int(round(level_ratio * 100))
            result_paths.append(get_safe_path(out_dir / f"{path.stem}_lod_{suffix}.obj"))
        return result_paths

    def cancel(self) -> None:
        self.cancel_flag = True
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
            except Exception:
                pass
