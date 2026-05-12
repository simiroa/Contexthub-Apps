from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QListWidgetItem
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap, QImage

from .thumbnail_service import request_thumbnail

class MultiFileInputMixin:
    """
    Mixin for QMainWindow or QWidget to handle multi-file input UI patterns.

    Subclasses should define:
    - self.state.files (list to store Paths)
    - self.load_thumbnail(path): Returns a PIL.Image (or None) for the thumbnail.
                                 Called on a worker thread — do NOT create QPixmap here.

    Optional Hooks:
    - self.get_file_filters(): returns string for QFileDialog filter
    - self.on_files_added(paths): called when new files are added
    - self.on_files_cleared(): called when files are cleared
    """
    
    def setup_file_inputs(self, add_btn, clear_btn, input_list, state, file_attr="files"):
        self.add_btn = add_btn
        self.clear_btn = clear_btn
        self.input_list = input_list
        self.state = state
        self._file_attr = file_attr
        
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        
        self.input_list.setIconSize(QSize(100, 100))
        self.input_list.setSpacing(4)
        
    def _on_add_clicked(self):
        filters = self.get_file_filters() if hasattr(self, 'get_file_filters') else "All Files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", filters)
        if files:
            self._add_files([Path(f) for f in files])
            
    def _on_clear_clicked(self):
        self.state.files.clear()
        self.input_list.clear()
        if hasattr(self, 'on_files_cleared'):
            self.on_files_cleared()
            
    def _add_files(self, paths):
        new_paths = []
        for p in paths:
            if p not in self.state.files:
                self.state.files.append(p)
                new_paths.append(p)
                item = QListWidgetItem(p.name)
                item.setToolTip(str(p))
                self.input_list.addItem(item)
                
        # Start thumbnail generation
        for p in new_paths:
            load_func = getattr(self, 'load_thumbnail', self._default_load_thumbnail)
            request_thumbnail(p, load_func, self._on_thumbnail_loaded)
            
        if hasattr(self, 'on_files_added'):
            self.on_files_added(new_paths)
            
    def _default_load_thumbnail(self, path):
        return None
            
    def handle_external_targets(self, targets: list[str]):
        """Called by SingleInstance when new targets are received from a secondary instance"""
        print(f"[Mixin] Received external targets: {targets}")
        if targets:
            self._add_files([Path(t) for t in targets])
        self.activateWindow()
        self.raise_()

    def _on_thumbnail_loaded(self, path, pil_img):
        """Called on main thread with PIL Image from worker. Converts to QPixmap here."""
        if not pil_img:
            return
        try:
            row = self.state.files.index(path)
        except ValueError:
            return

        item = self.input_list.item(row)
        if item:
            # QPixmap must be created on the main thread — safe here via Qt signal dispatch
            rgba = pil_img.convert("RGBA")
            data = rgba.tobytes("raw", "RGBA")
            qimg = QImage(data, rgba.width, rgba.height, QImage.Format_RGBA8888).copy()
            pixmap = QPixmap.fromImage(qimg)
            item.setIcon(QIcon(pixmap))
