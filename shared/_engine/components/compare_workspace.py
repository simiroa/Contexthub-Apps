from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSplitter, QVBoxLayout, QWidget

from contexthub.ui.qt.shell import set_surface_role


def build_compare_workspace(left_title: str = "Left", right_title: str = "Right") -> dict[str, object]:
    splitter = QSplitter(Qt.Horizontal)
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(8)

    left = QWidget()
    set_surface_role(left, "content")
    left_layout = QVBoxLayout(left)
    left_layout.addWidget(QLabel(left_title))

    right = QWidget()
    set_surface_role(right, "content")
    right_layout = QVBoxLayout(right)
    right_layout.addWidget(QLabel(right_title))

    splitter.addWidget(left)
    splitter.addWidget(right)
    splitter.setSizes([1, 1])
    return {"splitter": splitter, "left": left, "right": right}
