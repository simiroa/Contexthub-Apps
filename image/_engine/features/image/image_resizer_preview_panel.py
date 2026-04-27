from PySide6.QtCore import QTimer, Qt, QThreadPool
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PIL import Image

from contexthub.ui.qt.shell import get_shell_palette, set_surface_role
from features.image.comparison_preview_widget import ComparisonPreviewWidget
from features.image.image_resizer_workers import ProcessLivePreviewWorker

class ImageResizerPreviewPanel(QWidget):
    def __init__(self, service, thread_pool=None):
        super().__init__()
        self.service = service
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self._build_ui()
        
        # Debounce timer for processing real-time feedback
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(250)
        self._preview_timer.timeout.connect(self._refresh_preview_live)
        
    def _build_ui(self):
        p = get_shell_palette()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_view = ComparisonPreviewWidget()
        self.preview_view.setMinimumHeight(240)
        layout.addWidget(self.preview_view)
        
        self.meta_overlay = QLabel("-", self.preview_view)
        self.meta_overlay.setObjectName("summaryText")
        set_surface_role(self.meta_overlay, "panel")
        self.meta_overlay.setStyleSheet(
            f"padding: 2px 6px; border-radius: 4px; color: {p.text};"
        )
        self.meta_overlay.move(10, 10)
        
    def refresh(self):
        """Called when a new image is loaded (e.g. drop)"""
        path = self.service.state.preview_path
        if not path:
            self.preview_view.set_pixmaps(QPixmap())
            self.meta_overlay.setText("-")
            return
            
        try:
            # Always use PIL for initial load to handle high-res safely and check metadata
            with Image.open(path) as img:
                orig_w, orig_h = img.size
                # Create a thumbnail for display to keep memory usage low
                display_img = img.copy()
                display_img.thumbnail((1200, 1200), Image.Resampling.BILINEAR)
                pm_orig = self._pil_to_pixmap(display_img)
                 
            self.preview_view.set_pixmaps(pm_orig)
            self.preview_view.fit_image()
            
            self.meta_overlay.setText(f"{orig_w}x{orig_h}")
            self.meta_overlay.adjustSize()
            
            # Start live preview processing immediately
            self.refresh_live()
        except Exception as e:
            print(f"Preview error: {e}")
            self.meta_overlay.setText(f"Error: {str(e)[:20]}...")
            
    def refresh_live(self):
        """Called by control panel when params changed"""
        self._preview_timer.start()
        
    def _refresh_preview_live(self):
        path = self.service.state.preview_path
        if not path: return
        
        try:
            params = self.service.state.parameter_values
            worker = ProcessLivePreviewWorker(self.service, path, params)
            worker.signals.result.connect(self._on_live_preview_ready)
            self.thread_pool.start(worker)
        except Exception as e:
            print(f"Live preview dispatch error: {e}")
            
    def _on_live_preview_ready(self, res_pil: Image.Image, meta_added: str):
        try:
            # Scale down the result image for preview display if it's too large
            display_res = res_pil.copy()
            display_res.thumbnail((1200, 1200), Image.Resampling.BILINEAR)
            
            pm_res = self._pil_to_pixmap(display_res)
            self.preview_view.set_pixmaps(self.preview_view.original_pixmap, pm_res)
            
            orig_meta = self.meta_overlay.text().split(" ")[0] # Keep the original WxH
            self.meta_overlay.setText(f"{orig_meta} {meta_added}")
            self.meta_overlay.adjustSize()
        except Exception as e:
            print(f"Error handling live preview result: {e}")
            
    def _pil_to_pixmap(self, img: Image.Image) -> QPixmap:
        if img.mode == "RGB":
            fmt = QImage.Format_RGB888
        elif img.mode == "RGBA":
            fmt = QImage.Format_RGBA8888
        else:
            img = img.convert("RGBA")
            fmt = QImage.Format_RGBA8888
        
        # Ensure we have a contiguous buffer for QImage
        data = img.tobytes("raw", img.mode)
        qimg = QImage(data, img.width, img.height, img.width * (4 if "A" in img.mode else 3), fmt)
        # We must copy current data because QImage doesn't own the 'data' buffer
        return QPixmap.fromImage(qimg.copy())
