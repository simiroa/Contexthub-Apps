from __future__ import annotations

import sys
import math
import os
from pathlib import Path
from typing import Any
from PIL import Image

from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    get_shell_palette,
    qt_t,
)
from features.image.image_resizer_service import ImageResizerService
from features.image.comparison_preview_widget import ComparisonPreviewWidget

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, Signal, QRectF, QPointF
    from PySide6.QtGui import QPixmap, QPainter, QImage, QTransform, QBrush, QColor, QIntValidator
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QScrollArea,
        QVBoxLayout,
        QWidget,
        QPushButton,
        QGraphicsView,
        QGraphicsScene,
        QGraphicsPixmapItem,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for resize_power_of_2.") from exc

# Shared Components
from shared._engine.components.shell_frame import build_shell_window, finish_shell_window
from shared._engine.components.image_preview_card import build_image_preview_card
from shared._engine.components.parameter_controls_card import ParameterCard
from shared._engine.components.mini_execute_card import MiniExecuteCard
from shared._engine.components.icon_button import build_icon_button

APP_ID = "image_resizer"
APP_TITLE = qt_t("image_resizer.title", "Image Resizer")
APP_SUBTITLE = qt_t("image_resizer.subtitle", "Versatile Scaling Utility")


class ToggleButtonStrip(QWidget):
    """Horizontal strip of toggle buttons for selecting a mode."""
    valueChanged = Signal(str)

    def __init__(self, options: list[str], current_value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 2, 0, 8)
        self.layout.setSpacing(4)

        self.buttons = {}
        for opt in options:
            btn = build_icon_button(opt, role="secondary" if opt != current_value else "primary")
            btn.setFixedHeight(24)
            btn.setCheckable(True)
            btn.setChecked(opt == current_value)
            
            # Initial Style
            if opt == current_value:
                btn.setStyleSheet("background-color: #3b82f6; color: white; border-radius: 4px; font-weight: bold;")
            else:
                btn.setStyleSheet("background-color: #2d3748; color: #a0aec0; border-radius: 4px;")
                
            btn.clicked.connect(lambda _, val=opt: self._on_clicked(val))
            self.layout.addWidget(btn)
            self.buttons[opt] = btn

    def _on_clicked(self, value: str) -> None:
        for opt, btn in self.buttons.items():
            is_active = (opt == value)
            btn.setChecked(is_active)
            self._apply_button_style(btn, is_active)
        self.valueChanged.emit(value)

    def _apply_button_style(self, btn: QPushButton, is_active: bool) -> None:
        if is_active:
            btn.setStyleSheet("background-color: #3b82f6; color: white; border-radius: 4px; font-weight: bold; border: none;")
        else:
            btn.setStyleSheet("background-color: #2d3748; color: #a0aec0; border-radius: 4px; border: 1px solid transparent;")
        btn.style().unpolish(btn)
        btn.style().polish(btn)

class VerticalParameterRow(QWidget):
    """Local helper for vertical label (eyebrow) + field layout."""
    def __init__(self, label_text: str, field: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 8)
        layout.setSpacing(6)
        
        self.label = QLabel(label_text.upper())
        self.label.setObjectName("eyebrow")
        self.label.setStyleSheet("font-size: 10px; opacity: 0.8; font-weight: bold; color: #8892b0;")
        
        self.field = field
        layout.addWidget(self.label)
        layout.addWidget(self.field)







