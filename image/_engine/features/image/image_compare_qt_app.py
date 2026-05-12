import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QListWidget,
    QFrame,
    QAbstractItemView,
)

from contexthub.ui.qt.shell import (
    HeaderSurface,
    get_shell_metrics,
    build_shell_stylesheet,
    apply_app_icon,
    attach_size_grip,
)
from shared._engine.components.icon_button import build_icon_button

try:
    # Try relative imports first (when run as part of package)
    from .image_compare_state import ImageCompareState
    from .image_compare_service import ImageCompareService
    from .advanced_compare_widget import AdvancedCompareWidget
except ImportError:
    # Fall back to absolute imports (when run as standalone script)
    from features.image.image_compare_state import ImageCompareState
    from features.image.image_compare_service import ImageCompareService
    from features.image.advanced_compare_widget import AdvancedCompareWidget

from shared._engine.runtime.file_input_mixin import MultiFileInputMixin

APP_ID = "image_compare"

class ImageCompareWindow(QMainWindow, MultiFileInputMixin):
    def __init__(self, app_root: Path, targets: list[str] = None):
        super().__init__()
        self.app_root = app_root
        self.state = ImageCompareState()
        self.service = ImageCompareService()

        self.setWindowTitle("Image Compare")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1200, 850)
        apply_app_icon(self, self.app_root)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)
        m = get_shell_metrics()
        self.root_layout.setContentsMargins(0, 0, 0, 0)
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
            title="Image Compare",
            subtitle="Compare two images with split-slider, side-by-side, or difference views",
            app_root=self.app_root
        )
        self.header.set_header_visibility(
            show_subtitle=False,
            show_asset_count=False,
            show_runtime_status=False,
        )
        self.main_layout.addWidget(self.header)

        self.body_container = QFrame()
        self.body_container.setObjectName("card")
        self.body_layout = QHBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        self.body_layout.setSpacing(m.section_gap)

        self.left_panel = QFrame()
        self.left_panel.setObjectName("subtlePanel")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        left_layout.setSpacing(8)

        left_title = QLabel("Inputs")
        left_title.setObjectName("sectionTitle")
        left_layout.addWidget(left_title)

        actions_row = QHBoxLayout()
        self.add_btn = build_icon_button("Add", icon_name="plus", role="secondary")
        self.clear_btn = build_icon_button("Clear", icon_name="trash-2", role="ghost")
        actions_row.addWidget(self.add_btn)
        actions_row.addWidget(self.clear_btn)
        actions_row.addStretch(1)
        left_layout.addLayout(actions_row)

        self.input_list = QListWidget()
        self.input_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        left_layout.addWidget(self.input_list, 1)

        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("subtlePanel")
        preview_vbox = QVBoxLayout(self.preview_frame)
        preview_vbox.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        preview_vbox.setSpacing(8)

        tools_row = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Split", "Grid", "Difference", "Selection (Single)"])
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.setFixedWidth(180)
        tools_row.addWidget(self.mode_combo)
        tools_row.addStretch(1)

        self.metrics_label = QLabel("Select files to compare")
        self.metrics_label.setObjectName("summaryText")
        tools_row.addWidget(self.metrics_label)
        preview_vbox.addLayout(tools_row)

        self.comp_preview = AdvancedCompareWidget()
        preview_vbox.addWidget(self.comp_preview, 1)

        self.body_layout.addWidget(self.left_panel, 1)
        self.body_layout.addWidget(self.preview_frame, 3) 

        self.main_layout.addWidget(self.body_container, 1)
        
        # Shell Closing
        self.size_grip = attach_size_grip(self.main_layout, self.window_shell)
        self.root_layout.addWidget(self.window_shell)

        self.setStyleSheet(build_shell_stylesheet())
        self.setup_file_inputs(self.add_btn, self.clear_btn, self.input_list, self.state)
        self._bind_actions()
        
        if targets:
            self._add_files([Path(t) for t in targets])

    def get_file_filters(self):
        return "Images (*.png *.jpg *.exr *.hdr *.tga *.tiff)"

    def load_thumbnail(self, path):
        """Returns a PIL Image for thumbnail — called on worker thread, must NOT create QPixmap."""
        pil_img = self.service.get_pil_image(str(path), "RGB")
        if pil_img:
            thumb = pil_img.copy()
            thumb.thumbnail((200, 200))
            return thumb
        return None

    def on_files_added(self, paths):
        count = self.input_list.count()
        if count >= 2:
            self.input_list.item(0).setSelected(True)
            self.input_list.item(1).setSelected(True)
        elif count == 1:
            self.input_list.item(0).setSelected(True)
        self._on_selection_changed()

    def on_files_cleared(self):
        self.comp_preview.set_pixmap_list([])
        self.metrics_label.setText("Select two files to compare")

    def _bind_actions(self):
        self.input_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

    def _on_selection_changed(self):
        selected = self.input_list.selectedItems()
        mode_idx = self.mode_combo.currentIndex()
        mode_text = self.mode_combo.currentText()
        
        if mode_text == "Selection (Single)":
            if selected:
                idx = self.input_list.row(selected[-1])
                self._refresh_single_view(idx)
            else:
                self.metrics_label.setText("Select an image")
                self.comp_preview.set_pixmap_list([])
        elif mode_text == "Grid":
            if selected:
                pixmaps = []
                for item in selected:
                    idx = self.input_list.row(item)
                    path = str(self.state.files[idx])
                    pil_img = self.service.get_pil_image(path, "RGB")
                    if pil_img:
                        pixmaps.append(self._pil_to_pixmap(pil_img))
                self.comp_preview.set_pixmap_list(pixmaps)
                self.metrics_label.setText(f"Grid: {len(pixmaps)} images")
            else:
                self.metrics_label.setText("Select images for Grid view")
                self.comp_preview.set_pixmap_list([])
        elif len(selected) >= 2:
            idx_a = self.input_list.row(selected[0])
            idx_b = self.input_list.row(selected[1])
            self._refresh_comparison(idx_a, idx_b)
        else:
            self.metrics_label.setText("Select two files to compare")
            self.comp_preview.set_pixmap_list([])

    def _on_mode_changed(self, index):
        mode_map = {0: "split", 1: "grid", 2: "diff", 3: "single"}
        self.state.mode = mode_map.get(index, "split")
        self.comp_preview.set_mode(self.state.mode)
        self._on_selection_changed()

    def _refresh_single_view(self, idx):
        path = str(self.state.files[idx])
        pil_img = self.service.get_pil_image(path, "RGB")
        if pil_img:
            pm = self._pil_to_pixmap(pil_img)
            self.comp_preview.set_pixmap_list([pm])
            self.metrics_label.setText(f"Selection: {Path(path).name} ({pil_img.width}x{pil_img.height})")

    def _refresh_comparison(self, idx_a, idx_b):
        path_a = str(self.state.files[idx_a])
        path_b = str(self.state.files[idx_b])
        
        pil_a = self.service.get_pil_image(path_a, "RGB")
        pil_b = self.service.get_pil_image(path_b, "RGB")
        
        if pil_a and pil_b:
            pm_a = self._pil_to_pixmap(pil_a)
            pm_b = self._pil_to_pixmap(pil_b)
            pixmaps = [pm_a, pm_b]

            if self.state.mode == "diff":
                diff_pil = self.service.get_diff_visualization(path_a, path_b, "RGB")
                if diff_pil:
                    pixmaps.append(self._pil_to_pixmap(diff_pil))

            self.comp_preview.set_pixmap_list(pixmaps)

            try:
                ssim, diff = self.service.compute_metrics(path_a, path_b, "RGB")
                self.metrics_label.setText(f"SSIM: {ssim:.4f} | Diff: {diff:,}px")
            except Exception as e:
                self.metrics_label.setText(f"Metric Error: {e}")
        else:
            self.metrics_label.setText("Loading Error")

    def _pil_to_pixmap(self, pil_img):
        img = pil_img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimg = QImage(data, img.size[0], img.size[1], QImage.Format_RGBA8888).copy()
        return QPixmap.fromImage(qimg)

def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    
    from shared._engine.runtime.single_instance import SingleInstance
    si = SingleInstance(APP_ID)
    if si.is_already_running():
        if targets: si.send_to_primary(targets)
        return 0
        
    app_root = Path(__file__).resolve().parents[3] / APP_ID
    window = ImageCompareWindow(app_root, targets)
    
    si.start_server()
    si.message_received.connect(window.handle_external_targets)
    window._si = si
    
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(start_app(sys.argv[1:]))
