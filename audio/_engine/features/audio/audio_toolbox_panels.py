from __future__ import annotations

from dataclasses import dataclass

from contexthub.ui.qt.shell import set_transparent_surface
from features.audio.audio_toolbox_tasks import (
    COMPRESS_LEVELS,
    CONVERT_QUALITIES,
    ENHANCE_PROFILES,
    SEPARATOR_MODELS,
    SEPARATOR_STEM_MODES,
)

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QFrame,
        QScrollArea,
        QSizePolicy,
        QSpinBox,
        QStackedWidget,
        QVBoxLayout,
        QWidget,
        QLabel,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for audio_toolbox panels.") from exc


@dataclass
class AudioToolboxPanels:
    task_stack: QStackedWidget
    model_combo: QComboBox
    stem_mode_combo: QComboBox
    chunk_spin: QSpinBox
    loudness_spin: QDoubleSpinBox
    true_peak_spin: QDoubleSpinBox
    lra_spin: QDoubleSpinBox
    convert_quality_combo: QComboBox
    copy_metadata_check: QCheckBox
    delete_original_check: QCheckBox
    compress_level_combo: QComboBox
    enhance_profile_combo: QComboBox


def build_option_panels() -> AudioToolboxPanels:
    task_stack = QStackedWidget()

    model_combo = QComboBox()
    model_combo.addItems(SEPARATOR_MODELS)
    stem_mode_combo = QComboBox()
    stem_mode_combo.addItems(SEPARATOR_STEM_MODES)
    chunk_spin = QSpinBox()
    chunk_spin.setRange(0, 3600)
    chunk_spin.setSingleStep(60)
    chunk_spin.setSuffix(" sec")
    chunk_spin.setToolTip("Use a chunk duration for long files to reduce peak memory usage.")
    task_stack.addWidget(
        _build_scroll_panel(
            (
                ("Model", model_combo),
                ("Stem Mode", stem_mode_combo),
                ("Chunking", chunk_spin),
            )
        )
    )

    loudness_spin = QDoubleSpinBox()
    loudness_spin.setRange(-40.0, -1.0)
    loudness_spin.setDecimals(1)
    loudness_spin.setSingleStep(0.5)
    true_peak_spin = QDoubleSpinBox()
    true_peak_spin.setRange(-9.0, 0.0)
    true_peak_spin.setDecimals(1)
    true_peak_spin.setSingleStep(0.5)
    lra_spin = QDoubleSpinBox()
    lra_spin.setRange(1.0, 20.0)
    lra_spin.setDecimals(1)
    lra_spin.setSingleStep(0.5)
    task_stack.addWidget(
        _build_scroll_panel(
            (
                ("Target LUFS", loudness_spin),
                ("True Peak", true_peak_spin),
                ("Loudness Range", lra_spin),
            )
        )
    )

    convert_quality_combo = QComboBox()
    convert_quality_combo.addItems(CONVERT_QUALITIES)
    copy_metadata_check = QCheckBox("Copy metadata")
    delete_original_check = QCheckBox("Delete original after conversion")
    task_stack.addWidget(
        _build_scroll_panel(
            (("Quality", convert_quality_combo),),
            extra_widgets=(copy_metadata_check, delete_original_check),
        )
    )

    compress_level_combo = QComboBox()
    compress_level_combo.addItems(COMPRESS_LEVELS)
    task_stack.addWidget(_build_scroll_panel((("Compression", compress_level_combo),)))

    enhance_profile_combo = QComboBox()
    enhance_profile_combo.addItems(ENHANCE_PROFILES)
    task_stack.addWidget(_build_scroll_panel((("Enhance", enhance_profile_combo),)))

    return AudioToolboxPanels(
        task_stack=task_stack,
        model_combo=model_combo,
        stem_mode_combo=stem_mode_combo,
        chunk_spin=chunk_spin,
        loudness_spin=loudness_spin,
        true_peak_spin=true_peak_spin,
        lra_spin=lra_spin,
        convert_quality_combo=convert_quality_combo,
        copy_metadata_check=copy_metadata_check,
        delete_original_check=delete_original_check,
        compress_level_combo=compress_level_combo,
        enhance_profile_combo=enhance_profile_combo,
    )


def _build_scroll_panel(fields: tuple[tuple[str, QWidget], ...], extra_widgets: tuple[QWidget, ...] = ()) -> QWidget:
    panel = QWidget()
    set_transparent_surface(panel)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    for label, widget in fields:
        layout.addWidget(_field_block(label, widget))
    for widget in extra_widgets:
        layout.addWidget(widget)
    layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    set_transparent_surface(scroll.viewport())
    set_transparent_surface(panel)
    scroll.setWidget(panel)
    return scroll


def _field_block(label: str, widget: QWidget) -> QWidget:
    block = QWidget()
    set_transparent_surface(block)
    block.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
    layout = QVBoxLayout(block)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    title = QLabel(label)
    title.setObjectName("eyebrow")
    title.setMinimumHeight(16)
    layout.addWidget(title)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    widget.setMinimumHeight(max(widget.minimumHeight(), 38))
    layout.addWidget(widget)
    return block
