from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .auto_lod_state import AutoLodState


@dataclass(frozen=True)
class AutoLodSpec:
    title: str = "Auto LOD"
    subtitle: str = "Review one source mesh, tune LOD controls, and generate a predictable output set."
    primary_action: str = "Generate LODs"
    dependency_name: str = "Mesh Processor"
    source_title: str = "Source Mesh"
    output_title: str = "LOD Plan"


ALLOWED_EXTENSIONS: tuple[str, ...] = (".obj", ".ply", ".stl", ".off", ".gltf", ".glb", ".fbx")


def allowed_extensions() -> tuple[str, ...]:
    return ALLOWED_EXTENSIONS


def supports_path(path: Path) -> tuple[bool, str]:
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False, "Blocked"
    return True, "Ready"


def estimate_output_dir(state: AutoLodState) -> Path | None:
    if state.input_path is None:
        return None
    return state.input_path.parent / f"{state.input_path.stem}_lod"


def default_output_prefix() -> str:
    return "lod"


def build_expected_outputs(state: AutoLodState) -> list[str]:
    if state.input_path is None:
        return []
    outputs: list[str] = []
    ratio = max(min(state.lod_ratio, 0.95), 0.05)
    for level in range(1, max(1, state.lod_count) + 1):
        level_ratio = max(ratio**level, 0.01)
        suffix = int(round(level_ratio * 100))
        outputs.append(f"LOD{level}: {state.input_path.stem}_lod_{suffix}.obj")
    return outputs


def build_expected_output_paths(state: AutoLodState) -> list[Path]:
    if state.input_path is None:
        return []
    output_dir = estimate_output_dir(state)
    if output_dir is None:
        return []
    paths: list[Path] = []
    ratio = max(min(state.lod_ratio, 0.95), 0.05)
    for level in range(1, max(1, state.lod_count) + 1):
        level_ratio = max(ratio**level, 0.01)
        suffix = int(round(level_ratio * 100))
        paths.append(output_dir / f"{state.input_path.stem}_lod_{suffix}.obj")
    return paths


def supported_format_text() -> str:
    return ", ".join(ext.upper().lstrip(".") for ext in ALLOWED_EXTENSIONS)


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def safe_int(raw: str, default: int) -> int:
    try:
        return int(float(raw))
    except Exception:
        return default


def safe_float(raw: str, default: float) -> float:
    try:
        return float(raw)
    except Exception:
        return default


def collect_run_options(state: AutoLodState) -> dict[str, object]:
    return {
        "ratio": state.lod_ratio,
        "lod_count": state.lod_count,
        "preserve_uv": state.preserve_uv,
        "preserve_normal": state.preserve_normal,
        "preserve_boundary": state.preserve_boundary,
    }
