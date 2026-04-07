from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QPlainTextEdit, QVBoxLayout

from contexthub.ui.qt.shell import get_shell_metrics, set_surface_role


def build_result_inspector_card(title: str = "Result Inspector") -> dict[str, object]:
    m = get_shell_metrics()
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)

    body = QHBoxLayout()
    body.setSpacing(10)

    key_list = QListWidget()
    key_list.setMinimumWidth(180)
    set_surface_role(key_list.viewport(), "subtle")

    detail = QFrame()
    set_surface_role(detail, "subtle")
    detail_layout = QVBoxLayout(detail)
    inset = max(8, m.panel_padding - 4)
    detail_layout.setContentsMargins(inset, inset, inset, inset)
    detail_layout.setSpacing(8)

    summary_label = QLabel("Select a result field to inspect details.")
    summary_label.setObjectName("summaryText")
    summary_label.setWordWrap(True)

    detail_text = QPlainTextEdit()
    detail_text.setReadOnly(True)
    detail_text.setPlaceholderText("Inspector details")
    detail_text.setMinimumHeight(140)

    detail_layout.addWidget(summary_label)
    detail_layout.addWidget(detail_text, 1)

    body.addWidget(key_list, 0)
    body.addWidget(detail, 1)
    layout.addLayout(body)

    return {
        "card": card,
        "key_list": key_list,
        "summary_label": summary_label,
        "detail_text": detail_text,
        "detail": detail,
    }
