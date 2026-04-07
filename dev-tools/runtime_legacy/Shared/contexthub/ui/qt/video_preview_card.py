from __future__ import annotations

from .theme_metrics import get_shell_metrics
from .theme_style_helpers import set_surface_role
from shared._engine.components.icon_button import build_icon_button

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSlider, QStackedLayout, QVBoxLayout, QWidget
except ImportError as exc:
    raise ImportError("PySide6 is required for the shared Qt panel runtime.") from exc


class VideoPreviewCard(QFrame):
    """
    Dedicated modular class for video preview surface and playback controls.
    Does not require handling or importing QVideoWidget internally if it's fed
    from the outside (e.g. from the app main window) to avoid tying the Shared library
    to PySide6.QtMultimediaWidgets directly.
    """

    play_clicked = Signal()
    pause_clicked = Signal()
    seek_requested = Signal(int)
    volume_changed = Signal(int)
    mute_requested = Signal()

    def __init__(self, title: str = "Preview", empty_text: str = "Select a video to preview.", no_selection_text: str = "No video selected"):
        super().__init__()
        self.setObjectName("card")
        set_surface_role(self, "subtle")
        self.title_text = title
        self.empty_text = empty_text
        self.no_selection_text = no_selection_text
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("sectionTitle")
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setObjectName("summaryText")
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.time_label)
        layout.addLayout(header)

        self.surface_host = QFrame()
        set_surface_role(self.surface_host, "field")
        self.surface_layout = QVBoxLayout(self.surface_host)
        self.surface_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedLayout()
        self.placeholder = QLabel(self.empty_text)
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setObjectName("muted")
        self.stack.addWidget(self.placeholder)

        self.video_container = QWidget()
        self.stack.addWidget(self.video_container)

        container = QWidget()
        container.setLayout(self.stack)
        self.surface_layout.addWidget(container)
        layout.addWidget(self.surface_host, 1)

        self.name_label = QLabel(self.no_selection_text)
        self.name_label.setObjectName("title")
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.play_btn = build_icon_button("", icon_name="play", role="subtle")
        self.play_btn.clicked.connect(self.play_clicked.emit)

        self.pause_btn = build_icon_button("", icon_name="pause", role="subtle")
        self.pause_btn.clicked.connect(self.pause_clicked.emit)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderMoved.connect(self.seek_requested.emit)

        self.volume_btn = build_icon_button("", icon_name="volume-2", role="subtle")
        self.volume_btn.clicked.connect(self.mute_requested.emit)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setMaximumWidth(80)
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)

        controls.addWidget(self.play_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.slider, 1)
        controls.addWidget(self.volume_btn)
        controls.addWidget(self.volume_slider)
        layout.addLayout(controls)

    def set_placeholder_mode(self, show_placeholder: bool, text: str = ""):
        self.stack.setCurrentIndex(0 if show_placeholder else 1)
        if text:
            self.placeholder.setText(text)

    def set_metadata(self, name: str, time_info: str):
        self.name_label.setText(name)
        self.time_label.setText(time_info)
