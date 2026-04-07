from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics


def build_model_selector_card(title: str = "Model") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(8)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    combo = QComboBox()
    status = QLabel("Model status")
    status.setObjectName("summaryText")
    layout.addWidget(title_label)
    layout.addWidget(combo)
    layout.addWidget(status)
    return {"card": card, "combo": combo, "status": status}
