from typing import Any
from PIL import Image

from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QComboBox,
    QLineEdit
)

from shared._engine.components.parameter_controls_card import ParameterCard
from shared._engine.components.mini_execute_card import MiniExecuteCard
from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.toggle_button_strip import ToggleButtonStrip
from shared._engine.components.vertical_parameter_row import VerticalParameterRow

class ImageResizerControlPanel(QWidget):
    request_live_preview = Signal()
    request_save = Signal()

    def __init__(self, service):
        super().__init__()
        self.service = service
        self.param_rows = {}
        self._build_ui()
        self._bind_actions()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Parameters
        self.param_card = ParameterCard("Optimization Settings")
        self.param_card.layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.param_card)
        
        # Execution
        self.export_card = MiniExecuteCard("Save")
        self.export_card.layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.export_card)

    def _bind_actions(self):
        self.export_card.run_clicked.connect(self.request_save.emit)

    def refresh(self):
        self._refresh_parameter_form()

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
                
                row = VerticalParameterRow(" ", self.link_btn)
                custom_row_layout.addWidget(row)
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
        self.param_rows["scale_factor"].setVisible(mode == "Ratio")
        self.custom_container.setVisible(mode == "Custom")
        self.param_rows["po2_size"].setVisible(mode == "Po2")
        self.param_rows["force_square"].setVisible(mode == "Po2")
        
        self._update_upscale_visibility()

    def _calculate_locked_aspect(self, source_axis: str, source_val: int) -> int:
        """Pure function to calculate the reciprocal aspect dimension."""
        if not self.service.state.preview_path:
            return source_val
        try:
            with Image.open(self.service.state.preview_path) as img:
                orig_w, orig_h = img.size
        except: return source_val
        
        ratio = orig_w / orig_h
        clamped_val = max(1, min(10000, source_val))
        
        if source_axis == "custom_width":
            return max(1, min(10000, round(clamped_val / ratio)))
        else:
            return max(1, min(10000, round(clamped_val * ratio)))

    def _render_state(self) -> None:
        """Uni-directional data flow from state -> UI"""
        params = self.service.state.parameter_values
        for key in ["custom_width", "custom_height"]:
            if key in self.param_rows:
                field = self.param_rows[key].field
                val_str = str(params.get(key, ""))
                if field.text() != val_str:
                    field.setText(val_str)

    def _on_param_changed(self, key: str, value: Any) -> None:
        # Immediate state update
        if key in ["custom_width", "custom_height"]:
            try:
                val_int = min(10000, max(1, int(value)))
                self.service.update_parameter(key, str(val_int))
                
                if self.service.state.parameter_values.get("aspect_locked", True):
                    reciprocal_key = "custom_height" if key == "custom_width" else "custom_width"
                    reciprocal_val = self._calculate_locked_aspect(key, val_int)
                    self.service.update_parameter(reciprocal_key, str(reciprocal_val))
            except ValueError:
                pass # typing incomplete numbers etc
        else:
            self.service.update_parameter(key, value)
            
        self._render_state()
        self._update_ui_state()
        self.request_live_preview.emit()

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
        w.textEdited.connect(lambda t, k=key: self._on_param_changed(k, t))
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

    def update_run_status(self, is_running: bool, status_text: str):
        self.export_card.set_running(is_running)
        self.export_card.set_status(status_text)
