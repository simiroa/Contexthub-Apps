from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics


def build_output_options_card(title: str = "Output Options") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    format_row = QHBoxLayout()
    format_row.addWidget(QLabel("Format"))
    format_combo = QComboBox()
    format_row.addWidget(format_combo, 1)
    layout.addLayout(format_row)

    name_row = QHBoxLayout()
    name_row.addWidget(QLabel("Prefix"))
    prefix_edit = QLineEdit()
    name_row.addWidget(prefix_edit, 1)
    layout.addLayout(name_row)

    open_folder = QCheckBox("Open folder when done")
    layout.addWidget(open_folder)

    return {
        "card": card,
        "format_combo": format_combo,
        "prefix_edit": prefix_edit,
        "open_folder": open_folder,
    }
