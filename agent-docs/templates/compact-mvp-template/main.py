import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime_bootstrap import resolve_shared_runtime
from contexthub.utils.startup_errors import format_startup_error

SHARED_ROOT, SHARED_PACKAGE_ROOT = resolve_shared_runtime(APP_ROOT)
for path in (SHARED_ROOT, SHARED_PACKAGE_ROOT):
    if path.exists():
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

try:
    from PySide6.QtWidgets import QApplication
    from contexthub.ui.qt.shell import HeaderSurface, attach_size_grip
    from contexthub.ui.qt.layout import CompactAppShell

    from .service import __APP_CLASS_NAME__Service
    from .control_panel import __APP_CLASS_NAME__ControlPanel
    from .preview_panel import __APP_CLASS_NAME__PreviewPanel
except Exception as exc:
    raise SystemExit(format_startup_error(exc)) from exc

class __APP_CLASS_NAME__App(CompactAppShell):
    def __init__(self, service: __APP_CLASS_NAME__Service):
        super().__init__(title="__APP_NAME__")
        self.service = service
        self._build_components()
        attach_size_grip(self)

    def _build_components(self):
        # 1. Preview Panel (Top)
        self.preview_panel = __APP_CLASS_NAME__PreviewPanel(self.service)
        self.add_body_widget(self.preview_panel)

        # 2. Control Panel (Bottom)
        self.control_panel = __APP_CLASS_NAME__ControlPanel(self.service)
        self.control_panel.request_run.connect(self._run_main_workflow)
        self.control_panel.request_live_preview.connect(self.preview_panel.refresh_live)
        self.add_body_widget(self.control_panel)

    def _run_main_workflow(self):
        self.control_panel.set_running(True)
        success, msg, out_path = self.service.run_workflow()
        self.control_panel.set_running(False)
        self.show_status(msg, success)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
        self.service.add_inputs([str(p) for p in paths])
        self.preview_panel.refresh()

def main():
    app = QApplication(sys.argv)
    service = __APP_CLASS_NAME__Service()
    
    # Process initial arguments
    if len(sys.argv) > 1:
        service.add_inputs(sys.argv[1:])
    
    win = __APP_CLASS_NAME__App(service)
    win.show()
    
    # Handle initial preview refresh if files were passed
    if service.state.input_assets:
        win.preview_panel.refresh()
        
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
