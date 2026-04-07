from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QMenu, QWidgetAction, 
    QFrame, QTextEdit, QLabel, QComboBox
)
from shared._engine.components.icon_utils import get_icon
from shared._engine.components.icon_button import build_icon_button
from ai_text_lab_constants import POPUP_STYLE, SLIDER_STYLE

class OpacityPopup(QWidget):
    """Premium styled popup slider for window transparency. 
    Appears above the target widget."""
    valueChanged = Signal(int)

    def __init__(self, parent=None, initial_value=100):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.container = QWidget(self)
        self.container.setObjectName("OpacityPopup")
        self.container.setStyleSheet(POPUP_STYLE)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(12, 10, 12, 10)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(20, 100)
        self.slider.setValue(initial_value)
        self.slider.setFixedWidth(140)
        self.slider.setStyleSheet(SLIDER_STYLE)
        self.slider.valueChanged.connect(self.valueChanged.emit)
        
        layout.addWidget(self.slider)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)
        self.adjustSize()

    def show_above(self, widget: QWidget):
        """Show the popup centered above the given widget."""
        point = widget.mapToGlobal(widget.rect().topLeft())
        x = point.x() + (widget.width() - self.width()) // 2
        y = point.y() - self.height() - 8
        self.move(x, y)
        self.show()

class EditorPanel(QFrame):
    """Unified container for Input or Output text areas."""
    def __init__(self, title: str, is_readonly: bool = False, placeholder: str = ""):
        super().__init__()
        self.setObjectName("glassCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.editor = QTextEdit()
        self.editor.setObjectName("inputArea" if not is_readonly else "outputArea")
        self.editor.setPlaceholderText(placeholder)
        self.editor.setReadOnly(is_readonly)
        self.editor.setAcceptDrops(False)
        
        layout.addWidget(self.editor)

class PillActionsBar(QHBoxLayout):
    """Horizontal bar for contextual actions like Copy and Refine."""
    def __init__(self):
        super().__init__()
        self.setContentsMargins(8, 0, 8, 8)
        
        self.auto_run_btn = build_icon_button("Auto", icon_name="refresh-cw", role="ghost")
        self.auto_run_btn.setCheckable(True)
        self.auto_run_btn.setFixedHeight(24)
        
        self.refine_btn = build_icon_button("Use as Input", icon_name="chevron-up", role="ghost")
        self.refine_btn.setFixedHeight(24)
        
        self.copy_btn = build_icon_button("Copy", icon_name="check", role="ghost")
        self.copy_btn.setFixedHeight(24)
        
        self.addWidget(self.auto_run_btn)
        self.addStretch()
        self.addWidget(self.refine_btn)
        self.addWidget(self.copy_btn)
