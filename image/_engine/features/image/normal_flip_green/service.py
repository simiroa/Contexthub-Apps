from pathlib import Path
from typing import Iterable, List, Tuple
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

logger = setup_logger("normal_flip_service")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff", ".bmp", ".webp"}


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
        if path.stem.lower().endswith("_flipped"):
            errors.append(f"{path.name}: Skipped already flipped output")
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


def flip_green_file(path: Path) -> Path:
    with Image.open(path) as img:
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")

        arr = np.array(img)
        if arr.ndim < 3 or arr.shape[2] < 3:
            raise ValueError("Image does not contain RGB channels")

        if arr.dtype == np.uint8:
            arr[:, :, 1] = 255 - arr[:, :, 1]
        elif arr.dtype == np.uint16:
            arr[:, :, 1] = 65535 - arr[:, :, 1]
        else:
            max_val = np.max(arr[:, :, 1])
            arr[:, :, 1] = max_val - arr[:, :, 1]

        out_path = path.parent / f"{path.stem}_flipped{path.suffix}"
        Image.fromarray(arr).save(out_path)
        logger.info("Saved: %s", out_path)
        return out_path


def flip_green_batch(files: List[Path]) -> Tuple[int, List[str], List[Path]]:
    count = 0
    errors: List[str] = []
    outputs: List[Path] = []

    for path in files:
        try:
            outputs.append(flip_green_file(path))
            count += 1
        except Exception as exc:
            logger.error("Failed to flip %s: %s", path.name, exc)
            errors.append(f"{path.name}: {exc}")

    return count, errors, outputs
