from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics
from shared._engine.components.icon_button import build_icon_button


def build_execution_card(title: str = "Run") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    output_row = QHBoxLayout()
    output_label = QLabel("Output")
    output_label.setObjectName("summaryText")
    output_edit = QLineEdit()
    open_btn = build_icon_button("Open Folder", icon_name="folder-open", role="secondary")
    output_row.addWidget(output_label)
    output_row.addWidget(output_edit, 1)
    output_row.addWidget(open_btn)
    layout.addLayout(output_row)

    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(0)
    layout.addWidget(progress)

    footer = QHBoxLayout()
    status = QLabel("Ready")
    status.setObjectName("summaryText")
    run_btn = build_icon_button(title, icon_name="play-circle", role="primary")
    footer.addWidget(status, 1)
    footer.addWidget(run_btn, 0)
    layout.addLayout(footer)

    return {
        "card": card,
        "output_edit": output_edit,
        "open_btn": open_btn,
        "progress": progress,
        "status": status,
        "run_btn": run_btn,
    }
