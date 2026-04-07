from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics


def build_preset_selector_card(title: str = "Preset") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(8)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    description_label = QLabel("Preset description")
    description_label.setObjectName("summaryText")
    combo = QComboBox()
    layout.addWidget(title_label)
    layout.addWidget(description_label)
    layout.addWidget(combo)
    return {"card": card, "title_label": title_label, "description_label": description_label, "combo": combo}
