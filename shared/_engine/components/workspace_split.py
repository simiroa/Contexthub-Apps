from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget


def build_workspace_split(left: QWidget, right: QWidget, *, sizes: tuple[int, int] = (700, 500)) -> QSplitter:
    splitter = QSplitter(Qt.Horizontal)
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(8)
    splitter.addWidget(left)
    splitter.addWidget(right)
    splitter.setSizes(list(sizes))
    return splitter
