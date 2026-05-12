from __future__ import annotations

from typing import List, Tuple

try:
    from PySide6.QtGui import QUndoCommand
except ImportError as exc:
    raise ImportError("PySide6 is required for doc_scan.") from exc

from features.document.doc_scan_service import DocScanService
from features.document.doc_scan_state import DocScanState


class CornerAdjustCommand(QUndoCommand):
    def __init__(self, state: DocScanState, idx: int, old: Tuple[float, float], new: Tuple[float, float]) -> None:
        super().__init__(f"Adjust corner {idx + 1}")
        self.state = state
        self.idx = idx
        self.old = old
        self.new = new

    def redo(self) -> None:
        self.state.corners[self.idx] = self.new

    def undo(self) -> None:
        self.state.corners[self.idx] = self.old


class RotateImageCommand(QUndoCommand):
    def __init__(self, service: DocScanService, clockwise: bool) -> None:
        super().__init__("Rotate image")
        self.service = service
        self.clockwise = clockwise

    def redo(self) -> None:
        self.service.rotate_image(self.clockwise)

    def undo(self) -> None:
        self.service.rotate_image(not self.clockwise)


class ResetCornersCommand(QUndoCommand):
    def __init__(self, service: DocScanService, old_corners: List[Tuple[float, float]]) -> None:
        super().__init__("Reset corners")
        self.service = service
        self.old_corners = old_corners

    def redo(self) -> None:
        self.service.reset_corners()

    def undo(self) -> None:
        self.service.state.corners = self.old_corners.copy()


class GrayscaleToggleCommand(QUndoCommand):
    def __init__(self, service: DocScanService) -> None:
        super().__init__("Toggle grayscale")
        self.service = service

    def redo(self) -> None:
        self.service.toggle_grayscale()

    def undo(self) -> None:
        self.service.toggle_grayscale()


class SignaturePositionCommand(QUndoCommand):
    def __init__(self, state: DocScanState, old_x: float, old_y: float, new_x: float, new_y: float) -> None:
        super().__init__("Move signature")
        self.state = state
        self.old_x = old_x
        self.old_y = old_y
        self.new_x = new_x
        self.new_y = new_y

    def redo(self) -> None:
        self.state.signature_x = self.new_x
        self.state.signature_y = self.new_y

    def undo(self) -> None:
        self.state.signature_x = self.old_x
        self.state.signature_y = self.old_y


class SignatureScaleCommand(QUndoCommand):
    def __init__(self, state: DocScanState, old_scale: float, new_scale: float) -> None:
        super().__init__("Resize signature")
        self.state = state
        self.old_scale = old_scale
        self.new_scale = new_scale

    def redo(self) -> None:
        self.state.signature_scale = self.new_scale

    def undo(self) -> None:
        self.state.signature_scale = self.old_scale
