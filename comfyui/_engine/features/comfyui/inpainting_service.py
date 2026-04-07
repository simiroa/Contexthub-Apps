"""Inpainting service layer (stub).

Manages application state for the inpainting workflow.
Actual ComfyUI API calls are deferred to Phase 2.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class InpaintingState:
    source_path: Optional[Path] = None
    mask_ready: bool = False
    prompt: str = ""
    negative_prompt: str = "low quality, blurry, text, watermark"
    steps: int = 20
    cfg: float = 7.0
    denoise: float = 0.75
    sampler: str = "euler"
    scheduler: str = "normal"
    seed: int = -1
    checkpoint: str = ""
    output_dir: Path = field(default_factory=lambda: Path.home() / "Desktop" / "inpainting_output")
    file_prefix: str = "inpaint"
    open_folder_after_run: bool = True


class InpaintingService:
    """Business-logic service for the inpainting app.

    Phase 1: manages state, validates readiness, returns stubs.
    Phase 2: will connect to ComfyUIManager for actual execution.
    """

    def __init__(self) -> None:
        self.state = InpaintingState()
        self._checkpoint_options: list[str] = []

    # ------------------------------------------------------------------
    # Image management
    # ------------------------------------------------------------------

    def set_source_image(self, path: str | Path) -> bool:
        p = Path(path)
        if p.exists() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
            self.state.source_path = p
            return True
        return False

    def set_mask_ready(self, ready: bool) -> None:
        self.state.mask_ready = ready

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------

    def update_parameter(self, key: str, value: Any) -> None:
        if hasattr(self.state, key):
            setattr(self.state, key, value)

    def get_checkpoint_options(self) -> list[str]:
        return self._checkpoint_options

    # ------------------------------------------------------------------
    # Runtime probe (stub)
    # ------------------------------------------------------------------

    def probe_runtime(self) -> tuple[str, str]:
        """Check if ComfyUI is reachable. Returns (message, level)."""
        try:
            from manager.helpers.comfyui_service import ComfyUIService
            svc = ComfyUIService()
            running, port = svc.is_running()
            if running:
                # Refresh checkpoint options
                options = svc.client.get_input_options("CheckpointLoaderSimple", "ckpt_name")
                if options:
                    self._checkpoint_options = options
                return f"Connected to ComfyUI on port {port}.", "ready"
            return "ComfyUI is not running.", "warning"
        except Exception as exc:
            return f"ComfyUI probe failed: {exc}", "error"

    # ------------------------------------------------------------------
    # Execution (stub for Phase 2)
    # ------------------------------------------------------------------

    def can_run(self) -> tuple[bool, str]:
        if self.state.source_path is None:
            return False, "No source image loaded."
        if not self.state.mask_ready:
            return False, "No mask painted."
        if not self.state.prompt.strip():
            return False, "Prompt is empty."
        return True, "Ready to run."

    def run_inpainting(self, mask_image) -> tuple[bool, str, Optional[Path]]:
        """Execute inpainting. Returns (success, message, result_path).

        Phase 1: Stub that exports the mask and logs parameters.
        Phase 2: Will upload image+mask → queue workflow → download result.
        """
        ok, reason = self.can_run()
        if not ok:
            return False, reason, None

        # Phase 1 stub: save mask to output dir
        self.state.output_dir.mkdir(parents=True, exist_ok=True)
        mask_path = self.state.output_dir / f"{self.state.file_prefix}_mask.png"
        if mask_image is not None:
            try:
                mask_image.save(str(mask_path))
            except Exception:
                pass

        return True, "Phase 1 stub: mask exported. Workflow execution deferred.", mask_path

    def reveal_output_dir(self) -> None:
        self.state.output_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(self.state.output_dir)  # type: ignore[attr-defined]
