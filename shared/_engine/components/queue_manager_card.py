from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from contexthub.ui.qt.shell import get_shell_metrics, set_surface_role
from shared._engine.components.icon_button import build_icon_button

from .queue_card import build_queue_card


def build_queue_manager_card(title: str = "Queue") -> dict[str, object]:
    m = get_shell_metrics()
    section = build_queue_card(title=title, compact=False)
    card = section["card"]
    layout = card.layout()

    toolbar = QHBoxLayout()
    toolbar.setSpacing(8)

    pause_btn = build_icon_button("Pause", icon_name="pause", role="secondary")
    retry_btn = build_icon_button("Retry Failed", icon_name="refresh-cw", role="secondary")
    remove_btn = build_icon_button("Remove Selected", icon_name="trash-2", role="ghost")

    toolbar.addWidget(pause_btn)
    toolbar.addWidget(retry_btn)
    toolbar.addWidget(remove_btn)
    toolbar.addStretch(1)
    layout.insertLayout(1, toolbar)

    summary = QFrame()
    set_surface_role(summary, "subtle")
    summary_layout = QHBoxLayout(summary)
    inset = max(8, m.panel_padding - 4)
    summary_layout.setContentsMargins(inset, inset, inset, inset)
    summary_layout.setSpacing(12)

    active_label = QLabel("Active: 0")
    active_label.setObjectName("summaryText")
    failed_label = QLabel("Failed: 0")
    failed_label.setObjectName("summaryText")
    completed_label = QLabel("Done: 0")
    completed_label.setObjectName("summaryText")

    summary_layout.addWidget(active_label)
    summary_layout.addWidget(failed_label)
    summary_layout.addWidget(completed_label)
    summary_layout.addStretch(1)
    layout.insertWidget(2, summary)

    return {
        **section,
        "pause_btn": pause_btn,
        "retry_btn": retry_btn,
        "remove_btn": remove_btn,
        "summary": summary,
        "active_label": active_label,
        "failed_label": failed_label,
        "completed_label": completed_label,
    }
