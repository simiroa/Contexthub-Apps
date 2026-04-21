from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal
from contexthub.ui.qt.widgets import ParameterForm, StandardExecutionFooter

class __APP_CLASS_NAME__ControlPanel(QWidget):
    request_run = Signal()
    request_live_preview = Signal()

    def __init__(self, service):
        super().__init__()
        self.service = service
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 1. Parameter Form
        self.form = ParameterForm(self.service.get_ui_definition())
        self.form.value_changed.connect(self._on_param_changed)
        layout.addWidget(self.form)

        layout.addStretch()

        # 2. Execution Footer
        self.footer = StandardExecutionFooter("Run Process")
        self.footer.clicked.connect(self.request_run.emit)
        self.footer.reveal_clicked.connect(self.service.reveal_output_dir)
        layout.addWidget(self.footer)

    def _on_param_changed(self, key, value):
        self.service.update_parameter(key, value)
        self.request_live_preview.emit()

    def set_running(self, running: bool):
        self.footer.set_running(running)
