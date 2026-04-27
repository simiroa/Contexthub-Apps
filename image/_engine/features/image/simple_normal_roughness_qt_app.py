from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.shell import (
    HeaderSurface,
    attach_size_grip,
    apply_app_icon,
    build_shell_stylesheet,
    get_shell_metrics,
    get_shell_palette,
    qt_t,
    refresh_runtime_preferences,
    runtime_settings_signature,
    set_surface_role,
    set_button_role,
)
from shared._engine.components.icon_button import build_icon_button
from shared._engine.components.input_card import build_input_card
from _engine.features.image.simple_normal_roughness_service import SimpleNormalRoughnessService

try:
    from PySide6.QtCore import QSettings, Qt, QTimer, Signal, Slot
    from PySide6.QtGui import QImage, QPixmap, QDragEnterEvent, QDropEvent
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLineEdit,
        QMainWindow,
        QVBoxLayout,
        QWidget,
        QLabel,
        QPushButton,
        QScrollArea,
        QFormLayout,
    )
except ImportError as exc:
    raise ImportError("PySide6 is required for simple_normal_roughness.") from exc

APP_ID = "simple_normal_roughness"
APP_TITLE = qt_t("simple_normal_roughness.title", "Simple PBR Generator")
APP_SUBTITLE = qt_t("simple_normal_roughness.subtitle", "Generate Normal/Roughness maps from images.")


