from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from features.document.doc_scan_state import DocScanState, ScanItem


class DocScanService:
    def __init__(self, state: DocScanState) -> None:
        self.state = state

    def load_targets(self, targets: List[str]) -> None:
        valid_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        for path_str in targets:
            path = Path(path_str)
            if path.suffix.lower() not in valid_exts or not path.exists():
                continue
            image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is not None:
                item = ScanItem(path=path, image=image)
                # Initialize default corners (top-left, top-right, bottom-right, bottom-left)
                item.corners = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]
                self.state.items.append(item)
        
        if self.state.items and self.state.current_index < 0:
            self.state.current_index = 0

    def load_signature(self, path_str: str) -> bool:
        path = Path(path_str)
        if not path.exists():
            return False
        image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if image is not None:
            self.state.signature_image = image
            self.state.signature_path = path
            return True
        return False

    def get_rendered_image(self, index: int, apply_signature: bool = True) -> Optional[np.ndarray]:
        if not (0 <= index < len(self.state.items)):
            return None
        
        item = self.state.items[index]
        image = item.image.copy()
        
        # 1. Rotation (apply before unwarp or after? Usually after for raw scan, but here we follow initial logic)
        if item.rotation == 90:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif item.rotation == 180:
            image = cv2.rotate(image, cv2.ROTATE_180)
        elif item.rotation == 270:
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
        # 2. Perspective Unwarp
        if item.unwarp_active and item.corners:
            h, w = image.shape[:2]
            src_pts = np.float32([[c[0] * w, c[1] * h] for c in item.corners])
            
            # Calculate output dimensions (standardize to a rectangle)
            # Find max width and height among edges
            width_a = np.sqrt(((src_pts[2][0] - src_pts[3][0]) ** 2) + ((src_pts[2][1] - src_pts[3][1]) ** 2))
            width_b = np.sqrt(((src_pts[1][0] - src_pts[0][0]) ** 2) + ((src_pts[1][1] - src_pts[0][1]) ** 2))
            max_w = max(int(width_a), int(width_b))
            
            height_a = np.sqrt(((src_pts[1][0] - src_pts[2][0]) ** 2) + ((src_pts[1][1] - src_pts[2][1]) ** 2))
            height_b = np.sqrt(((src_pts[0][0] - src_pts[3][0]) ** 2) + ((src_pts[0][1] - src_pts[3][1]) ** 2))
            max_h = max(int(height_a), int(height_b))
            
            dst_pts = np.float32([[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]])
            matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
            image = cv2.warpPerspective(image, matrix, (max_w, max_h))

        # 3. Filter
        if item.filter_type == "bw":
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10)
            image = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
        elif item.filter_type == "magic":
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            v_eq = clahe.apply(v)
            s_eq = cv2.add(s, 50)
            hsv_eq = cv2.merge((h, s_eq, v_eq))
            colored = cv2.cvtColor(hsv_eq, cv2.COLOR_HSV2BGR)
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            image = cv2.filter2D(colored, -1, kernel)
            
        # 4. Signature Overlay
        if apply_signature and self.state.signature_image is not None and item.signature_pos:
            image = self._overlay_signature(image, self.state.signature_image, item.signature_pos, item.signature_scale)
            
        return image

    def _overlay_signature(self, base: np.ndarray, sig: np.ndarray, pos: Tuple[float, float], scale: float) -> np.ndarray:
        bh, bw = base.shape[:2]
        
        # Calculate signature size based on base width
        target_w = int(bw * scale)
        sh, sw = sig.shape[:2]
        ratio = target_w / sw
        target_h = int(sh * ratio)
        
        sig_resized = cv2.resize(sig, (target_w, target_h), interpolation=cv2.INTER_AREA)
        
        # Calculate top-left from normalized center pos
        cx, cy = int(pos[0] * bw), int(pos[1] * bh)
        tx, ty = cx - target_w // 2, cy - target_h // 2
        
        # Bounds check and clipping
        x1, y1 = max(0, tx), max(0, ty)
        x2, y2 = min(bw, tx + target_w), min(bh, ty + target_h)
        
        # If clipped out completely
        if x1 >= x2 or y1 >= y2:
            return base
            
        # Portion of signature to overlay
        sx1, sy1 = x1 - tx, y1 - ty
        sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)
        
        overlay = sig_resized[sy1:sy2, sx1:sx2]
        roi = base[y1:y2, x1:x2]
        
        if overlay.shape[2] == 4:  # With Alpha
            alpha = overlay[:, :, 3] / 255.0
            alpha_inv = 1.0 - alpha
            
            for c in range(3):
                roi[:, :, c] = (alpha * overlay[:, :, c] + alpha_inv * roi[:, :, c])
        else:
            base[y1:y2, x1:x2] = overlay[:, :, :3]
            
        return base

    def update_item_corners(self, index: int, corners: List[Tuple[float, float]]) -> None:
        if 0 <= index < len(self.state.items):
            self.state.items[index].corners = corners

    def set_unwarp(self, index: int, active: bool) -> None:
        if 0 <= index < len(self.state.items):
            self.state.items[index].unwarp_active = active

    def set_signature_pos(self, index: int, pos: Optional[Tuple[float, float]]) -> None:
        if 0 <= index < len(self.state.items):
            self.state.items[index].signature_pos = pos

    def set_signature_scale(self, index: int, scale: float) -> None:
        if 0 <= index < len(self.state.items):
            self.state.items[index].signature_scale = scale

    def update_item_rotation(self, index: int, delta: int) -> None:
        if 0 <= index < len(self.state.items):
            self.state.items[index].rotation = (self.state.items[index].rotation + delta) % 360

    def update_item_filter(self, index: int, filter_type: str) -> None:
        if 0 <= index < len(self.state.items):
            self.state.items[index].filter_type = filter_type

    def reset_item(self, index: int) -> None:
        if 0 <= index < len(self.state.items):
            item = self.state.items[index]
            item.rotation = 0
            item.filter_type = "orig"
            item.unwarp_active = False
            item.signature_pos = None

    def save_current_as_png(self, index: int) -> str:
        if not (0 <= index < len(self.state.items)):
            return "Error: No item selected"
        
        item = self.state.items[index]
        rendered = self.get_rendered_image(index)
        output = item.path.with_stem(f"{item.path.stem}_scanned").with_suffix(".png")
        cv2.imencode(".png", rendered)[1].tofile(output)
        return str(output)

    def save_all_as_pdf(self) -> str:
        if not self.state.items:
            return "Error: No items to save"
            
        output = self.state.items[0].path.with_stem(f"{self.state.items[0].path.stem}_batch_scanned").with_suffix(".pdf")
        pil_images = []
        for i in range(len(self.state.items)):
            rendered = self.get_rendered_image(i)
            rgb = cv2.cvtColor(rendered, cv2.COLOR_BGR2RGB)
            pil_images.append(Image.fromarray(rgb))
            
        pil_images[0].save(output, "PDF", resolution=100.0, save_all=True, append_images=pil_images[1:])
        return str(output)
