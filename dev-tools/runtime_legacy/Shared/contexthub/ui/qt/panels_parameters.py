from __future__ import annotations

from .theme_metrics import get_shell_metrics
from .theme_style_helpers import set_surface_role, set_transparent_surface

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QSlider,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt panel runtime.") from exc


class ParameterControlsPanel(QFrame):
    def __init__(self, title: str = "Parameters"):
        super().__init__()
        self.setObjectName("card")
        m = get_shell_metrics()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        layout.addWidget(self.title_label)

        profile_row = QHBoxLayout()
        profile_row.setSpacing(8)
        profile_row.addWidget(QLabel("Profile"))
        self.profile_combo = QComboBox()
        profile_row.addWidget(self.profile_combo, 1)
        layout.addLayout(profile_row)

        scale_row = QHBoxLayout()
        scale_row.setSpacing(8)
        scale_row.addWidget(QLabel("Scale"))
        self.scale_combo = QComboBox()
        scale_row.addWidget(self.scale_combo, 1)
        layout.addLayout(scale_row)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)
        slider_row.addWidget(QLabel("Strength"), 0)
        self.slider = QSlider(Qt.Horizontal)
        slider_row.addWidget(self.slider, 1)
        self.slider_value = QLabel("0")
        slider_row.addWidget(self.slider_value, 0)
        layout.addLayout(slider_row)

        self.smart_toggle = QCheckBox("Use smart defaults")
        layout.addWidget(self.smart_toggle)


class PresetParameterPanel(QFrame):
    def __init__(self, title: str = "Settings"):
        super().__init__()
        self.setObjectName("card")
        m = get_shell_metrics()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        self.description_label = QLabel("Preset and core parameters live in one card.")
        self.description_label.setObjectName("summaryText")
        self.description_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label)

        self.preset_shell = QFrame()
        set_surface_role(self.preset_shell, "subtle")
        preset_layout = QVBoxLayout(self.preset_shell)
        preset_layout.setContentsMargins(10, 10, 10, 10)
        preset_layout.setSpacing(8)
        self.preset_label = QLabel("Preset")
        self.preset_label.setObjectName("summaryText")
        self.preset_combo = QComboBox()
        preset_layout.addWidget(self.preset_label)
        preset_layout.addWidget(self.preset_combo)
        layout.addWidget(self.preset_shell)

        self.parameter_label = QLabel("Parameters")
        self.parameter_label.setObjectName("summaryText")
        layout.addWidget(self.parameter_label)

        self.parameter_panel = ParameterControlsPanel()
        set_transparent_surface(self.parameter_panel)
        self.parameter_panel.title_label.hide()
        layout.addWidget(self.parameter_panel)

        self.profile_combo = self.parameter_panel.profile_combo
        self.scale_combo = self.parameter_panel.scale_combo
        self.slider = self.parameter_panel.slider
        self.slider_value = self.parameter_panel.slider_value
        self.smart_toggle = self.parameter_panel.smart_toggle


class FixedParameterPanel(QFrame):
    def __init__(self, title: str, description: str = "", preset_label: str = "Preset"):
        super().__init__()
        self.setObjectName("card")
        m = get_shell_metrics()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        self.description_label = QLabel(description)
        self.description_label.setObjectName("summaryText")
        self.description_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label)

        preset_row = QHBoxLayout()
        self.preset_label = QLabel(preset_label)
        self.preset_combo = QComboBox()
        preset_row.addWidget(self.preset_label)
        preset_row.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_row)

        self.fields_container = QWidget()
        set_transparent_surface(self.fields_container)
        self.fields_layout = QVBoxLayout(self.fields_container)
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        self.fields_layout.setSpacing(8)
        layout.addWidget(self.fields_container, 1)
        self.form_body = self.fields_layout

    def clear_fields(self) -> None:
        while self.fields_layout.count():
            item = self.fields_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_field(self, label: str, widget: QWidget) -> None:
        row = QWidget()
        set_transparent_surface(row)
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)
        title = QLabel(label)
        title.setObjectName("eyebrow")
        row_layout.addWidget(title)
        row_layout.addWidget(widget)
        self.fields_layout.addWidget(row)