class DropZoneCard(QFrame):
    files_dropped = Signal(list)

    def __init__(self, title: str, body: str):
        super().__init__()
        m = get_shell_metrics()
        set_surface_role(self, "card")
        self.setAcceptDrops(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(m.section_gap // 2)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        self.zone = QFrame()
        set_surface_role(self.zone, "subtle")
        self.zone.setMinimumHeight(100)
        zone_layout = QVBoxLayout(self.zone)
        self.body_label = QLabel(body)
        self.body_label.setAlignment(Qt.AlignCenter)
        self.body_label.setWordWrap(True)
        zone_layout.addWidget(self.body_label, 1)
        
        self.pick_btn = build_icon_button(qt_t("snr.pick", "Pick Images"), icon_name="file-plus", role="secondary")
        zone_layout.addWidget(self.pick_btn, 0, Qt.AlignCenter)
        
        layout.addWidget(self.zone)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            set_surface_role(self.zone, "accent")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        set_surface_role(self.zone, "subtle")

    def dropEvent(self, event: QDropEvent):
        set_surface_role(self.zone, "subtle")
        urls = event.mimeData().urls()
        if urls:
            paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
            self.files_dropped.emit(paths)
            event.acceptProposedAction()


class SimpleNormalRoughnessWindow(QMainWindow):
    def __init__(self, service: SimpleNormalRoughnessService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        self._field_widgets: dict[str, QWidget] = {}

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(700, 940)
        self.setMinimumSize(620, 800)
        apply_app_icon(self, self.app_root)

        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._bind_actions()

        if targets:
            self.service.add_inputs(targets)
        self._refresh_parameter_form()
        self._refresh_ui_state()
        self._runtime_timer.start()

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)

        # 1. Header
        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root)
        self.header_surface.set_header_visibility(show_subtitle=False, show_runtime_status=False)
        shell_layout.addWidget(self.header_surface)

        # 2. Mode Strip (Strip Check)
        self.mode_strip_card = QFrame()
        set_surface_role(self.mode_strip_card, "card")
        mode_strip_layout = QHBoxLayout(self.mode_strip_card)
        mode_strip_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        mode_strip_layout.setSpacing(8)
        
        mode_label = QLabel(qt_t("pbr.mode_strip", "Generate Mode"))
        mode_label.setObjectName("sectionTitle")
        mode_strip_layout.addWidget(mode_label)
        mode_strip_layout.addStretch(1)

        self.mode_buttons: dict[str, QPushButton] = {}
        for mode_name in ["Normal", "Roughness", "Both"]:
            btn = QPushButton(mode_name)
            btn.setCheckable(True)
            btn.setMinimumWidth(100)
            btn.clicked.connect(lambda _, m=mode_name: self._handle_mode_change(m))
            mode_strip_layout.addWidget(btn)
            self.mode_buttons[mode_name] = btn
        
        shell_layout.addWidget(self.mode_strip_card)

        # 3. Preview Card
        self.preview_card = QFrame()
        set_surface_role(self.preview_card, "card")
        preview_layout = QVBoxLayout(self.preview_card)
        preview_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        
        self.preview_surface = QFrame()
        set_surface_role(self.preview_surface, "subtle")
        self.preview_surface.setMinimumHeight(300)
        preview_surf_layout = QVBoxLayout(self.preview_surface)
        
        self.preview_label = QLabel(qt_t("pbr.no_preview", "No image selected"))
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_surf_layout.addWidget(self.preview_label, 1)
        preview_layout.addWidget(self.preview_surface, 1)
        
        # Meta info inside preview card
        self.meta_label = QLabel("")
        self.meta_label.setObjectName("summaryText")
        preview_layout.addWidget(self.meta_label)
        
        shell_layout.addWidget(self.preview_card, 1)

        # 4. Parameters Card (Dynamic)
        self.param_card = QFrame()
        set_surface_role(self.param_card, "card")
        self.param_layout = QVBoxLayout(self.param_card)
        self.param_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        
        param_title = QLabel(qt_t("pbr.parameters", "Parameters"))
        param_title.setObjectName("sectionTitle")
        self.param_layout.addWidget(param_title)
        
        self.param_content_layout = QFormLayout()
        self.param_content_layout.setSpacing(m.section_gap // 2)
        self.param_content_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.param_layout.addLayout(self.param_content_layout)
        
        shell_layout.addWidget(self.param_card)

        # 5. Footer Export Card
        self.footer_card = QFrame()
        set_surface_role(self.footer_card, "card")
        footer_layout = QVBoxLayout(self.footer_card)
        footer_layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        
        self.status_label = QLabel(qt_t("common.ready", "Ready. Drag an image to start."))
        self.status_label.setObjectName("summaryText")
        footer_layout.addWidget(self.status_label)
        
        btn_row = QHBoxLayout()
        self.reveal_btn = build_icon_button(None, icon_name="folder-open", role="ghost")
        self.run_btn = build_icon_button(qt_t("snr.generate", "Generate Maps"), icon_name="play", role="primary")
        btn_row.addWidget(self.reveal_btn)
        btn_row.addWidget(self.run_btn, 1)
        footer_layout.addLayout(btn_row)
        
        shell_layout.addWidget(self.footer_card)

        attach_size_grip(shell_layout, self.window_shell)
        root.addWidget(self.window_shell)

    def _bind_actions(self) -> None:
        self.preview_surface.setAcceptDrops(True)
        # Drop logic directly on the preview card
        self.preview_surface.dragEnterEvent = self._preview_drag_enter
        self.preview_surface.dropEvent = self._preview_drop
        
        self.run_btn.clicked.connect(self._run_workflow)
        self.reveal_btn.clicked.connect(self.service.reveal_output_dir)

    def _preview_drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            set_surface_role(self.preview_surface, "accent")
    
    def _preview_drop(self, event):
        set_surface_role(self.preview_surface, "subtle")
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.service.clear_inputs()
            self.service.add_inputs([path])
            self._refresh_ui_state()

    def _handle_mode_change(self, mode: str):
        # Update buttons
        for m, btn in self.mode_buttons.items():
            btn.setChecked(m == mode)
            set_button_role(btn, "primary" if m == mode else "secondary")
        
        # Sync service state
        self.service.update_parameter("save_mode", mode)
        # Use Normal/Roughness for preview if Both is selected
        self.service.update_parameter("preview_mode", "Normal" if mode == "Both" else mode)
        
        self._refresh_parameter_form()
        self._refresh_preview()

    def _refresh_parameter_form(self) -> None:
        # Clear
        while self.param_content_layout.count():
            item = self.param_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Recursively clear sub-layouts (if any)
                self._clear_layout(item.layout())

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        
        mode = self.service.state.parameter_values.get("save_mode", "Normal")
        self._field_widgets.clear()
        
        # Filter parameters based on mode
        defs = self.service.get_ui_definition()
        visible_keys = []
        if mode in ["Normal", "Both"]:
            visible_keys.extend(["normal_strength", "normal_flip_g"])
        if mode in ["Roughness", "Both"]:
            visible_keys.extend(["roughness_contrast", "roughness_invert"])
            
        # Add sub-headers if in Both mode
        added_normal_header = False
        added_roughness_header = False
        
        for d in defs:
            if d["key"] not in visible_keys:
                continue
            
            # Grouping headers
            if mode == "Both":
                if d["key"].startswith("normal") and not added_normal_header:
                    h = QLabel(qt_t("pbr.normal_settings", "Normal Map Settings"))
                    h.setStyleSheet("font-weight: bold; color: palette(link); margin-top: 5px;")
                    self.param_content_layout.addRow(h)
                    added_normal_header = True
                elif d["key"].startswith("roughness") and not added_roughness_header:
                    h = QLabel(qt_t("pbr.roughness_settings", "Roughness Map Settings"))
                    h.setStyleSheet("font-weight: bold; color: palette(link); margin-top: 5px;")
                    self.param_content_layout.addRow(h)
                    added_roughness_header = True

            label = QLabel(d["label"])
            val = self.service.state.parameter_values.get(d["key"], d["default"])
            
            if d["type"] == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(val))
                widget.stateChanged.connect(lambda s, k=d["key"]: self._update_and_preview(k, bool(s)))
            else: # float/string
                widget = QLineEdit(str(val))
                widget.textChanged.connect(lambda t, k=d["key"]: self._update_and_preview(k, t))
            
            self.param_content_layout.addRow(label, widget)
            self._field_widgets[d["key"]] = widget

    def _update_and_preview(self, key: str, value: any):
        self.service.update_parameter(key, value)
        self._refresh_preview()

    def _refresh_ui_state(self) -> None:
        # Sync the initial mode
        mode = self.service.state.parameter_values.get("save_mode", "Normal")
        self._handle_mode_change(mode)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        path = self.service.state.preview_path
        if not path:
            self.preview_label.setText(qt_t("pbr.no_preview", "Drop Image to Preview"))
            self.preview_label.setPixmap(QPixmap())
            self.meta_label.setText("")
            return
        
        try:
            pil_img = self.service.get_processed_preview(path)
            qimg = QImage(pil_img.tobytes(), pil_img.width, pil_img.height, QImage.Format_RGB888)
            pm = QPixmap.fromImage(qimg)
            
            scaled_pm = pm.scaled(
                self.preview_surface.size() - Qt.Size(20, 20), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pm)
            self.meta_label.setText(f"{pil_img.width}x{pil_img.height} | {path.suffix.upper()} ({self.service.state.parameter_values.get('preview_mode')})")
        except Exception as e:
            self.preview_label.setText(f"Preview Error: {e}")

    def _run_workflow(self) -> None:
        if not self.service.state.input_assets:
            self.status_label.setText("Please select an input image first.")
            return

        self.status_label.setText(qt_t("common.processing", "Generating maps..."))
        QApplication.processEvents()
        
        ok, msg, _ = self.service.run_workflow()
        self.status_label.setText(msg)

    def _check_runtime_preferences(self) -> None:
        if self._runtime_signature != runtime_settings_signature():
            self._runtime_signature = runtime_settings_signature()
            refresh_runtime_preferences()
            self.setStyleSheet(build_shell_stylesheet())

    def _restore_window_state(self) -> None:
        geo = self._settings.value("geometry")
        if geo: self.restoreGeometry(geo)

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def main(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    service = SimpleNormalRoughnessService()
    # Correct pathing to engine module
    app_root = Path(__file__).resolve().parents[3] / APP_ID
    window = SimpleNormalRoughnessWindow(service, app_root, targets)
    window.show()
    return app.exec()
