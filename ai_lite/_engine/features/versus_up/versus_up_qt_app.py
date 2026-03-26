from __future__ import annotations

import sys
from pathlib import Path

from contexthub.ui.qt.shell import (
    CollapsibleSection,
    HeaderSurface,
    apply_app_icon,
    build_shell_stylesheet,
    build_size_grip,
    get_shell_metrics,
    get_shell_palette,
    refresh_runtime_preferences,
    runtime_settings_signature,
)
from features.versus_up import versus_up_matrix_controller as matrix_controller
from features.versus_up import versus_up_project_controller as project_controller
from features.versus_up.versus_up_service import PROJECT_EXTENSION, VersusUpService
from features.versus_up.versus_up_qt_panels import (
    CompareSummaryPanel,
    CriterionDetailPanel,
    HistoryPanel,
    ServerStatusPanel,
    WorkspacePanel,
)
from features.versus_up import versus_up_vision_controller as vision_controller
from features.versus_up.versus_up_qt_widgets import (
    CriterionMatrixCellWidget,
    DONUT_COLORS,
    EdgeAddButton,
    ProductMatrixCellWidget,
    ProposalReviewDialog,
    TemplatePickerDialog,
    TextEntryDialog,
    VisionPopup,
    VisionWorker,
)
from features.versus_up.versus_up_state import CriterionRecord, ProductRecord

try:
    from PySide6.QtCore import QPoint, QSettings, QSize, Qt, QThread, QTimer
    from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QDialog,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QListWidgetItem,
        QMenu,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSplitter,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for versus_up.") from exc

APP_ID = "versus_up"
APP_TITLE = "VersusUp"
APP_SUBTITLE = "Weighted decision support with OCR and hover vision review."
PRODUCT_PALETTE = ["#7f8a96", "#5e9777", "#b49563", "#7797c6", "#9b8fd8", "#c97d5a", "#6f9b32", "#c28a3a"]


