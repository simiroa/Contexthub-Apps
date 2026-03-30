from __future__ import annotations

from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from PIL import Image

try:
    from core.logger import setup_logger
except ModuleNotFoundError:
    try:
        from contexthub.core.logger import setup_logger
    except ModuleNotFoundError:
        import logging

        def setup_logger(name: str):
            logger = logging.getLogger(name)
            if not logger.handlers:
                logging.basicConfig(level=logging.INFO)
            return logger


logger = setup_logger("blur_gray32_exr_service")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff", ".bmp", ".webp"}
OUTPUT_SUFFIX = "_blur_gray32"


def normalize_targets(targets: Iterable[str | Path]) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    errors: list[str] = []
    seen: set[str] = set()

    for target in targets:
        path = Path(target)
        if not path.exists():
            errors.append(f"{path.name}: File not found")
            continue
        if path.is_dir():
            errors.append(f"{path.name}: Directories are not supported")
            continue
        if path.suffix.lower() not in IMAGE_EXTS:
            errors.append(f"{path.name}: Unsupported image format")
            continue
        if path.stem.lower().endswith(OUTPUT_SUFFIX):
            errors.append(f"{path.name}: Skipped existing blur-gray output")
            continue
        try:
            resolved = str(path.resolve())
        except Exception:
            resolved = str(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        files.append(path)

    return files, errors


def build_output_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}{OUTPUT_SUFFIX}.exr")


def blur_to_gray32_exr(path: Path, radius: float) -> Path:
    if radius < 0:
        raise ValueError("Blur radius must be greater than or equal to 0")

    with Image.open(path) as img:
        rgb_img = img.convert("RGB")
        arr = np.asarray(rgb_img, dtype=np.uint8)
        gray = _prepare_guided_depth(arr, radius)

    out_path = build_output_path(path)
    _save_single_channel_exr(gray, out_path)
    logger.info("Saved: %s", out_path)
    return out_path


def _prepare_guided_depth(arr: np.ndarray, radius: float) -> np.ndarray:
    gray_u8 = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    if radius <= 0:
        return gray_u8.astype(np.float32) / 255.0

    base = cv2.medianBlur(gray_u8, 3)
    normalized = base.astype(np.float32) / 255.0
    guided_radius = max(2, int(round(radius * 4.0)))
    eps = max(1e-4, (0.01 * max(radius, 1.0)) ** 2)
    filtered = _guided_filter(normalized, normalized, guided_radius, eps)
    return np.clip(filtered, 0.0, 1.0)


def _guided_filter(guide: np.ndarray, src: np.ndarray, radius: float, eps: float) -> np.ndarray:
    ksize = (int(radius) * 2 + 1, int(radius) * 2 + 1)
    mean_guide = cv2.boxFilter(guide, ddepth=-1, ksize=ksize, borderType=cv2.BORDER_REFLECT)
    mean_src = cv2.boxFilter(src, ddepth=-1, ksize=ksize, borderType=cv2.BORDER_REFLECT)
    corr_guide = cv2.boxFilter(guide * guide, ddepth=-1, ksize=ksize, borderType=cv2.BORDER_REFLECT)
    corr_guide_src = cv2.boxFilter(guide * src, ddepth=-1, ksize=ksize, borderType=cv2.BORDER_REFLECT)

    var_guide = corr_guide - mean_guide * mean_guide
    cov_guide_src = corr_guide_src - mean_guide * mean_src

    a = cov_guide_src / (var_guide + eps)
    b = mean_src - a * mean_guide

    mean_a = cv2.boxFilter(a, ddepth=-1, ksize=ksize, borderType=cv2.BORDER_REFLECT)
    mean_b = cv2.boxFilter(b, ddepth=-1, ksize=ksize, borderType=cv2.BORDER_REFLECT)
    return mean_a * guide + mean_b


def _save_single_channel_exr(arr: np.ndarray, out_path: Path) -> None:
    if arr.ndim != 2:
        raise ValueError("Expected a single grayscale channel")

    import Imath
    import OpenEXR

    height, width = arr.shape
    header = OpenEXR.Header(width, height)
    header["compression"] = Imath.Compression(Imath.Compression.PIZ_COMPRESSION)
    header["channels"] = {"Y": Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))}

    exr_out = OpenEXR.OutputFile(str(out_path), header)
    try:
        exr_out.writePixels({"Y": np.ascontiguousarray(arr).tobytes()})
    finally:
        exr_out.close()
