import os
import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QListWidget,
    QFrame,
)

from contexthub.ui.qt.shell import (
    HeaderSurface,
    get_shell_metrics,
    build_shell_stylesheet,
    qt_t,
    apply_app_icon,
    build_size_grip,
)
from contexthub.ui.qt.panels import (
    ExportRunPanel,
)

from .split_exr_state import SplitExrState
from .split_exr_service import SplitExrService

class SplitChannelWindow(QMainWindow):
    def __init__(self, app_root: Path, targets: list[str] = None):
        super().__init__()
        self.app_root = app_root
        self.state = SplitExrState()
        self.service = SplitExrService()
        
        self.setWindowTitle("Split Channel")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(800, 600)
        apply_app_icon(self, self.app_root)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)
        m = get_shell_metrics()
        self.root_layout.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)
        self.root_layout.setSpacing(m.section_gap)

        # Standard Window Shell
        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        self.main_layout = QVBoxLayout(self.window_shell)
        self.main_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        self.main_layout.setSpacing(m.section_gap)

        # Header
        self.header = HeaderSurface(
            self,
            title="Split Channel",
            subtitle="Automated extraction of all layers and channels from images",
            app_root=self.app_root
        )
        self.main_layout.addWidget(self.header)

        # Body: Automation Focused
        self.body_container = QWidget()
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        self.body_layout.setSpacing(m.section_gap)
        
        # File List Area
        self.list_frame = QFrame()
        self.list_frame.setObjectName("card")
        list_vbox = QVBoxLayout(self.list_frame)
        list_vbox.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        
        self.list_title = QLabel("Files to Process")
        self.list_title.setObjectName("sectionTitle")
        list_vbox.addWidget(self.list_title)
        
        from contexthub.ui.qt.shell import DropListWidget
        self.input_list = DropListWidget()
        self.input_list.setStyleSheet("background: transparent; border: none;")
        list_vbox.addWidget(self.input_list, 1)
        
        action_row = QHBoxLayout()
        self.add_btn = QPushButton("＋ Add Files")
        self.add_btn.setObjectName("pillBtn")
        self.clear_btn = QPushButton("✕ Clear")
        self.clear_btn.setObjectName("pillBtn")
        action_row.addWidget(self.add_btn)
        action_row.addWidget(self.clear_btn)
        list_vbox.addLayout(action_row)
        
        self.body_layout.addWidget(self.list_frame, 1)
        
        # Export & Process Panel
        self.export_panel = ExportRunPanel(title="Execution")
        self.body_layout.addWidget(self.export_panel)
        
        self.main_layout.addWidget(self.body_container, 1)
        
        # Shell Closing
        self.root_layout.addWidget(self.window_shell)
        self.main_layout.addWidget(build_size_grip(), 0, Qt.AlignRight)

        self.setStyleSheet(build_shell_stylesheet())
        self._bind_actions()
        
        if targets:
            self._add_files([Path(t) for t in targets])

    def _bind_actions(self):
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.input_list.files_dropped.connect(self._add_files)
        self.export_panel.run_requested.connect(self._on_run_clicked)

    def _on_add_clicked(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", "Images (*.exr *.hdr *.png *.jpg *.tiff *.tga)")
        if files:
            self._add_files([Path(f) for f in files])

    def _on_clear_clicked(self):
        self.state.files.clear()
        self.input_list.clear()
        self.header.set_asset_count(0)

    def _add_files(self, paths: list[Path]):
        for p in paths:
            if p not in self.state.files:
                self.state.files.append(p)
                self.input_list.addItem(p.name)
        self.header.set_asset_count(len(self.state.files))

    def _on_run_clicked(self):
        if not self.state.files: 
            self.export_panel.set_status("Error: No files to process")
            return
        
        self.export_panel.set_progress(0)
        self.export_panel.set_status("Analyzing and Splitting all channels...")
        
        def on_progress(p, status):
            self.export_panel.set_progress(int(p * 100))
            self.export_panel.set_status(status)
            
        def on_complete(success, errors):
            self.export_panel.set_progress(100)
            status = f"Completed: {success} files split into layers."
            if errors: status += f" ({len(errors)} errors)"
            self.export_panel.set_status(status)
            
        # Strategy: Analyze each file and split ALL detected layers
        self.service.run_automation_split(
            self.state.files,
            "PNG", # Default format
            on_progress,
            on_complete
        )

def main():
    app = QApplication(sys.argv)
    app_root = Path(os.environ.get("CTX_APP_ROOT", "."))
    window = SplitChannelWindow(app_root, sys.argv[1:])
    window.show()
    sys.exit(app.exec())
