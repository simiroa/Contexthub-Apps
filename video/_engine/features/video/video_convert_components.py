import os
from PySide6.QtCore import Qt, Signal, QSize, QUrl
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QListWidget, QComboBox, 
    QLineEdit, QCheckBox, QAbstractItemView, QScrollArea, QSizePolicy,
    QStackedLayout, QSlider, QStyle
)
from contexthub.ui.qt.shell import (
    HeaderSurface, CardSurface, ScrollSurface, TitleLabel, BodyLabel, TooltipLabel,
    set_surface_role, set_field_role, qt_t
)
from shared._engine.components.icon_button import build_icon_button

class VideoPreviewCard(CardSurface):
    """
    Encapsulates the video preview surface, placeholder, and playback controls.
    """
    play_clicked = Signal()
    pause_clicked = Signal()
    stop_clicked = Signal()
    seek_changed = Signal(int)
    volume_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Preview Header
        header_layout = QHBoxLayout()
        self.preview_title = TitleLabel("Video Preview")
        self.preview_filename = BodyLabel("No file selected")
        self.preview_filename.set_subtle_role()
        header_layout.addWidget(self.preview_title)
        header_layout.addStretch()
        header_layout.addWidget(self.preview_filename)
        layout.addLayout(header_layout)

        # 2. Video Surface Container
        self.video_container = CardSurface()
        self.video_container.set_surface_role("field") # Recessed look
        self.video_container.setMinimumSize(480, 270)
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        video_layout = QVBoxLayout(self.video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        # Video Placeholder (Transparent surface for QVideoWidget)
        self.video_surface = QWidget()
        self.video_surface.setAttribute(Qt.WA_OpaquePaintEvent)
        video_layout.addWidget(self.video_surface)
        
        # Empty State Overlay
        self.empty_overlay = QWidget(self.video_container)
        overlay_layout = QVBoxLayout(self.empty_overlay)
        self.empty_label = BodyLabel("Select a video from the queue to preview")
        self.empty_label.set_subtle_role()
        self.empty_label.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(self.empty_label)
        
        layout.addWidget(self.video_container)

        # 3. Playback Controls
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        self.btn_play = build_icon_button("Play", icon_name="play", role="primary")
        self.btn_play.setFixedWidth(80)
        self.btn_play.clicked.connect(self.play_clicked)

        self.btn_pause = build_icon_button("Pause", icon_name="pause", role="secondary")
        self.btn_pause.setFixedWidth(80)
        self.btn_pause.clicked.connect(self.pause_clicked)

        self.time_label = BodyLabel("00:00 / 00:00")
        self.time_label.set_subtle_role()

        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.btn_pause)
        ctrl_layout.addSpacing(8)
        ctrl_layout.addWidget(self.time_label)
        ctrl_layout.addStretch()
        
        # Simple placeholder for Volume (Could be a slider in real app)
        self.volume_label = BodyLabel("Volume")
        self.volume_label.set_subtle_role()
        ctrl_layout.addWidget(self.volume_label)

        layout.addLayout(ctrl_layout)

    def set_filename(self, text):
        self.preview_filename.setText(text)
        self.empty_overlay.setVisible(not bool(text))
        self.video_surface.setVisible(bool(text))

    def update_time(self, current, total):
        self.time_label.setText(f"{current} / {total}")


class QueueCard(CardSurface):
    """
    Encapsulates the video queue list and management actions.
    """
    add_clicked = Signal()
    remove_clicked = Signal()
    clear_clicked = Signal()
    item_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Title Row with Action Buttons
        title_row = QWidget()
        title_row.setFixedHeight(56)
        title_row_layout = QHBoxLayout(title_row)
        title_row_layout.setContentsMargins(16, 0, 16, 0)
        
        self.title_label = TitleLabel("Queue")
        self.count_label = BodyLabel("(0)")
        self.count_label.set_subtle_role()
        
        btn_add = build_icon_button("Add", icon_name="plus", role="subtle")
        btn_add.clicked.connect(self.add_clicked)
        
        btn_remove = build_icon_button("Remove", icon_name="minus", role="subtle")
        btn_remove.clicked.connect(self.remove_clicked)
        
        btn_clear = build_icon_button("Clear", icon_name="trash-2", role="subtle")
        btn_clear.clicked.connect(self.clear_clicked)

        title_row_layout.addWidget(self.title_label)
        title_row_layout.addSpacing(4)
        title_row_layout.addWidget(self.count_label)
        title_row_layout.addStretch()
        title_row_layout.addWidget(btn_add)
        title_row_layout.addWidget(btn_remove)
        title_row_layout.addWidget(btn_clear)
        
        layout.addWidget(title_row)

        # 2. List Widget
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Use field role for list background if possible, or just default card styling
        self.list_widget.setStyleSheet("QListWidget { border: none; background: transparent; padding: 8px; }")
        
        layout.addWidget(self.list_widget)

    def _on_selection_changed(self):
        items = self.list_widget.selectedItems()
        if items:
            self.item_selected.emit(items[0].text())

    def update_count(self, count):
        self.count_label.setText(f"({count})")


