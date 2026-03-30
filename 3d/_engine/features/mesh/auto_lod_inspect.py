from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


MAX_INSPECT_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class MeshBounds:
    center: tuple[float, float, float]
    radius: float
    vertex_count: int | None
    face_count: int | None


@dataclass(frozen=True)
class PreviewMesh:
    vertices: list[tuple[float, float, float]]
    faces: list[tuple[int, int, int]]
    bounds: MeshBounds


def _bounds_from_points(points: list[tuple[float, float, float]], face_count: int | None = None) -> MeshBounds | None:
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0)
    radius = max(max_x - min_x, max_y - min_y, max_z - min_z) / 2.0
    return MeshBounds(center=center, radius=max(radius, 0.5), vertex_count=len(points), face_count=face_count)


def _inspect_obj(path: Path) -> MeshBounds | None:
    points: list[tuple[float, float, float]] = []
    face_count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("v "):
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        points.append((float(parts[1]), float(parts[2]), float(parts[3])))
                    except Exception:
                        continue
            elif line.startswith("f "):
                face_count += 1
    return _bounds_from_points(points, face_count)


def _inspect_ascii_stl(path: Path) -> MeshBounds | None:
    points: list[tuple[float, float, float]] = []
    face_count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped.startswith("vertex "):
                parts = stripped.split()
                if len(parts) >= 4:
                    try:
                        points.append((float(parts[1]), float(parts[2]), float(parts[3])))
                    except Exception:
                        continue
            elif stripped.startswith("facet normal"):
                face_count += 1
    return _bounds_from_points(points, face_count)


def _inspect_binary_stl(path: Path) -> MeshBounds | None:
    points: list[tuple[float, float, float]] = []
    with path.open("rb") as handle:
        header = handle.read(80)
        if len(header) < 80:
            return None
        count_bytes = handle.read(4)
        if len(count_bytes) < 4:
            return None
        triangle_count = struct.unpack("<I", count_bytes)[0]
        for _ in range(triangle_count):
            chunk = handle.read(50)
            if len(chunk) < 50:
                break
            coords = struct.unpack("<12fH", chunk)
            points.extend(
                [
                    (coords[3], coords[4], coords[5]),
                    (coords[6], coords[7], coords[8]),
                    (coords[9], coords[10], coords[11]),
                ]
            )
    return _bounds_from_points(points, triangle_count)


def _inspect_stl(path: Path) -> MeshBounds | None:
    try:
        with path.open("rb") as handle:
            sample = handle.read(256)
        if sample.lstrip().startswith(b"solid"):
            result = _inspect_ascii_stl(path)
            if result is not None:
                return result
        return _inspect_binary_stl(path)
    except Exception:
        return None


def _inspect_ascii_ply(path: Path) -> MeshBounds | None:
    vertex_count = 0
    face_count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("element vertex"):
                try:
                    vertex_count = int(line.split()[-1])
                except Exception:
                    vertex_count = 0
            elif line.startswith("element face"):
                try:
                    face_count = int(line.split()[-1])
                except Exception:
                    face_count = 0
            elif line.strip() == "end_header":
                break
        points: list[tuple[float, float, float]] = []
        for _ in range(vertex_count):
            line = handle.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) >= 3:
                try:
                    points.append((float(parts[0]), float(parts[1]), float(parts[2])))
                except Exception:
                    continue
    return _bounds_from_points(points, face_count)


def inspect_mesh_bounds(path: Path | None) -> MeshBounds | None:
    if path is None or not path.exists():
        return None
    if path.stat().st_size > MAX_INSPECT_BYTES:
        return None
    suffix = path.suffix.lower()
    try:
        if suffix == ".obj":
            return _inspect_obj(path)
        if suffix == ".stl":
            return _inspect_stl(path)
        if suffix == ".ply":
            return _inspect_ascii_ply(path)
    except Exception:
        return None
    return None


