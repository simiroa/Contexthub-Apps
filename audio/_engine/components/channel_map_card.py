from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QLabel, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics


def build_channel_map_card(title: str = "Channel Mapping") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    grid = QGridLayout()
    combos = {}
    for row, channel in enumerate(("R", "G", "B", "A")):
        grid.addWidget(QLabel(channel), row, 0)
        combo = QComboBox()
        grid.addWidget(combo, row, 1)
        combos[channel] = combo
    layout.addLayout(grid)
    return {"card": card, "combos": combos}
