from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from features.document.doc_scan_state import DocScanState


class DocScanService:
    def __init__(self, state: DocScanState) -> None:
        self.state = state

    def load_image(self, path_str: str) -> bool:
        path = Path(path_str)
        if not path.exists():
            return False
        image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return False
        self.state.image_path = path
        self.state.image = image
        self.state.corners = self._detect_corners(image)
        return True

    def load_targets(self, targets: List[str]) -> None:
        if targets:
            self.load_image(targets[0])

    def reset_corners(self) -> bool:
        if self.state.image is None:
            return False
        self.state.corners = self._detect_corners(self.state.image)
        return True

    def rotate_image(self, clockwise: bool) -> bool:
        if self.state.image is None:
            return False
        rotation = cv2.ROTATE_90_CLOCKWISE if clockwise else cv2.ROTATE_90_COUNTERCLOCKWISE
        self.state.image = cv2.rotate(self.state.image, rotation)
        self.state.corners = self._detect_corners(self.state.image)
        return True

    def _detect_corners(self, image: np.ndarray) -> List[Tuple[float, float]]:
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 75, 200)

        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        for c in contours[:5]:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                pts = approx.reshape(4, 2).astype(float)
                pts[:, 0] /= w
                pts[:, 1] /= h
                return _order_points(pts.tolist())

        return [(0.05, 0.05), (0.95, 0.05), (0.95, 0.95), (0.05, 0.95)]

    def get_warped(self) -> Optional[np.ndarray]:
        if self.state.image is None:
            return None
        h, w = self.state.image.shape[:2]
        src = np.float32([[c[0] * w, c[1] * h] for c in self.state.corners])
        tl, tr, br, bl = src

        out_w = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
        out_h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))

        if out_w < 1 or out_h < 1:
            result = self.state.image.copy()
        else:
            dst = np.float32([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]])
            M = cv2.getPerspectiveTransform(src, dst)
            result = cv2.warpPerspective(self.state.image, M, (out_w, out_h))

        if self.state.is_grayscale:
            result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        return result

    def toggle_grayscale(self) -> None:
        self.state.is_grayscale = not self.state.is_grayscale

    def load_signature(self, path_str: str) -> bool:
        path = Path(path_str)
        if not path.exists():
            return False
        sig_image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if sig_image is None:
            return False
        self.state.signature_image = sig_image
        self.state.signature_path = path
        return True

    def _overlay_signature(self, image: np.ndarray) -> np.ndarray:
        if self.state.signature_image is None:
            return image
        result = image.copy()
        h, w = image.shape[:2]
        sig = self.state.signature_image
        sig_h, sig_w = sig.shape[:2]
        if sig_w <= 0 or sig_h <= 0:
            return result
        scaled_w = max(1, int(w * self.state.signature_scale))
        scaled_h = max(1, int(sig_h * scaled_w / sig_w))
        sig_resized = cv2.resize(sig, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
        x = int(w * self.state.signature_x - scaled_w / 2)
        y = int(h * self.state.signature_y - scaled_h / 2)
        x = max(0, min(x, w - scaled_w))
        y = max(0, min(y, h - scaled_h))

        if sig_resized.ndim == 2:
            sig_rgb = cv2.cvtColor(sig_resized, cv2.COLOR_GRAY2BGR)
            alpha_chan = None
        elif sig_resized.shape[2] == 4:
            sig_rgb = sig_resized[:, :, :3]
            alpha_chan = sig_resized[:, :, 3].astype(np.float32) / 255.0
        else:
            sig_rgb = sig_resized
            alpha_chan = None

        opacity = self.state.signature_opacity / 100.0
        region = result[y:y+scaled_h, x:x+scaled_w].astype(np.float32)
        sig_f = sig_rgb.astype(np.float32)

        mode = getattr(self.state, "signature_blend_mode", "normal")
        if mode == "multiply":
            blended = region * sig_f / 255.0
        elif mode == "darken":
            blended = np.minimum(region, sig_f)
        else:
            blended = sig_f

        if alpha_chan is not None:
            a = (alpha_chan * opacity)[:, :, np.newaxis]
            out = region * (1.0 - a) + blended * a
        else:
            out = region * (1.0 - opacity) + blended * opacity

        result[y:y+scaled_h, x:x+scaled_w] = np.clip(out, 0, 255).astype(np.uint8)
        return result

    def save_png(self, output_path: str) -> bool:
        warped = self.get_warped()
        if warped is None:
            return False
        with_signature = self._overlay_signature(warped)
        cv2.imencode(".png", with_signature)[1].tofile(Path(output_path))
        return True


def _order_points(pts: list) -> List[Tuple[float, float]]:
    """Sort 4 points into TL, TR, BR, BL order."""
    pts_sorted = sorted(pts, key=lambda p: p[1])
    top = sorted(pts_sorted[:2], key=lambda p: p[0])
    bottom = sorted(pts_sorted[2:], key=lambda p: p[0])
    return [tuple(top[0]), tuple(top[1]), tuple(bottom[1]), tuple(bottom[0])]
