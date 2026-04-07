from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_surface_role


def build_preset_parameter_card(title: str = "Settings") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    description_label = QLabel("Preset and core parameters live in one card.")
    description_label.setObjectName("summaryText")
    description_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(description_label)

    preset_shell = QFrame()
    set_surface_role(preset_shell, "subtle")
    preset_layout = QVBoxLayout(preset_shell)
    preset_layout.setContentsMargins(10, 10, 10, 10)
    preset_layout.setSpacing(8)
    preset_meta = QLabel("Preset")
    preset_meta.setObjectName("summaryText")
    preset_combo = QComboBox()
    preset_layout.addWidget(preset_meta)
    preset_layout.addWidget(preset_combo)
    layout.addWidget(preset_shell)

    parameter_title = QLabel("Parameters")
    parameter_title.setObjectName("summaryText")
    layout.addWidget(parameter_title)

    profile_row = QHBoxLayout()
    profile_row.setSpacing(8)
    profile_row.addWidget(QLabel("Profile"))
    profile_combo = QComboBox()
    profile_row.addWidget(profile_combo, 1)
    layout.addLayout(profile_row)

    scale_row = QHBoxLayout()
    scale_row.setSpacing(8)
    scale_row.addWidget(QLabel("Scale"))
    scale_combo = QComboBox()
    scale_row.addWidget(scale_combo, 1)
    layout.addLayout(scale_row)

    slider_row = QHBoxLayout()
    slider_row.setSpacing(8)
    slider_label = QLabel("Strength")
    slider_value = QLabel("0")
    slider = QSlider(Qt.Horizontal)
    slider_row.addWidget(slider_label, 0)
    slider_row.addWidget(slider, 1)
    slider_row.addWidget(slider_value, 0)
    layout.addLayout(slider_row)

    smart_toggle = QCheckBox("Use smart defaults")
    layout.addWidget(smart_toggle)

    return {
        "card": card,
        "title_label": title_label,
        "description_label": description_label,
        "preset_shell": preset_shell,
        "preset_meta": preset_meta,
        "parameter_title": parameter_title,
        "preset_combo": preset_combo,
        "profile_combo": profile_combo,
        "scale_combo": scale_combo,
        "slider": slider,
        "slider_value": slider_value,
        "smart_toggle": smart_toggle,
    }