class ImageResizerWindow(QMainWindow):
    def __init__(self, service: ImageResizerService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Spacious UI: 380px Width, 810px Height (+160 for comfort)
        self.setFixedWidth(380)
        self.setMinimumHeight(810)
        
        # Enable Drag and Drop
        self.setAcceptDrops(True)
        
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        # Preview Debounce Timer
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(250)
        self._preview_timer.timeout.connect(self._refresh_preview_live)

        if targets:
            self.service.add_inputs(targets)
        self._refresh_parameter_form()
        self._refresh_assets()

    def _build_ui(self) -> None:
        # 1. Base Shell
        self.central, self.shell, self.shell_layout = build_shell_window(
            self, self.app_root, APP_TITLE, "", use_size_grip=True
        )
        self.shell_layout.setContentsMargins(8, 8, 8, 8)

        # 2. Scrollable Content Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(12)
        
        # 3. Immersive Preview
        self.preview_view = ComparisonPreviewWidget()
        self.preview_view.setMinimumHeight(240)
        self.content_layout.addWidget(self.preview_view)
        
        # Floating metadata overlay label
        self.meta_overlay = QLabel("-", self.preview_view)
        self.meta_overlay.setObjectName("summaryText")
        self.meta_overlay.setStyleSheet("background: rgba(0,0,0,0.4); color: white; padding: 2px 6px; border-radius: 4px;")
        self.meta_overlay.move(10, 10)

        # Parameters (Vertical labels)
        self.param_card = ParameterCard("Optimization Settings")
        self.param_card.layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.addWidget(self.param_card)
        
        # Execution (One-Line Footer: Open | Format | Save)
        self.export_card = MiniExecuteCard("Save")
        self.export_card.layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.addWidget(self.export_card)
        
        self.content_layout.addStretch(1)
        self.scroll.setWidget(self.content_widget)
        self.shell_layout.addWidget(self.scroll, 1)
        
        finish_shell_window(self.shell_layout, self.shell, use_size_grip=True)

    def _bind_actions(self) -> None:
        
        self.export_card.run_clicked.connect(self._run_workflow)
        # Note: Reveal is hidden, but can still be triggered after success if we want
        # self.export_card.reveal_clicked.connect(self.service.reveal_output_dir)

    def _refresh_parameter_form(self) -> None:
        label_map = {
            "mode": "Upscale Method",
            "target_type": "Resize Mode",
            "scale_factor": "Scale Factor",
            "custom_width": "Width",
            "custom_height": "Height",
            "aspect_locked": "Link Aspect",
            "po2_size": "POT Size",
            "force_square": "Square 1:1"
        }

        # Clear existing rows
        while self.param_card.rows_layout.count():
            item = self.param_card.rows_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        self.param_rows = {}

        # Custom Row (Horizontal for W/H with central Link Button)
        custom_row_widget = QWidget()
        custom_row_layout = QHBoxLayout(custom_row_widget)
        custom_row_layout.setContentsMargins(0, 0, 0, 0)
        custom_row_layout.setSpacing(4)
        self.custom_container = custom_row_widget

        parameter_order = ["mode", "target_type", "scale_factor", "custom_width", "link_aspect", "custom_height", "po2_size", "force_square"]
        
        for key in parameter_order:
            if key == "link_aspect":
                self.link_btn = build_icon_button("", icon_name="link-2", role="secondary", is_icon_only=True)
                self.link_btn.setCheckable(True)
                self.link_btn.setChecked(self.service.state.parameter_values.get("aspect_locked", True))
                self.link_btn.toggled.connect(lambda b: self._on_param_changed("aspect_locked", b))
                
                # Ensure 32px height and consistent styling
                self.link_btn.setFixedHeight(32)
                self.link_btn.setFixedWidth(32)
                self.link_btn.setStyleSheet("""
                    QPushButton { 
                        background: #2d3748; 
                        border: 1px solid #3f4e64;
                        border-radius: 6px; 
                    }
                    QPushButton:checked { 
                        background: #3b82f6; 
                        border: none;
                    }
                    QPushButton:hover { background: #3f4e64; }
                    QPushButton:checked:hover { background: #2563eb; }
                """)
                
                btn_container = QVBoxLayout()
                btn_container.addStretch()
                btn_container.addWidget(self.link_btn)
                btn_container.setContentsMargins(0, 0, 0, 0)
                btn_container.setSpacing(0)
                custom_row_layout.addLayout(btn_container)
                continue

            d = next((item for item in self.service._ui_definition if item["key"] == key), None)
            if not d: continue

            clean_label = label_map.get(key, str(d["label"]))
            widget = self._create_param_widget(d)
            
            if key in ["custom_width", "custom_height"]:
                row = VerticalParameterRow(clean_label, widget)
                custom_row_layout.addWidget(row)
                self.param_rows[key] = row
            else:
                row = VerticalParameterRow(clean_label, widget)
                self.param_card.rows_layout.addWidget(row)
                self.param_rows[key] = row
            
            if key == "custom_width":
                self.param_card.rows_layout.addWidget(custom_row_widget)

            if key == "mode": self.mode_combo = widget
            if key == "target_type": self.type_strip = widget
        
        self._update_ui_state()

    def _update_ui_state(self) -> None:
        """Toggles parameter visibility based on the selected Resize Mode."""
        mode = self.service.state.parameter_values.get("target_type", "Po2")
        
        # Visibility Rules
        # Visibility Rules
        self.param_rows["scale_factor"].setVisible(mode == "Ratio")
        self.custom_container.setVisible(mode == "Custom")
        self.param_rows["po2_size"].setVisible(mode == "Po2")
        self.param_rows["force_square"].setVisible(mode == "Po2")
        
        self._update_upscale_visibility()

    def _on_param_changed(self, key: str, value: Any) -> None:
        # ASPECT RATIO SYNC LOGIC
        if key in ["custom_width", "custom_height"] and self.service.state.preview_path:
            locked = self.service.state.parameter_values.get("aspect_locked", True)
            if locked:
                try:
                    with Image.open(self.service.state.preview_path) as img:
                        orig_w, orig_h = img.size
                        ratio = orig_w / orig_h
                        try:
                            val_int = int(value)
                            if val_int > 10000: # Security Limit
                                val_int = 10000
                                self.param_rows[key].field.setText(str(val_int))
                        except: return

                        if key == "custom_width":
                            new_h = str(max(1, min(10000, round(val_int / ratio))))
                            self.service.update_parameter("custom_height", new_h)
                            self.param_rows["custom_height"].field.blockSignals(True)
                            self.param_rows["custom_height"].field.setText(new_h)
                            self.param_rows["custom_height"].field.blockSignals(False)
                        else:
                            new_w = str(max(1, min(10000, round(val_int * ratio))))
                            self.service.update_parameter("custom_width", new_w)
                            self.param_rows["custom_width"].field.blockSignals(True)
                            self.param_rows["custom_width"].field.setText(new_w)
                            self.param_rows["custom_width"].field.blockSignals(False)
                except Exception as e:
                    print(f"Aspect sync error: {e}")

        self.service.update_parameter(key, value)
        self._update_ui_state()
        self._preview_timer.start()

    def _create_param_widget(self, d: dict) -> QWidget:
        key, kind, value = str(d["key"]), str(d.get("type", "string")), self.service.state.parameter_values.get(str(d["key"]), d.get("default"))
        if kind == "choice":
            if key == "target_type":
                w = ToggleButtonStrip(d.get("options", []), str(value))
                w.valueChanged.connect(lambda t, k=key: self._on_param_changed(k, t))
                return w
            w = QComboBox()
            w.setObjectName("compactField")
            w.addItems([str(o) for o in d.get("options", [])])
            w.setCurrentText(str(value))
            w.currentTextChanged.connect(lambda t, k=key: self._on_param_changed(k, t))
            return w
        if kind == "bool":
            w = QCheckBox("") 
            w.setChecked(bool(value))
            w.stateChanged.connect(lambda s, k=key: self._on_param_changed(k, bool(s)))
            return w
        w = QLineEdit(str(value))
        w.setObjectName("compactField")
        # Security: Size limit validator (1-10000)
        if key in ["custom_width", "custom_height", "po2_size"]:
            w.setValidator(QIntValidator(1, 10000))
        w.textChanged.connect(lambda t, k=key: self._on_param_changed(k, t))
        return w

    def _update_upscale_visibility(self):
        """Disables upscale mode if target size <= original size (only for relevant modes)."""
        if not hasattr(self, "mode_combo") or not self.service.state.preview_path:
            return
        
        try:
            params = self.service.state.parameter_values
            target_type = params.get("target_type", "Po2")
            
            with Image.open(self.service.state.preview_path) as img:
                orig_max = max(img.size)
            
            is_upscaling = True
            if target_type == "Ratio":
                is_upscaling = float(params.get("scale_factor", "1.0")) > 1.0
            elif target_type == "Po2":
                is_upscaling = int(params.get("po2_size", "1024")) > orig_max
            # Custom is always enabled for method choice as it's ambiguous
            
            self.mode_combo.setEnabled(is_upscaling)
            self.mode_combo.setToolTip("Only active when upscaling" if not is_upscaling else "")
        except:
            pass

    def _pick_inputs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images")
        if files:
            self.service.clear_inputs()
            self.service.add_inputs([files[-1]])
            self._refresh_assets()

    def _refresh_assets(self) -> None:
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        path = self.service.state.preview_path
        if not path:
            self.preview_view.set_pixmaps(QPixmap())
            self.meta_overlay.setText("-")
            return
        
        try:
            # 1. Load Original
            pm_orig = QPixmap(str(path))
            if pm_orig.isNull():
                 # Fallback to PIL if Qt fails
                 with Image.open(path) as img: pm_orig = self._pil_to_pixmap(img)
                 
            self.preview_view.set_pixmaps(pm_orig)
            self.preview_view.fit_image()
            
            # 2. Trigger processed preview (Debounced)
            self._preview_timer.start()
            
            w, h = pm_orig.width(), pm_orig.height()
            self.meta_overlay.setText(f"{w}x{h}")
            self.meta_overlay.adjustSize()
            
            self._update_upscale_visibility()
        except Exception as e:
            print(f"Preview error: {e}")

    def _refresh_preview_live(self) -> None:
        path = self.service.state.preview_path
        if not path: return
        
        try:
            # Generate Processed version at UI scale or reasonable size for performance
            params = self.service.state.parameter_values
            res_pil = self.service.get_processed_preview_pil(path, params)
            pm_res = self._pil_to_pixmap(res_pil)
            
            self.preview_view.set_pixmaps(self.preview_view.original_pixmap, pm_res)
            
            nw, nh = res_pil.size
            self.meta_overlay.setText(f"{self.preview_view.original_pixmap.width()}x{self.preview_view.original_pixmap.height()} → {nw}x{nh}")
            self.meta_overlay.adjustSize()
        except Exception as e:
             print(f"Live preview error: {e}")

    def _pil_to_pixmap(self, img: Image.Image) -> QPixmap:
        if img.mode == "RGB":
            fmt = QImage.Format_RGB888
        elif img.mode == "RGBA":
            fmt = QImage.Format_RGBA8888
        else:
            img = img.convert("RGBA")
            fmt = QImage.Format_RGBA8888
        
        qimg = QImage(img.tobytes(), img.width, img.height, fmt)
        return QPixmap.fromImage(qimg)

    def _run_workflow(self) -> None:
        self.export_card.set_running(True)
        self.export_card.set_status("Processing...")
        
        ok, msg, _ = self.service.run_workflow()
        
        self.export_card.set_running(False)
        self.export_card.set_status("Done" if ok else f"Error: {msg}")
        
        if ok:
             # Auto reveal or similar in slim mode?
             pass

    def _restore_window_state(self) -> None:
        geo = self._settings.value("geometry")
        if geo: self.restoreGeometry(geo)

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if files:
            self.service.add_inputs(files)
            self._refresh_assets()


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = ImageResizerWindow(ImageResizerService(), Path(__file__).resolve().parents[3] / APP_ID, targets)
    window.show()
    return app.exec()