class VersusUpWindow(QMainWindow):
    def __init__(self, service: VersusUpService, app_root: str | Path, targets: list[str] | None = None) -> None:
        super().__init__()
        self.service = service
        self.app_root = Path(app_root)
        self._settings = QSettings("Contexthub", APP_ID)
        self._runtime_signature = runtime_settings_signature()
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1500)
        self._runtime_timer.timeout.connect(self._check_runtime_preferences)
        self._vision_threads: dict[str, tuple[QThread, VisionWorker]] = {}
        self._popup_product_id: str | None = None
        self._product_header_cards: dict[str, ProductMatrixCellWidget] = {}
        self._criterion_header_cards: dict[str, CriterionMatrixCellWidget] = {}
        self._building_matrix = False
        self._detail_mode = "criterion"
        self._history_mode = "recent"
        self.vision_popup = VisionPopup(self)
        self.vision_popup.apply_requested.connect(self._review_popup_product)
        self.vision_popup.dismissed.connect(self._clear_popup_product)
        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1560, 940)
        self.setMinimumSize(1380, 920)
        apply_app_icon(self, self.app_root)
        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._bind_actions()
        self._build_history_menu()
        self._build_product_palette()
        self._restore_window_state()
        self.service.open_recent_or_default()
        self._refresh_all()
        self._runtime_timer.start()

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        p = get_shell_palette()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2, m.shell_margin - 2)
        root.setSpacing(m.section_gap)
        self.window_shell = QFrame()
        self.window_shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.window_shell)
        shell_layout.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        shell_layout.setSpacing(m.section_gap)
        self.header_surface = HeaderSurface(self, APP_TITLE, APP_SUBTITLE, self.app_root, show_webui=False)
        self.runtime_status_badge = self.header_surface.runtime_status_badge
        self.asset_count_badge = self.header_surface.asset_count_badge
        shell_layout.addWidget(self.header_surface)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(self._build_left_panel())
        self.main_splitter.addWidget(self._build_center_panel())
        self.main_splitter.addWidget(self._build_right_panel())
        self.main_splitter.setSizes([340, 790, 400])
        shell_layout.addWidget(self.main_splitter, 1)
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 2, 0)
        grip_row.addStretch(1)
        self.size_grip = build_size_grip()
        self.size_grip.setParent(self.window_shell)
        grip_row.addWidget(self.size_grip, 0, Qt.AlignRight | Qt.AlignBottom)
        shell_layout.addLayout(grip_row)
        root.addWidget(self.window_shell)
        self.workspace_panel.matrix_table.setStyleSheet(
            f"QTableWidget {{ background: {p.field_bg}; border: 1px solid {p.border}; border-radius: 14px; gridline-color: {p.border}; font-size: 15px; }}"
            f"QTableWidget::item {{ padding: 6px; }}"
        )
        self.workspace_panel.matrix_table.setWordWrap(True)
        list_style = (
            "QListWidget { background:#111722; border:1px solid #2a3852; border-radius:14px; padding:6px; }"
            "QListWidget::item { margin:4px 2px; padding:10px 10px; border-radius:10px; }"
            "QListWidget::item:selected { background:#253246; }"
        )
        self.history_panel.recent_list.setStyleSheet(list_style)
        self.history_panel.preset_list.setStyleSheet(list_style)

    def _build_left_panel(self) -> QWidget:
        m = get_shell_metrics()
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)
        self.history_panel = HistoryPanel()
        layout.addWidget(self.history_panel, 1)
        return card

    def _build_center_panel(self) -> QWidget:
        self.workspace_panel = WorkspacePanel()
        return self.workspace_panel

    def _build_right_panel(self) -> QWidget:
        m = get_shell_metrics()
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(m.panel_padding, m.panel_padding, m.panel_padding, m.panel_padding)
        layout.setSpacing(10)
        self.compare_panel = CompareSummaryPanel()
        self.compare_panel.setMaximumHeight(318)
        self.detail_panel = CriterionDetailPanel()
        self.server_panel = ServerStatusPanel()
        layout.addWidget(self.compare_panel, 0)
        layout.addWidget(self.detail_panel, 1)
        layout.addWidget(self.server_panel, 0)
        return card

    def _bind_actions(self) -> None:
        self.history_panel.new_btn.clicked.connect(self._new_project)
        self.history_panel.open_btn.clicked.connect(self._open_project)
        self.history_panel.add_preset_btn.clicked.connect(self._save_preset)
        self.history_panel.remove_preset_btn.clicked.connect(self._remove_preset)
        self.history_panel.recent_tab_btn.clicked.connect(lambda: self._set_history_mode("recent"))
        self.history_panel.presets_tab_btn.clicked.connect(lambda: self._set_history_mode("presets"))
        self.detail_panel.criterion_label_edit.editingFinished.connect(self._commit_criterion_detail)
        self.detail_panel.criterion_description_edit.textChanged.connect(self._commit_criterion_detail)
        self.detail_panel.criterion_type_combo.currentTextChanged.connect(self._commit_criterion_detail)
        self.detail_panel.criterion_direction_combo.currentTextChanged.connect(self._commit_criterion_detail)
        self.detail_panel.criterion_unit_edit.editingFinished.connect(self._commit_criterion_detail)
        self.detail_panel.criterion_include_box.toggled.connect(self._commit_criterion_detail)
        self.detail_panel.criterion_weight_slider.valueChanged.connect(self._commit_criterion_detail)
        self.detail_panel.product_name_edit.editingFinished.connect(self._commit_product_detail)
        self.detail_panel.product_color_edit.editingFinished.connect(self._commit_product_detail)
        self.detail_panel.product_notes_edit.textChanged.connect(self._commit_product_detail)
        self.detail_panel.product_favorite_box.toggled.connect(self._commit_product_detail)
        self.detail_panel.product_image_btn.clicked.connect(self._attach_image)
        self.detail_panel.product_vision_btn.clicked.connect(self._run_selected_product_vision)
        self.detail_panel.product_delete_btn.clicked.connect(self._remove_selected_product)
        self.detail_panel.product_remove_image_btn.clicked.connect(self._remove_selected_product_image)
        self.detail_panel.product_thumbnail.mousePressEvent = lambda _event: self._attach_image()
        self.server_panel.ollama_host_edit.editingFinished.connect(self._commit_runtime_settings)
        self.server_panel.vision_model_edit.editingFinished.connect(self._commit_runtime_settings)
        self.server_panel.classifier_model_edit.editingFinished.connect(self._commit_runtime_settings)
        self.history_panel.recent_list.itemDoubleClicked.connect(self._open_recent_item)
        self.history_panel.preset_list.itemDoubleClicked.connect(self._open_preset_item)
        self.workspace_panel.matrix_table.currentCellChanged.connect(self._sync_selection_from_table)
        self.workspace_panel.matrix_table.itemChanged.connect(self._handle_matrix_item_changed)
        save_shortcut = QAction(self)
        save_shortcut.setShortcut("Ctrl+S")
        save_shortcut.triggered.connect(self._save_project)
        self.addAction(save_shortcut)

    def _build_history_menu(self) -> None:
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        duplicate_action = menu.addAction("Duplicate")
        export_action = menu.addAction("Export")
        rename_action.triggered.connect(self._rename_project)
        duplicate_action.triggered.connect(self._duplicate_project)
        export_action.triggered.connect(self._export_report)
        self.history_panel.project_menu_btn.setMenu(menu)

    def _build_product_palette(self) -> None:
        self.detail_panel.product_color_buttons = []
        while self.detail_panel.product_palette_row.count():
            item = self.detail_panel.product_palette_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for color in PRODUCT_PALETTE:
            button = QPushButton("")
            button.setFixedSize(34, 34)
            button.clicked.connect(lambda _=False, c=color: self._select_product_color(c))
            button.setProperty("swatchColor", color)
            self.detail_panel.product_palette_row.addWidget(button)
            self.detail_panel.product_color_buttons.append(button)
        self.detail_panel.product_palette_row.addStretch(1)
        self._refresh_palette_selection(None)

    def _display_products(self) -> list[ProductRecord]:
        return self.service.sorted_products()

    def _refresh_all(self) -> None:
        self._refresh_history_card()
        self._rebuild_matrix()
        self._refresh_detail_panel()
        self._refresh_header()
        self._refresh_server_status()
        self._refresh_compare_summary()

    def _refresh_history_card(self) -> None:
        self.server_panel.ollama_host_edit.blockSignals(True)
        self.server_panel.vision_model_edit.blockSignals(True)
        self.server_panel.classifier_model_edit.blockSignals(True)
        self.history_panel.current_project_label.setText(
            f"{self.service.state.project_meta.name}\n{self.service.state.project_meta.category}"
        )
        self.server_panel.ollama_host_edit.setText(self.service.state.ollama_host)
        self.server_panel.vision_model_edit.setText(self.service.state.vision_model)
        self.server_panel.classifier_model_edit.setText(self.service.state.classifier_model)
        self.server_panel.ollama_host_edit.blockSignals(False)
        self.server_panel.vision_model_edit.blockSignals(False)
        self.server_panel.classifier_model_edit.blockSignals(False)
        self.history_panel.recent_list.clear()
        current_path = str(self.service.state.project_path) if self.service.state.project_path else ""
        for entry in self.service.recent_project_entries():
            label = entry["name"]
            if entry["category"]:
                label = f"{entry['name']}\n{entry['category']}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, entry["path"])
            item.setToolTip(entry["path"])
            self.history_panel.recent_list.addItem(item)
            if entry["path"] == current_path:
                self.history_panel.recent_list.setCurrentItem(item)
        self.history_panel.preset_list.clear()
        for preset in self.service.preset_entries():
            label = preset["name"]
            if preset["category"]:
                label = f"{preset['name']}\n{preset['category']}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, preset["id"])
            self.history_panel.preset_list.addItem(item)
        self.history_panel.list_stack.setCurrentIndex(0 if self._history_mode == "recent" else 1)
        self.history_panel.recent_tab_btn.setObjectName("primary" if self._history_mode == "recent" else "")
        self.history_panel.presets_tab_btn.setObjectName("primary" if self._history_mode == "presets" else "")
        self.history_panel.remove_preset_btn.setVisible(self._history_mode == "presets")
        self.history_panel.project_menu_btn.setText("More")
        self.history_panel.add_preset_btn.setText("Preset")

    def _set_history_mode(self, mode: str) -> None:
        self._history_mode = mode
        self._refresh_history_card()

    def _matrix_row_count(self) -> int:
        return matrix_controller.matrix_row_count(self)

    def _matrix_col_count(self) -> int:
        return matrix_controller.matrix_col_count(self)

    def _is_data_cell(self, row: int, column: int) -> bool:
        return matrix_controller.is_data_cell(self, row, column)

    def _is_product_header(self, row: int, column: int) -> bool:
        return matrix_controller.is_product_header(self, row, column)

    def _is_criterion_header(self, row: int, column: int) -> bool:
        return matrix_controller.is_criterion_header(self, row, column)

    def _criterion_for_row(self, row: int) -> CriterionRecord | None:
        return matrix_controller.criterion_for_row(self, row)

    def _product_for_col(self, column: int) -> ProductRecord | None:
        return matrix_controller.product_for_col(self, column)

    def _display_cell_value(self, product_id: str, criterion: CriterionRecord) -> str:
        return matrix_controller.display_cell_value(self, product_id, criterion)

    def _criterion_header_text(self, criterion: CriterionRecord) -> str:
        meta = []
        if criterion.unit:
            meta.append(criterion.unit)
        meta.append("high" if criterion.direction == "high" else "low")
        meta.append(f"W{criterion.weight:.1f}")
        return f"{criterion.label}\n{' / '.join(meta)}"

    def _make_table_item(self, text: str, *, role: str, raw_value: str = "", criterion: CriterionRecord | None = None) -> QTableWidgetItem:
        return matrix_controller.make_table_item(self, text, role=role, raw_value=raw_value, criterion=criterion)

    def _apply_data_cell_style(self, item: QTableWidgetItem, criterion: CriterionRecord, raw_value: str) -> None:
        matrix_controller.apply_data_cell_style(self, item, criterion, raw_value)

    def _rebuild_matrix(self) -> None:
        matrix_controller.rebuild_matrix(self)

    def _refresh_detail_panel(self) -> None:
        matrix_controller.refresh_detail_panel(self)

    def _build_insight_segments(self, product: ProductRecord) -> list[tuple[str, float, str]]:
        return matrix_controller.build_insight_segments(self, product)

    def _refresh_compare_summary(self) -> None:
        matrix_controller.refresh_compare_summary(self)

    def _refresh_header(self) -> None:
        matrix_controller.refresh_header(self)

    def _refresh_server_status(self) -> None:
        matrix_controller.refresh_server_status(self)

    def _selected_product(self) -> ProductRecord | None:
        return self.service.product_by_id(self.service.state.selected_product_id)

    def _selected_criterion(self) -> CriterionRecord | None:
        return self.service.criterion_by_id(self.service.state.selected_criterion_id)

    def _sync_selection_from_product_list(self) -> None:
        product_id = self.service.state.selected_product_id or (self.service.state.products[0].id if self.service.state.products else None)
        if product_id is None:
            return
        self.service.state.selected_product_id = product_id
        product_index = next((i for i, product in enumerate(self._display_products()) if product.id == product_id), 0)
        row = next((i for i, criterion in enumerate(self.service.state.criteria) if criterion.id == self.service.state.selected_criterion_id), 0)
        if self.service.state.criteria:
            self.workspace_panel.matrix_table.setCurrentCell(row + 1, product_index + 1)
        self._refresh_detail_panel()
        self._refresh_server_status()

    def _sync_selection_from_table(self, current_row: int, current_column: int, _previous_row: int, _previous_column: int) -> None:
        matrix_controller.sync_selection_from_table(self, current_row, current_column, _previous_row, _previous_column)

    def _handle_matrix_item_changed(self, item: QTableWidgetItem) -> None:
        matrix_controller.handle_matrix_item_changed(self, item)

    def _commit_criterion_detail(self) -> None:
        matrix_controller.commit_criterion_detail(self)

    def _commit_product_detail(self) -> None:
        matrix_controller.commit_product_detail(self)

    def _select_product_color(self, color: str) -> None:
        matrix_controller.select_product_color(self, color)

    def _product_accent(self, product: ProductRecord | None, fallback_index: int | None = None) -> str:
        if product and product.color:
            return product.color
        if product:
            products = self._display_products()
            index = next((i for i, item in enumerate(products) if item.id == product.id), 0)
            return DONUT_COLORS[index % len(DONUT_COLORS)]
        return DONUT_COLORS[(fallback_index or 0) % len(DONUT_COLORS)]

    def _refresh_palette_selection(self, selected_color: str | None) -> None:
        normalized = (selected_color or "").lower()
        for button in self.detail_panel.product_color_buttons:
            color = str(button.property("swatchColor"))
            is_selected = color.lower() == normalized
            button.setStyleSheet(
                f"background:{color}; border:{'3px solid #f3f7ff' if is_selected else '1px solid ' + color}; "
                f"border-radius:17px; {'padding:1px;' if is_selected else ''}"
            )

    def _refresh_product_header_selection(self) -> None:
        selected = self._selected_product().id if self._selected_product() else None
        for product_id, widget in self._product_header_cards.items():
            widget.set_selected(product_id == selected)

    def _refresh_criterion_header_selection(self) -> None:
        selected = self._selected_criterion().id if self._selected_criterion() else None
        for criterion_id, widget in self._criterion_header_cards.items():
            widget.set_selected(criterion_id == selected and self._detail_mode != "product")

    def _select_product_header(self, column: int, product_id: str) -> None:
        self.service.state.selected_product_id = product_id
        self._detail_mode = "product"
        self.workspace_panel.matrix_table.setCurrentCell(0, column)

    def _commit_runtime_settings(self) -> None:
        project_controller.commit_runtime_settings(self)

    def _new_project(self) -> None:
        project_controller.new_project(self)

    def _open_project(self) -> None:
        project_controller.open_project(self, APP_TITLE)

    def _save_project(self) -> None:
        project_controller.save_project(self, APP_TITLE)

    def _rename_project(self) -> None:
        project_controller.rename_project(self, APP_TITLE)

    def _duplicate_project(self) -> None:
        project_controller.duplicate_project(self, APP_TITLE)

    def _export_report(self) -> None:
        project_controller.export_report(self)

    def _export_project_snapshot(self) -> None:
        project_controller.export_project_snapshot(self)

    def _save_preset(self) -> None:
        project_controller.save_preset(self, APP_TITLE)

    def _remove_preset(self) -> None:
        project_controller.remove_preset(self)

    def _add_product(self) -> None:
        self.service.add_product()
        self._refresh_all()

    def _remove_selected_product(self) -> None:
        product = self._selected_product()
        if product is None:
            return
        self.service.remove_product(product.id)
        self._refresh_all()

    def _attach_image(self) -> None:
        vision_controller.attach_image(self)

    def _attach_image_for(self, product_id: str) -> None:
        vision_controller.attach_image_for(self, product_id)

    def _select_gallery_image(self, item) -> None:
        vision_controller.select_gallery_image(self, item)

    def _remove_selected_product_image(self) -> None:
        vision_controller.remove_selected_product_image(self)

    def _clear_product_gallery(self) -> None:
        while self.detail_panel.product_gallery_layout.count():
            item = self.detail_panel.product_gallery_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _append_gallery_item(self, product: ProductRecord, image_path: str, is_main: bool) -> None:
        index = self.detail_panel.product_gallery_layout.count()
        button = QPushButton()
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedSize(88, 88)
        button.setProperty("imagePath", image_path)
        pixmap = QPixmap(image_path)
        accent = self._product_accent(product)
        if not pixmap.isNull():
            button.setIcon(QIcon(pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            button.setIconSize(QSize(72, 72))
            button.setText("")
        else:
            button.setText(Path(image_path).name[:10] or "IMG")
        border = "2px solid #f3f7ff" if is_main else f"1px solid {accent}55"
        button.setStyleSheet(
            f"QPushButton {{ background:#111722; border:{border}; border-radius:16px; padding:6px; text-align:center; }}"
            f"QPushButton:hover {{ border-color:{accent}; background:#172131; }}"
        )
        button.clicked.connect(self._select_gallery_image)
        row = index // 4
        col = index % 4
        self.detail_panel.product_gallery_layout.addWidget(button, row, col)

    def _run_selected_product_vision(self) -> None:
        vision_controller.run_selected_product_vision(self)

    def _run_product_vision(self, product_id: str) -> None:
        vision_controller.run_product_vision(self, product_id)

    def _rename_product(self, product_id: str, value: str) -> None:
        product = self.service.product_by_id(product_id)
        if product is None:
            return
        self.service.update_product(product_id, name=value.strip() or product.name)
        self._refresh_all()

    def _toggle_product_favorite(self, product_id: str, favorite: bool) -> None:
        self.service.update_product(product_id, favorite=favorite)
        self._refresh_all()

    def _delete_product_from_header(self, product_id: str) -> None:
        self.service.remove_product(product_id)
        self._refresh_all()

    def _add_criterion(self) -> None:
        self.service.add_criterion(description="Describe how this field should be judged.")
        self._refresh_all()

    def _remove_selected_criterion(self) -> None:
        criterion = self._selected_criterion()
        if criterion is None:
            return
        self.service.remove_criterion(criterion.id)
        self._refresh_all()

    def _open_recent_item(self, item: QListWidgetItem) -> None:
        project_controller.open_recent_item(self, item)

    def _open_preset_item(self, item: QListWidgetItem) -> None:
        project_controller.open_preset_item(self, item)

    def _start_vision_thread(self, product_id: str) -> None:
        vision_controller.start_vision_thread(self, product_id)

    def _on_product_hovered(self, product_id: str, global_pos: QPoint) -> None:
        vision_controller.on_product_hovered(self, product_id, global_pos)

    def _clear_popup_product(self) -> None:
        vision_controller.clear_popup_product(self)

    def _cleanup_vision_thread(self, product_id: str) -> None:
        vision_controller.cleanup_vision_thread(self, product_id)

    def _on_vision_finished(self, product_id: str, _cache) -> None:
        vision_controller.on_vision_finished(self, product_id, _cache)

    def _on_vision_failed(self, product_id: str, message: str) -> None:
        vision_controller.on_vision_failed(self, product_id, message)

    def _review_popup_product(self) -> None:
        vision_controller.review_popup_product(self, APP_TITLE)

    def _check_runtime_preferences(self) -> None:
        current = runtime_settings_signature()
        if current == self._runtime_signature:
            return
        self._runtime_signature = current
        refresh_runtime_preferences()
        self.setStyleSheet(build_shell_stylesheet())

    def _restore_window_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        splitter = self._settings.value("splitter")
        if splitter:
            self.main_splitter.restoreState(splitter)
        if self._settings.value("is_maximized", False, bool):
            self.showMaximized()

    def closeEvent(self, event) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("splitter", self.main_splitter.saveState())
        self._settings.setValue("is_maximized", self.isMaximized())
        super().closeEvent(event)


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = VersusUpWindow(VersusUpService(), Path(__file__).resolve().parents[3] / APP_ID, targets)
    window.show()
    return app.exec()