def _obj_preview_mesh(path: Path, max_faces: int = 3500) -> PreviewMesh | None:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            if raw_line.startswith("v "):
                parts = raw_line.split()
                if len(parts) >= 4:
                    try:
                        vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
                    except Exception:
                        continue
            elif raw_line.startswith("f "):
                tokens = raw_line.split()[1:]
                polygon: list[int] = []
                for token in tokens:
                    base = token.split("/")[0]
                    if not base:
                        continue
                    try:
                        raw_index = int(base)
                    except Exception:
                        continue
                    if raw_index < 0:
                        index = len(vertices) + raw_index
                    else:
                        index = raw_index - 1
                    if 0 <= index < len(vertices):
                        polygon.append(index)
                if len(polygon) >= 3:
                    for index in range(1, len(polygon) - 1):
                        faces.append((polygon[0], polygon[index], polygon[index + 1]))
                        if len(faces) >= max_faces:
                            break
            if len(faces) >= max_faces:
                break
    bounds = _bounds_from_points(vertices, len(faces))
    if bounds is None or not faces:
        return None
    return PreviewMesh(vertices=vertices, faces=faces, bounds=bounds)


def _stl_preview_mesh(path: Path, max_faces: int = 3500) -> PreviewMesh | None:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    bounds = _inspect_stl(path)
    if bounds is None:
        return None
    with path.open("rb") as handle:
        sample = handle.read(256)
    if sample.lstrip().startswith(b"solid"):
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            triangle: list[tuple[float, float, float]] = []
            for line in handle:
                stripped = line.strip()
                if stripped.startswith("vertex "):
                    parts = stripped.split()
                    if len(parts) >= 4:
                        try:
                            triangle.append((float(parts[1]), float(parts[2]), float(parts[3])))
                        except Exception:
                            continue
                    if len(triangle) == 3:
                        start = len(vertices)
                        vertices.extend(triangle)
                        faces.append((start, start + 1, start + 2))
                        triangle = []
                        if len(faces) >= max_faces:
                            break
    else:
        with path.open("rb") as handle:
            handle.read(80)
            count_bytes = handle.read(4)
            if len(count_bytes) < 4:
                return None
            triangle_count = struct.unpack("<I", count_bytes)[0]
            for _ in range(min(triangle_count, max_faces)):
                chunk = handle.read(50)
                if len(chunk) < 50:
                    break
                coords = struct.unpack("<12fH", chunk)
                start = len(vertices)
                vertices.extend(
                    [
                        (coords[3], coords[4], coords[5]),
                        (coords[6], coords[7], coords[8]),
                        (coords[9], coords[10], coords[11]),
                    ]
                )
                faces.append((start, start + 1, start + 2))
    if not vertices or not faces:
        return None
    return PreviewMesh(vertices=vertices, faces=faces, bounds=bounds)


def _ply_preview_mesh(path: Path, max_faces: int = 3500) -> PreviewMesh | None:
    vertex_count = 0
    face_count = 0
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("format") and "ascii" not in line:
                return None
            if line.startswith("element vertex"):
                try:
                    vertex_count = int(line.split()[-1])
                except Exception:
                    vertex_count = 0
            elif line.startswith("element face"):
                try:
                    face_count = int(line.split()[-1])
                except Exception:
                    face_count = 0
            elif line.strip() == "end_header":
                break
        for _ in range(vertex_count):
            line = handle.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) >= 3:
                try:
                    vertices.append((float(parts[0]), float(parts[1]), float(parts[2])))
                except Exception:
                    continue
        for _ in range(face_count):
            line = handle.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                count = int(parts[0])
                indices = [int(value) for value in parts[1 : 1 + count]]
            except Exception:
                continue
            if len(indices) >= 3:
                for index in range(1, len(indices) - 1):
                    a, b, c = indices[0], indices[index], indices[index + 1]
                    if max(a, b, c) < len(vertices):
                        faces.append((a, b, c))
                        if len(faces) >= max_faces:
                            break
            if len(faces) >= max_faces:
                break
    bounds = _bounds_from_points(vertices, len(faces))
    if bounds is None or not faces:
        return None
    return PreviewMesh(vertices=vertices, faces=faces, bounds=bounds)


def load_preview_mesh(path: Path | None, max_faces: int = 3500) -> PreviewMesh | None:
    if path is None or not path.exists():
        return None
    if path.stat().st_size > MAX_INSPECT_BYTES:
        return None
    suffix = path.suffix.lower()
    try:
        if suffix == ".obj":
            return _obj_preview_mesh(path, max_faces=max_faces)
        if suffix == ".stl":
            return _stl_preview_mesh(path, max_faces=max_faces)
        if suffix == ".ply":
            return _ply_preview_mesh(path, max_faces=max_faces)
    except Exception:
        return None
    return None
