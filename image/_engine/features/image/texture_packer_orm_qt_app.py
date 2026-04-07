import os
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QEvent, QSize
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QFrame,
    QPushButton,
    QLineEdit,
    QLabel,
    QFileDialog,
    QComboBox,
    QGridLayout,
    QSizePolicy,
)

from contexthub.ui.qt.shell import (
    HeaderSurface,
    get_shell_metrics,
    get_shell_palette,
    build_shell_stylesheet,
    qt_t,
    apply_app_icon,
    attach_size_grip,
)
from contexthub.ui.qt.panels import (
    PreviewListPanel,
    FixedParameterPanel,
)
from shared._engine.components.icon_button import build_icon_button

from .texture_packer_orm_state import PackerState, SlotState
from .texture_packer_orm_service import TexturePackerService

class TexturePackerWindow(QMainWindow):
    def __init__(self, app_root: Path, targets: list[str] = None):
        super().__init__()
        self.app_root = app_root
        self.state = PackerState()
        self.service = TexturePackerService()
        
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(520, 800)
        self.setMinimumWidth(480)
        apply_app_icon(self, self.app_root)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)
        m = get_shell_metrics()
        self.root_layout.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)
        self.root_layout.setSpacing(m.section_gap)

        # Standard Window Shell
        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        self.main_layout = QVBoxLayout(self.window_shell)
        self.main_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        self.main_layout.setSpacing(m.section_gap)

        # Header
        self.header = HeaderSurface(
            self,
            title="Texture Packer",
            subtitle="Channel-based Map Packing Tool",
            app_root=self.app_root
        )
        self.header.set_header_visibility(
            show_subtitle=False,
            show_asset_count=False,
            show_runtime_status=False,
        )
        self.main_layout.addWidget(self.header)
        
        # Preset Selector
        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(m.panel_padding, 0, m.panel_padding, 0)
        preset_row.addWidget(QLabel("Map Preset:"), 0)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.state.presets.keys()))
        self.preset_combo.setFixedWidth(180)
        preset_row.addWidget(self.preset_combo)
        preset_row.addStretch(1)
        self.main_layout.addLayout(preset_row)

        # Body: Slot Focused UI
        self.body_container = QWidget()
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        self.body_layout.setSpacing(m.section_gap)
        
        # Grid for Slots
        self.slots_card = QFrame()
        self.slots_card.setObjectName("card")
        slots_layout = QVBoxLayout(self.slots_card)
        slots_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        slots_layout.setSpacing(m.section_gap)
        
        slots_title = QLabel("Channel Assignments")
        slots_title.setObjectName("sectionTitle")
        slots_layout.addWidget(slots_title)
        
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.setRowStretch(0, 1)
        self.grid.setRowStretch(1, 1)
        self._build_grid_slots()
        slots_layout.addLayout(self.grid)
        
        self.body_layout.addWidget(self.slots_card, 1)
        
        # Compact Export
        palette = get_shell_palette()
        self.pack_save_btn = build_icon_button(qt_t("texture_packer.pack_save", "Pack & Save"), icon_name="save", role="primary")
        self.pack_save_btn.setProperty("buttonRole", "primary")
        self.pack_save_btn.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        self.body_layout.addWidget(self.pack_save_btn)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("summaryText")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.body_layout.addWidget(self.status_label)
        
        self.main_layout.addWidget(self.body_container, 1)
        
        # Shell Closing
        self.size_grip = attach_size_grip(self.main_layout, self.window_shell)
        self.root_layout.addWidget(self.window_shell)

        self.setStyleSheet(build_shell_stylesheet())
        self._bind_actions()
        self._on_preset_changed() # Initialize labels from default preset
        
        if targets:
            self._auto_fill(Path(targets[0]))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Refresh all loaded slots to rescale images to new window size
        for key in self.slot_widgets:
            if self.state.slots[key].path:
                self._update_slot_visuals(key, self.state.slots[key].path)

    def _build_grid_slots(self):
        self.slot_widgets = {}
        slots_info = [
            ('r', 0, 0),
            ('g', 0, 1),
            ('b', 1, 0),
            ('a', 1, 1)
        ]
        
        for key, row_idx, col_idx in slots_info:
            palette = get_shell_palette()
            slot_frame = QFrame()
            slot_frame.setObjectName("subtlePanel")
            slot_layout = QVBoxLayout(slot_frame)
            slot_layout.setContentsMargins(10, 10, 10, 10)
            slot_layout.setSpacing(8)
            
            # Header with Name Edit
            header_row = QHBoxLayout()
            name_edit = QLineEdit(self.state.slots[key].label)
            name_edit.setObjectName("eyebrow")
            name_edit.setStyleSheet(
                f"border: none; background: transparent; font-weight: bold; font-size: 13px; color: {palette.text_muted};"
            )
            header_row.addWidget(name_edit)
            header_row.addStretch(1)
            slot_layout.addLayout(header_row)
            
            # UX: Large Clickable Preview with Overlays
            preview_container = QFrame()
            preview_container.setObjectName("imagePreview")
            preview_container.setMinimumHeight(120)
            preview_container.setCursor(Qt.PointingHandCursor)
            preview_container.setStyleSheet(
                f"border-radius: 8px; background: {palette.field_bg}; border: 1px solid {palette.control_border};"
            )
            
            pc_layout = QVBoxLayout(preview_container)
            pc_layout.setContentsMargins(5, 5, 5, 5)
            
            # Preview Label
            preview_label = QLabel()
            preview_label.setAlignment(Qt.AlignCenter)
            preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            preview_label.setStyleSheet("background: transparent; border-radius: 4px;")
            pc_layout.addWidget(preview_label)
            
            # Overlay Row (Hidden by default)
            overlay_frame = QFrame(preview_container)
            overlay_frame.setStyleSheet(
                f"background: {palette.window_shell_bg}; border-radius: 8px; border: 1px solid {palette.control_border};"
            )
            overlay_frame.hide()
            
            overlay_layout = QHBoxLayout(overlay_frame)
            overlay_layout.setContentsMargins(10, 0, 10, 0)
            
            label_hint = QLabel("Click to Change")
            label_hint.setStyleSheet(f"color: {palette.text}; font-size: 11px; font-weight: bold;")
            overlay_layout.addWidget(label_hint, 1, Qt.AlignCenter)
            
            invert_btn = QPushButton("±")
            invert_btn.setObjectName("iconBtn")
            invert_btn.setToolTip("Invert Channel")
            invert_btn.setFixedSize(28, 28)
            overlay_layout.addWidget(invert_btn)
            
            clear_btn = QPushButton("✕")
            clear_btn.setObjectName("iconBtn")
            clear_btn.setToolTip("Clear")
            clear_btn.setFixedSize(28, 28)
            overlay_layout.addWidget(clear_btn)
            
            slot_layout.addWidget(preview_container, 1)
            
            path_label = QLabel("Drop here")
            path_label.setObjectName("mutedSmall")
            path_label.setAlignment(Qt.AlignCenter)
            path_label.setStyleSheet("font-size: 11px;")
            slot_layout.addWidget(path_label)
            
            self.grid.addWidget(slot_frame, row_idx, col_idx)
            self.slot_widgets[key] = {
                "path": path_label, 
                "preview": preview_label, 
                "name": name_edit, 
                "invert": invert_btn,
                "clear": clear_btn,
                "frame": slot_frame,
                "preview_box": preview_container,
                "overlay": overlay_frame
            }
            
            # Event Filters for Hover & Click
            slot_frame.installEventFilter(self)
            preview_container.installEventFilter(self)
            
            # Bindings
            name_edit.textChanged.connect(lambda t, k=key: self._on_name_changed(k, t))
            invert_btn.clicked.connect(lambda _, k=key: self._toggle_invert(k))
            clear_btn.clicked.connect(lambda _, k=key: self._clear_slot(k))

    def eventFilter(self, obj, event):
        for key, widgets in self.slot_widgets.items():
            if obj == widgets["preview_box"]:
                if event.type() == QEvent.Enter:
                    widgets["overlay"].show()
                    widgets["overlay"].setGeometry(0, 0, widgets["preview_box"].width(), widgets["preview_box"].height())
                elif event.type() == QEvent.Leave:
                    widgets["overlay"].hide()
                elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                    self._pick_file(key)
        return super().eventFilter(obj, event)

    def _toggle_invert(self, key):
        self.state.slots[key].invert = not self.state.slots[key].invert
        btn = self.slot_widgets[key]["invert"]
        palette = get_shell_palette()
        if self.state.slots[key].invert:
            btn.setStyleSheet(
                f"background: {palette.accent}; color: {palette.accent_text}; border-radius: 4px; border: 1px solid {palette.accent};"
            )
        else:
            btn.setStyleSheet("")
        self._update_slot_visuals(key, self.state.slots[key].path)

    def _on_name_changed(self, key, text):
        self.state.slots[key].label = text

    def _on_preset_changed(self):
        preset_name = self.preset_combo.currentText()
        mapping = self.state.presets.get(preset_name, {})
        for key, name in mapping.items():
            if key in self.slot_widgets:
                self.slot_widgets[key]["name"].setText(name)
        self.state.current_preset = preset_name

    def _update_slot_visuals(self, key, path: Path | None):
        widgets = self.slot_widgets[key]
        path_label = widgets["path"]
        preview_label = widgets["preview"]
        
        if path:
            path_label.setText(path.name)
            try:
                # Force Grayscale as requested
                from PIL import Image
                img = Image.open(path).convert("L")
                if self.state.slots[key].invert:
                    from PIL import ImageOps
                    img = ImageOps.invert(img)
                
                # Convert PIL to QImage (Grayscale8)
                data = img.tobytes("raw", "L")
                qimg = QImage(data, img.size[0], img.size[1], QImage.Format_Grayscale8)
                pixmap = QPixmap.fromImage(qimg)
                
                # Scale to fit current container size while keeping aspect ratio
                container_size = widgets["preview_box"].size()
                if container_size.width() > 10 and container_size.height() > 10:
                    scaled_pm = pixmap.scaled(
                        container_size - QSize(10, 10), 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    preview_label.setPixmap(scaled_pm)
                else:
                    preview_label.setPixmap(pixmap)
            except Exception as e:
                preview_label.setText("!")
        else:
            path_label.setText("Drop here")
            preview_label.clear()

    def _bind_actions(self):
        self.pack_save_btn.clicked.connect(self._on_run_clicked)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)

    def _pick_file(self, key):
        file, _ = QFileDialog.getOpenFileName(self, "Select Texture", "", "Images (*.png *.jpg *.exr *.tga *.tiff)")
        if file:
            self._set_slot_file(key, Path(file))

    def _clear_slot(self, key):
        self.state.slots[key].path = None
        self._update_slot_visuals(key, None)
        self._update_title()

    def _set_slot_file(self, key, path: Path):
        self.state.slots[key].path = path
        self._update_slot_visuals(key, path)
        self._auto_fill(path) # Try to find others
        self._update_title()

    def _auto_fill(self, base_path: Path):
        labels = {k: self.state.slots[k].label for k in self.state.slots}
        results = self.service.auto_parse(base_path, labels)
        for k, p in results.items():
            if not self.state.slots[k].path:
                self.state.slots[k].path = p
                self._update_slot_visuals(k, p)

    def _update_title(self):
        return None

    def _on_run_clicked(self):
        # Validation
        if not any(s.path for s in self.state.slots.values()):
            self.status_label.setText("Error: No textures assigned")
            return
            
        ext = self.state.output_format
        output_file, _ = QFileDialog.getSaveFileName(self, "Save Packed Texture", f"Packed_Map{ext}", f"Packed (*{ext})")
        
        if output_file:
            self.header.set_loading(True)
            self.status_label.setText("Packing & Saving...")
            
            # Prepare data
            slots_data = {k: s.path for k, s in self.state.slots.items()}
            labels = {}
            for k, s in self.state.slots.items():
                labels[k] = s.label
                if s.invert:
                    labels[f"{k}_invert"] = True
            
            self.service.pack_textures(
                slots_data,
                labels,
                Path(output_file),
                None,
                self._on_complete
            )

    def _on_complete(self, success, message):
        self.header.set_loading(False)
        if success:
            self.status_label.setText(f"Saved: {os.path.basename(message)}")
        else:
            self.status_label.setText(f"Error: {message}")

def main():
    app = QApplication(sys.argv)
    app_root = Path(os.environ.get("CTX_APP_ROOT", "."))
    window = TexturePackerWindow(app_root, sys.argv[1:])
    window.show()
    sys.exit(app.exec())
