from __future__ import annotations

import os
from pathlib import Path

from contexthub.ui.qt.shell import get_shell_metrics

from .auto_lod_inspect import load_preview_mesh
from .auto_lod_preview_fallback import FallbackMeshViewport
from .auto_lod_preview_opengl import OpenGlMeshViewport

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout
except ImportError as exc:
    raise ImportError("PySide6 is required for the Auto LOD preview widget.") from exc


SUPPORTED_PREVIEW_SUFFIXES = {".obj", ".stl", ".ply"}


class AutoLodPreviewCard(QFrame):
    file_dropped = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("card")
        self.setAcceptDrops(True)

        metrics = get_shell_metrics()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(metrics.panel_padding, metrics.panel_padding, metrics.panel_padding, metrics.panel_padding)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.title_label = QLabel("3D Preview")
        self.title_label.setObjectName("sectionTitle")
        header.addWidget(self.title_label)
        header.addStretch(1)

        self.view_label = QLabel("Display")
        self.view_label.setObjectName("eyebrow")
        header.addWidget(self.view_label)
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumWidth(140)
        header.addWidget(self.mode_combo)

        self.lod_label = QLabel("LOD")
        self.lod_label.setObjectName("eyebrow")
        header.addWidget(self.lod_label)
        self.lod_combo = QComboBox()
        self.lod_combo.setMinimumWidth(120)
        header.addWidget(self.lod_combo)
        self.lod_label.hide()
        self.lod_combo.hide()
        layout.addLayout(header)

        tools = QHBoxLayout()
        self.fit_btn = QPushButton("Fit")
        self.reset_btn = QPushButton("Reset")
        self.wireframe_btn = QPushButton("Wireframe")
        tools.addWidget(self.fit_btn)
        tools.addWidget(self.reset_btn)
        tools.addWidget(self.wireframe_btn)
        tools.addStretch(1)
        self.hint_label = QLabel("Orbit: Left drag  Pan: Right drag / Shift+drag  Zoom: Wheel")
        self.hint_label.setObjectName("summaryText")
        tools.addWidget(self.hint_label)
        layout.addLayout(tools)

        self.viewport = self._build_viewport()
        self.viewport.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.viewport_frame = QFrame()
        self.viewport_frame.setObjectName("subtlePanel")
        self.viewport_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.viewport_frame.setMinimumHeight(420)
        self.viewport_frame.setMaximumHeight(760)

        viewport_layout = QVBoxLayout(self.viewport_frame)
        viewport_layout.setContentsMargins(16, 16, 16, 16)
        viewport_layout.setSpacing(0)
        viewport_layout.addWidget(self.viewport, 1)

        layout.addWidget(self.viewport_frame, 1)

        self.status_label = QLabel("Preview available for OBJ, STL, and PLY.")
        self.status_label.setObjectName("summaryText")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.fit_btn.clicked.connect(self.viewport.fit_camera)
        self.reset_btn.clicked.connect(self.viewport.reset_camera)
        self.wireframe_btn.clicked.connect(self._toggle_wireframe)

    def _build_viewport(self):
        if os.environ.get("CTX_AUTO_LOD_EXPERIMENTAL_OPENGL") == "1":
            try:
                return OpenGlMeshViewport()
            except Exception:
                pass
        return FallbackMeshViewport()

    def set_view_modes(self, modes: list[tuple[str, str]], selected: str) -> None:
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        selected_index = 0
        for index, (value, label) in enumerate(modes):
            self.mode_combo.addItem(label, value)
            if value == selected:
                selected_index = index
        self.mode_combo.setCurrentIndex(selected_index)
        self.mode_combo.setEnabled(len(modes) > 1)
        self.mode_combo.blockSignals(False)

    def set_lod_choices(self, labels: list[str], selected_index: int) -> None:
        self.lod_combo.blockSignals(True)
        self.lod_combo.clear()
        for label in labels:
            self.lod_combo.addItem(label)
        if labels:
            self.lod_combo.setCurrentIndex(max(0, min(selected_index, len(labels) - 1)))
        self.lod_combo.setEnabled(bool(labels))
        self.lod_label.setVisible(bool(labels))
        self.lod_combo.setVisible(bool(labels))
        self.lod_combo.blockSignals(False)

    def set_preview_path(self, path: Path | None, status: str) -> None:
        self.status_label.setText(status)
        mesh = None
        if path is not None and path.exists() and path.suffix.lower() in SUPPORTED_PREVIEW_SUFFIXES:
            mesh = load_preview_mesh(path)
        self.viewport.set_preview_mesh(mesh, status)

    def _toggle_wireframe(self) -> None:
        enable_wire = self.wireframe_btn.text() == "Wireframe"
        self.viewport.set_wireframe(enable_wire)
        self.wireframe_btn.setText("Shaded" if enable_wire else "Wireframe")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.file_dropped.emit(Path(url.toLocalFile()))
                event.acceptProposedAction()
                return
        super().dropEvent(event)