class ParametersCard(CardSurface):
    """
    Encapsulates encoding parameters like presets, format, and CRF.
    """
    preset_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 24)
        layout.setSpacing(20)

        layout.addWidget(TitleLabel("Encoding Parameters"))

        # Form Layout Emulation
        form = QVBoxLayout()
        form.setSpacing(16)

        # Preset
        preset_box = QVBoxLayout()
        preset_box.setSpacing(4)
        preset_box.addWidget(BodyLabel("Conversion Preset"))
        self.combo_preset = QComboBox()
        self.combo_preset.set_field_role()
        self.combo_preset.currentTextChanged.connect(self.preset_changed)
        preset_box.addWidget(self.combo_preset)
        form.addLayout(preset_box)

        # Format & Scale Row
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        
        fmt_box = QVBoxLayout()
        fmt_box.addWidget(BodyLabel("Format"))
        self.combo_format = QComboBox()
        self.combo_format.set_field_role()
        fmt_box.addWidget(self.combo_format)
        row1.addLayout(fmt_box, 1)

        scale_box = QVBoxLayout()
        scale_box.addWidget(BodyLabel("Scale"))
        self.combo_scale = QComboBox()
        self.combo_scale.set_field_role()
        scale_box.addWidget(self.combo_scale)
        row1.addLayout(scale_box, 1)
        
        form.addLayout(row1)

        # CRF Slider Row (Simplified as SpinBox/Combo for now)
        crf_box = QVBoxLayout()
        crf_box.addWidget(BodyLabel("Quality (CRF)"))
        self.combo_crf = QComboBox()
        self.combo_crf.set_field_role()
        crf_box.addWidget(self.combo_crf)
        form.addLayout(crf_box)

        layout.addLayout(form)
        layout.addStretch()


class ExportRunCard(CardSurface):
    """
    Encapsulates output destination, foldout details, and action buttons.
    """
    run_clicked = Signal()
    stop_clicked = Signal()
    reveal_clicked = Signal()
    folder_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Output Folder
        folder_layout = QVBoxLayout()
        folder_layout.setSpacing(4)
        folder_layout.addWidget(TitleLabel("Export Settings"))
        
        path_row = QHBoxLayout()
        self.edit_path = QLineEdit()
        self.edit_path.set_field_role()
        self.edit_path.setReadOnly(True)
        
        btn_folder = build_icon_button("Browse", icon_name="folder", role="secondary")
        btn_folder.clicked.connect(self.folder_clicked)
        
        path_row.addWidget(self.edit_path)
        path_row.addWidget(btn_folder)
        folder_layout.addLayout(path_row)
        layout.addLayout(folder_layout)

        # 2. Details Foldout
        self.foldout_header = QWidget()
        foldout_layout = QHBoxLayout(self.foldout_header)
        foldout_layout.setContentsMargins(0, 4, 0, 4)
        
        self.btn_toggle = build_icon_button("More Options", icon_name="chevron-down", role="subtle")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.toggled.connect(self._on_foldout_toggled)
        
        foldout_layout.addWidget(self.btn_toggle)
        foldout_layout.addStretch()
        layout.addWidget(self.foldout_header)

        self.foldout_content = QWidget()
        self.foldout_content.setVisible(False)
        content_layout = QVBoxLayout(self.foldout_content)
        content_layout.setContentsMargins(12, 0, 0, 8)
        content_layout.setSpacing(10)

        self.check_delete_orig = QCheckBox("Delete original files after conversion")
        self.check_source_toggle = QCheckBox("Show source files in result folder")
        self.check_conv_toggle = QCheckBox("Show converted files in result folder")
        
        content_layout.addWidget(self.check_delete_orig)
        content_layout.addWidget(self.check_source_toggle)
        content_layout.addWidget(self.check_conv_toggle)
        
        layout.addWidget(self.foldout_content)

        # 3. Progress Area
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        
        self.status_label = BodyLabel("Ready")
        self.status_label.set_subtle_role()
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        layout.addWidget(self.progress_container)

        # 4. Action Row
        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.btn_run = build_icon_button("Start Conversion", icon_name="zap", role="primary")
        self.btn_run.clicked.connect(self.run_clicked)

        self.btn_stop = build_icon_button("Cancel", icon_name="x-circle", role="secondary")
        self.btn_stop.setVisible(False)
        self.btn_stop.clicked.connect(self.stop_clicked)

        self.btn_reveal = build_icon_button("Reveal", icon_name="external-link", role="secondary")
        self.btn_reveal.setFixedWidth(80)
        self.btn_reveal.clicked.connect(self.reveal_clicked)

        actions.addWidget(self.btn_run, 3)
        actions.addWidget(self.btn_stop, 3)
        actions.addWidget(self.btn_reveal, 1)
        layout.addLayout(actions)

    def _on_foldout_toggled(self, checked):
        from shared._engine.assets.icons.icon_utils import get_qicon
        self.foldout_content.setVisible(checked)
        self.btn_toggle.setText("Less Options" if checked else "More Options")
        icon_name = "chevron-up" if checked else "chevron-down"
        self.btn_toggle.setIcon(get_qicon(icon_name, color="#94a3b8")) # Secondary/Subtle grey

    def set_progress(self, value, status):
        self.progress_bar.setValue(value)
        self.status_label.setText(status)

    def set_running(self, running):
        self.btn_run.setVisible(not running)
        self.btn_stop.setVisible(running)
        self.progress_container.setVisible(running or self.progress_bar.value() > 0)
