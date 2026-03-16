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
from features.versus_up.versus_up_service import PROJECT_EXTENSION, VersusUpService
from features.versus_up.versus_up_qt_panels import (
    CompareSummaryPanel,
    CriterionDetailPanel,
    HistoryPanel,
    ServerStatusPanel,
    WorkspacePanel,
)
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
        return len(self.service.state.criteria) + 2

    def _matrix_col_count(self) -> int:
        return len(self.service.state.products) + 2

    def _is_data_cell(self, row: int, column: int) -> bool:
        return 0 < row < self._matrix_row_count() - 1 and 0 < column < self._matrix_col_count() - 1

    def _is_product_header(self, row: int, column: int) -> bool:
        return row == 0 and 0 < column < self._matrix_col_count() - 1

    def _is_criterion_header(self, row: int, column: int) -> bool:
        return column == 0 and 0 < row < self._matrix_row_count() - 1

    def _criterion_for_row(self, row: int) -> CriterionRecord | None:
        if not self._is_criterion_header(row, 0) and not (0 < row < self._matrix_row_count() - 1):
            return None
        return self.service.state.criteria[row - 1]

    def _product_for_col(self, column: int) -> ProductRecord | None:
        if not self._is_product_header(0, column) and not (0 < column < self._matrix_col_count() - 1):
            return None
        products = self._display_products()
        return products[column - 1] if 0 <= column - 1 < len(products) else None

    def _display_cell_value(self, product_id: str, criterion: CriterionRecord) -> str:
        raw = self.service.cell_value(product_id, criterion.id)
        if raw and criterion.unit and criterion.type == "number":
            return f"{raw} {criterion.unit}"
        return raw

    def _criterion_header_text(self, criterion: CriterionRecord) -> str:
        meta = []
        if criterion.unit:
            meta.append(criterion.unit)
        meta.append("high" if criterion.direction == "high" else "low")
        meta.append(f"W{criterion.weight:.1f}")
        return f"{criterion.label}\n{' / '.join(meta)}"

    def _make_table_item(self, text: str, *, role: str, raw_value: str = "", criterion: CriterionRecord | None = None) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setData(Qt.UserRole, role)
        if raw_value:
            item.setData(Qt.UserRole + 1, raw_value)
        if criterion is not None:
            item.setToolTip(f"{criterion.label}\n{criterion.description or 'No description'}\nWeight: {criterion.weight:.2f} / {criterion.direction}")
        return item

    def _apply_data_cell_style(self, item: QTableWidgetItem, criterion: CriterionRecord, raw_value: str) -> None:
        palette = get_shell_palette()
        item.setForeground(Qt.white)
        if criterion.type == "number" and criterion.include_in_score:
            values = []
            for product in self._display_products():
                try:
                    values.append(float(self.service.cell_value(product.id, criterion.id)))
                except Exception:
                    continue
            try:
                current = float(raw_value)
            except Exception:
                current = None
            if values and current is not None:
                best = max(values) if criterion.direction == "high" else min(values)
                worst = min(values) if criterion.direction == "high" else max(values)
                if current == best:
                    item.setBackground(QColor("#1d4a33"))
                    return
                if current == worst and len(values) > 1:
                    item.setBackground(QColor("#573035"))
                    return
        item.setBackground(QColor(palette.field_bg))

    def _rebuild_matrix(self) -> None:
        table = self.workspace_panel.matrix_table
        self._building_matrix = True
        table.blockSignals(True)
        table.clear()
        table.setRowCount(self._matrix_row_count())
        table.setColumnCount(self._matrix_col_count())
        self._product_header_cards = {}
        self._criterion_header_cards = {}
        self.workspace_panel.matrix_context_label.setText(f"{self.service.state.project_meta.name} / {self.service.state.project_meta.category}")
        products = self._display_products()
        product_count = max(1, len(products))
        product_width = 196 if product_count <= 2 else 170 if product_count <= 4 else 152
        for row in range(self._matrix_row_count()):
            table.setRowHeight(row, 158 if row == 0 else 56)
        for column in range(self._matrix_col_count()):
            if column == 0:
                table.setColumnWidth(column, 250)
            elif column == self._matrix_col_count() - 1:
                table.setColumnWidth(column, 110)
            else:
                table.setColumnWidth(column, product_width)
        corner = self._make_table_item("Criteria / Products", role="corner")
        table.setItem(0, 0, corner)
        for product_index, product in enumerate(products, start=1):
            header_item = self._make_table_item("", role="product_header")
            table.setItem(0, product_index, header_item)
            widget = ProductMatrixCellWidget(product.id, table)
            accent = product.color or DONUT_COLORS[(product_index - 1) % len(DONUT_COLORS)]
            widget.set_product(product, self.service.state.scores.get(product.id, 0.0), accent)
            widget.selected.connect(lambda product_id, column=product_index: self._select_product_header(column, product_id))
            table.setCellWidget(0, product_index, widget)
            self._product_header_cards[product.id] = widget
        add_product_item = self._make_table_item("", role="add_product")
        table.setItem(0, self._matrix_col_count() - 1, add_product_item)
        add_product_button = EdgeAddButton("+ Product", table)
        add_product_button.clicked.connect(self._add_product)
        table.setCellWidget(0, self._matrix_col_count() - 1, add_product_button)
        for row_index, criterion in enumerate(self.service.state.criteria, start=1):
            criterion_item = self._make_table_item("", role="criterion_header", criterion=criterion)
            table.setItem(row_index, 0, criterion_item)
            criterion_widget = CriterionMatrixCellWidget(criterion.id, table)
            criterion_widget.set_criterion(criterion)
            table.setCellWidget(row_index, 0, criterion_widget)
            self._criterion_header_cards[criterion.id] = criterion_widget
            for col_index, product in enumerate(products, start=1):
                raw = self.service.cell_value(product.id, criterion.id)
                data_item = self._make_table_item(self._display_cell_value(product.id, criterion), role="data", raw_value=raw, criterion=criterion)
                self._apply_data_cell_style(data_item, criterion, raw)
                table.setItem(row_index, col_index, data_item)
            filler = self._make_table_item("", role="filler")
            table.setItem(row_index, self._matrix_col_count() - 1, filler)
        add_criterion_item = self._make_table_item("", role="add_criterion")
        table.setItem(self._matrix_row_count() - 1, 0, add_criterion_item)
        add_criterion_button = EdgeAddButton("+ Criterion", table)
        add_criterion_button.clicked.connect(self._add_criterion)
        table.setCellWidget(self._matrix_row_count() - 1, 0, add_criterion_button)
        for column in range(1, self._matrix_col_count()):
            filler = self._make_table_item("", role="filler")
            table.setItem(self._matrix_row_count() - 1, column, filler)
        table.blockSignals(False)
        self._building_matrix = False
        self._refresh_product_header_selection()
        self._refresh_criterion_header_selection()

    def _refresh_detail_panel(self) -> None:
        criterion = self._selected_criterion()
        product = self._selected_product()
        product_mode = self._detail_mode == "product" and product is not None
        self.detail_panel.criterion_label_edit.blockSignals(True)
        self.detail_panel.criterion_description_edit.blockSignals(True)
        self.detail_panel.criterion_type_combo.blockSignals(True)
        self.detail_panel.criterion_direction_combo.blockSignals(True)
        self.detail_panel.criterion_unit_edit.blockSignals(True)
        self.detail_panel.criterion_include_box.blockSignals(True)
        self.detail_panel.criterion_weight_slider.blockSignals(True)
        self.detail_panel.product_name_edit.blockSignals(True)
        self.detail_panel.product_color_edit.blockSignals(True)
        self.detail_panel.product_notes_edit.blockSignals(True)
        self.detail_panel.product_favorite_box.blockSignals(True)
        self.detail_panel.mode_label.setText("Editing product" if product_mode else "Editing criterion")
        self.detail_panel.title.setText(product.name if product_mode and product else criterion.label if criterion else "Selection")
        self.detail_panel.selected_product_label.setText(f"Product: {product.name if product else '-'}")
        self.detail_panel.selected_criterion_label.setText(
            f"Criterion: {criterion.label if (criterion and not product_mode) else '-'}"
        )
        self.detail_panel.product_name_edit.setText(product.name if product else "")
        self.detail_panel.product_color_edit.setText(product.color if product else "")
        self.detail_panel.product_notes_edit.setPlainText(product.notes if product else "")
        self.detail_panel.product_favorite_box.setChecked(product.favorite if product else False)
        product_color = self._product_accent(product)
        self._clear_product_gallery()
        if product:
            for image_path in product.image_paths or ([product.image_path] if product.image_path else []):
                self._append_gallery_item(product, image_path, image_path == product.image_path)
        if product and product.image_path:
            pixmap = QPixmap(product.image_path)
            if not pixmap.isNull():
                self.detail_panel.product_thumbnail.setPixmap(pixmap.scaled(360, 188, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.detail_panel.product_thumbnail.setText("")
                self.detail_panel.product_thumbnail.setStyleSheet("background:transparent; border:none; border-radius:18px; padding:0px;")
            else:
                self.detail_panel.product_thumbnail.setPixmap(QPixmap())
                self.detail_panel.product_thumbnail.setText("Image unavailable")
                self.detail_panel.product_thumbnail.setStyleSheet(
                    f"background:{product_color}2E; border:1px solid {product_color}88; border-radius:18px; color:{product_color}; font-weight:600; padding:8px;"
                )
        else:
            self.detail_panel.product_thumbnail.setPixmap(QPixmap())
            self.detail_panel.product_thumbnail.setText("No image")
            self.detail_panel.product_thumbnail.setStyleSheet(
                f"background:{product_color}2E; border:1px solid {product_color}88; border-radius:18px; color:{product_color}; font-weight:600; padding:8px;"
            )
        self.detail_panel.product_color_chip.setText("Color")
        self.detail_panel.product_color_chip.setStyleSheet(
            f"background:{product_color}22; color:{product_color}; border:1px solid {product_color}66; border-radius:10px; padding:4px 8px; font-weight:600;"
        )
        self.detail_panel.product_preview_card.setStyleSheet(
            f"QFrame#card {{ background: #162033; border:1px solid {product_color}44; border-radius:18px; }}"
        )
        self.detail_panel.product_identity_card.setStyleSheet("QFrame#subtlePanel { border-radius:18px; }")
        self.detail_panel.product_notes_edit.setStyleSheet(
            "QPlainTextEdit { background:#111722; border:1px solid #2a3852; border-radius:14px; padding:10px; color:#edf3ff; }"
        )
        self.detail_panel.product_image_btn.setStyleSheet(
            "QPushButton { background:#192436; border:1px solid #334767; border-radius:16px; padding:10px 14px; }"
        )
        self.detail_panel.product_remove_image_btn.setStyleSheet(
            "QPushButton { background:#192436; border:1px solid #334767; border-radius:16px; padding:10px 14px; }"
        )
        self.detail_panel.product_delete_btn.setStyleSheet(
            "QPushButton { background:#1b2231; border:1px solid #42506a; border-radius:16px; padding:10px 14px; }"
        )
        self.detail_panel.criterion_card.setStyleSheet("QFrame#subtlePanel { background:#162033; border:1px solid #2a3852; border-radius:18px; }")
        self.detail_panel.criterion_description_edit.setStyleSheet(
            "QPlainTextEdit { background:#111722; border:1px solid #2a3852; border-radius:14px; padding:10px; color:#edf3ff; }"
        )
        self.detail_panel.criterion_label_edit.setText(criterion.label if criterion else "")
        self.detail_panel.criterion_description_edit.setPlainText(criterion.description if criterion else "")
        self.detail_panel.criterion_type_combo.setCurrentText(criterion.type if criterion else "number")
        self.detail_panel.criterion_direction_combo.setCurrentText(criterion.direction if criterion else "high")
        self.detail_panel.criterion_unit_edit.setText(criterion.unit if criterion else "")
        self.detail_panel.criterion_include_box.setChecked(criterion.include_in_score if criterion else False)
        weight = int(round((criterion.weight if criterion else 1.0) * 100))
        self.detail_panel.criterion_weight_slider.setValue(weight)
        self.detail_panel.weight_value_label.setText(f"{(weight / 100):.2f}")
        criterion_enabled = criterion is not None and not product_mode
        product_enabled = product is not None and product_mode
        for widget in (
            self.detail_panel.product_name_edit,
            self.detail_panel.product_color_edit,
            self.detail_panel.product_notes_edit,
            self.detail_panel.product_favorite_box,
            self.detail_panel.product_image_btn,
            self.detail_panel.product_vision_btn,
            self.detail_panel.product_delete_btn,
        ):
            widget.setEnabled(product_enabled)
        self.detail_panel.product_thumbnail.setEnabled(product_enabled)
        self.detail_panel.product_gallery_scroll.setEnabled(product_enabled)
        self.detail_panel.product_remove_image_btn.setEnabled(product_enabled and product is not None and bool(product.image_path))
        self.detail_panel.selected_product_label.setVisible(not product_mode)
        self.detail_panel.selected_criterion_label.setVisible(not product_mode)
        for widget in (
            self.detail_panel.criterion_label_edit,
            self.detail_panel.criterion_description_edit,
            self.detail_panel.criterion_type_combo,
            self.detail_panel.criterion_direction_combo,
            self.detail_panel.criterion_unit_edit,
            self.detail_panel.criterion_include_box,
            self.detail_panel.criterion_weight_slider,
        ):
            widget.setEnabled(criterion_enabled)
        self.detail_panel.detail_stack.setCurrentIndex(0 if product_mode else 1)
        self._refresh_palette_selection(product_color if product_mode else None)
        self._refresh_product_header_selection()
        self._refresh_criterion_header_selection()
        self.detail_panel.criterion_label_edit.blockSignals(False)
        self.detail_panel.criterion_description_edit.blockSignals(False)
        self.detail_panel.criterion_type_combo.blockSignals(False)
        self.detail_panel.criterion_direction_combo.blockSignals(False)
        self.detail_panel.criterion_unit_edit.blockSignals(False)
        self.detail_panel.criterion_include_box.blockSignals(False)
        self.detail_panel.criterion_weight_slider.blockSignals(False)
        self.detail_panel.product_name_edit.blockSignals(False)
        self.detail_panel.product_color_edit.blockSignals(False)
        self.detail_panel.product_notes_edit.blockSignals(False)
        self.detail_panel.product_favorite_box.blockSignals(False)

    def _build_insight_segments(self, product: ProductRecord) -> list[tuple[str, float, str]]:
        numeric = [criterion for criterion in self.service.state.criteria if criterion.type == "number" and criterion.include_in_score]
        if not numeric:
            return []
        raw: list[tuple[str, float]] = []
        total = 0.0
        for criterion in numeric:
            weighted = 0.0
            try:
                current = float(self.service.cell_value(product.id, criterion.id))
                peer_values = []
                for peer in self.service.state.products:
                    try:
                        peer_values.append(float(self.service.cell_value(peer.id, criterion.id)))
                    except Exception:
                        continue
                if peer_values:
                    lo = min(peer_values)
                    hi = max(peer_values)
                    span = hi - lo
                    normalized = 1.0 if span == 0 else (current - lo) / span
                    if criterion.direction == "low":
                        normalized = 1.0 - normalized
                    weighted = max(0.0, normalized * max(criterion.weight, 0.01))
            except Exception:
                weighted = 0.0
            raw.append((criterion.label, weighted))
            total += weighted
        if total <= 0:
            equal = 1.0 / len(raw)
            return [(label, equal, DONUT_COLORS[index % len(DONUT_COLORS)]) for index, (label, _value) in enumerate(raw)]
        return [(label, value / total, DONUT_COLORS[index % len(DONUT_COLORS)]) for index, (label, value) in enumerate(raw)]

    def _refresh_compare_summary(self) -> None:
        products = self._display_products()
        if not products:
            self.compare_panel.subtitle.setText("No products")
            self.compare_panel.radar.set_data([], [], None)
            return
        numeric = [criterion for criterion in self.service.state.criteria if criterion.type == "number" and criterion.include_in_score]
        axes = [criterion.label for criterion in numeric]
        series = []
        for index, product in enumerate(products):
            values = []
            for criterion in numeric:
                try:
                    current = float(self.service.cell_value(product.id, criterion.id))
                    peers = [float(self.service.cell_value(peer.id, criterion.id)) for peer in products if self.service.cell_value(peer.id, criterion.id)]
                    lo = min(peers) if peers else current
                    hi = max(peers) if peers else current
                    span = hi - lo
                    normalized = 1.0 if span == 0 else (current - lo) / span
                    if criterion.direction == "low":
                        normalized = 1.0 - normalized
                    values.append(max(0.05, normalized))
                except Exception:
                    values.append(0.05)
            series.append((product.name, values, self._product_accent(product, index)))
        selected_name = self._selected_product().name if self._selected_product() else None
        if selected_name:
            self.compare_panel.subtitle.setText(f"Normalized multi-axis comparison. {selected_name} is highlighted.")
        else:
            self.compare_panel.subtitle.setText("Normalized multi-axis comparison across numeric criteria.")
        self.compare_panel.radar.set_data(axes, series, selected_name)

    def _refresh_header(self) -> None:
        self.asset_count_badge.setText(f"{len(self.service.state.products)} products / {len(self.service.state.criteria)} criteria")
        status, _mode = self.service.build_runtime_status()
        self.runtime_status_badge.setText(status)

    def _refresh_server_status(self) -> None:
        self.server_panel.server_runtime_label.setText(self.service.state.status_text)
        product = self._selected_product()
        error = product.vision_cache.error if product and product.vision_status == "error" else ""
        self.server_panel.server_last_error.setText(error or "No active issue.")

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
        if self._building_matrix or current_row < 0 or current_column < 0:
            return
        if self._is_data_cell(current_row, current_column):
            self._detail_mode = "criterion"
            self.service.select_cell(current_row - 1, current_column - 1)
        elif self._is_product_header(current_row, current_column):
            self._detail_mode = "product"
            product = self._product_for_col(current_column)
            self.service.state.selected_product_id = product.id if product else None
        elif self._is_criterion_header(current_row, current_column):
            self._detail_mode = "criterion"
            criterion = self._criterion_for_row(current_row)
            self.service.state.selected_criterion_id = criterion.id if criterion else None
        self._refresh_detail_panel()
        self._refresh_compare_summary()
        self._refresh_header()
        self._refresh_product_header_selection()

    def _handle_matrix_item_changed(self, item: QTableWidgetItem) -> None:
        if self._building_matrix:
            return
        row = item.row()
        column = item.column()
        if not self._is_data_cell(row, column):
            return
        criterion = self._criterion_for_row(row)
        product = self._product_for_col(column)
        if criterion is None or product is None:
            return
        text = item.text().strip()
        if criterion.unit and criterion.type == "number" and text.endswith(f" {criterion.unit}"):
            text = text[: -(len(criterion.unit) + 1)].rstrip()
        self.service.set_cell_value(product.id, criterion.id, text)
        self.service.recalculate_scores()
        self._refresh_all()

    def _commit_criterion_detail(self) -> None:
        criterion = self._selected_criterion()
        if criterion is None:
            return
        weight = self.detail_panel.criterion_weight_slider.value() / 100.0
        self.detail_panel.weight_value_label.setText(f"{weight:.2f}")
        self.service.update_criterion(
            criterion.id,
            label=self.detail_panel.criterion_label_edit.text().strip() or criterion.label,
            description=self.detail_panel.criterion_description_edit.toPlainText().strip(),
            data_type=self.detail_panel.criterion_type_combo.currentText(),
            weight=weight,
            direction=self.detail_panel.criterion_direction_combo.currentText(),
            unit=self.detail_panel.criterion_unit_edit.text().strip(),
            include_in_score=self.detail_panel.criterion_include_box.isChecked(),
        )
        self.service.autosave_project()
        self._rebuild_matrix()
        self._refresh_compare_summary()
        self._refresh_header()

    def _commit_product_detail(self) -> None:
        product = self._selected_product()
        if product is None or self._detail_mode != "product":
            return
        color = self.detail_panel.product_color_edit.text().strip()
        self.service.update_product(
            product.id,
            name=self.detail_panel.product_name_edit.text().strip() or product.name,
            color=color,
            notes=self.detail_panel.product_notes_edit.toPlainText().strip(),
            favorite=self.detail_panel.product_favorite_box.isChecked(),
        )
        self._rebuild_matrix()
        self._refresh_compare_summary()
        self._refresh_header()
        self._refresh_server_status()
        self._refresh_detail_panel()

    def _select_product_color(self, color: str) -> None:
        self.detail_panel.product_color_edit.setText(color)
        self._commit_product_detail()

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
        self.service.state.ollama_host = self.server_panel.ollama_host_edit.text().strip() or self.service.state.ollama_host
        self.service.state.vision_model = self.server_panel.vision_model_edit.text().strip() or self.service.state.vision_model
        self.service.state.classifier_model = self.server_panel.classifier_model_edit.text().strip() or self.service.state.classifier_model
        self.service.save_settings()
        self._refresh_server_status()

    def _new_project(self) -> None:
        dialog = TemplatePickerDialog(self.service.get_template_options(), self)
        if dialog.exec() != dialog.Accepted:
            return
        self.service.create_project_from_template(dialog.selected_template)
        self.service.ensure_project_registered()
        self._refresh_all()

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, APP_TITLE, str(self.service.projects_dir), f"VersusUp Project (*{PROJECT_EXTENSION})")
        if not path:
            return
        try:
            self.service.load_project(path)
            self._refresh_all()
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, str(exc))

    def _save_project(self) -> None:
        suggested = str(self.service.suggested_project_path())
        path, _ = QFileDialog.getSaveFileName(self, APP_TITLE, suggested, f"VersusUp Project (*{PROJECT_EXTENSION})")
        if not path:
            return
        if not path.endswith(PROJECT_EXTENSION):
            path += PROJECT_EXTENSION
        self.service.save_project(path)
        self._refresh_all()

    def _rename_project(self) -> None:
        dialog = TextEntryDialog("Rename Project", "Enter a clearer project name.", self.service.state.project_meta.name, self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.rename_current_project(dialog.value)
            self._refresh_all()
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, str(exc))

    def _duplicate_project(self) -> None:
        suggested = f"{self.service.state.project_meta.name} Copy"
        dialog = TextEntryDialog("Duplicate Project", "Create a backup copy with a new name.", suggested, self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.duplicate_current_project(dialog.value)
            self._refresh_all()
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, str(exc))

    def _export_report(self) -> None:
        path = self.service.export_report()
        self.service.state.status_text = f"Exported {path.name}"
        self._refresh_server_status()

    def _export_project_snapshot(self) -> None:
        path = self.service.build_project_snapshot_json()
        self.service.state.status_text = f"Exported {path.name}"
        self._refresh_server_status()

    def _save_preset(self) -> None:
        dialog = TextEntryDialog("Save Preset", "Store the current comparison structure as a reusable preset.", self.service.state.project_meta.name, self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.save_current_as_preset(dialog.value)
            self._refresh_all()
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, str(exc))

    def _remove_preset(self) -> None:
        item = self.history_panel.preset_list.currentItem()
        if item is None:
            return
        self.service.delete_preset(str(item.data(Qt.UserRole)))
        self._refresh_all()

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
        product = self._selected_product()
        if product is None:
            return
        self._attach_image_for(product.id)

    def _attach_image_for(self, product_id: str) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Attach Images", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if paths:
            self.service.attach_product_images(product_id, paths)
            self.service.state.selected_product_id = product_id
            self._refresh_all()

    def _select_gallery_image(self, item) -> None:
        product = self._selected_product()
        if product is None:
            return
        sender = self.sender()
        image_path = sender.property("imagePath") if sender is not None else ""
        if image_path:
            self.service.set_main_product_image(product.id, str(image_path))
            self._refresh_all()

    def _remove_selected_product_image(self) -> None:
        product = self._selected_product()
        if product is None or not product.image_path:
            return
        image_path = product.image_path
        if image_path:
            self.service.remove_product_image(product.id, image_path)
            self._refresh_all()

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
        product = self._selected_product()
        if product is None:
            return
        self._run_product_vision(product.id)

    def _run_product_vision(self, product_id: str) -> None:
        card = self._product_header_cards.get(product_id)
        point = card.mapToGlobal(card.rect().center()) if card is not None else QPoint(0, 0)
        self.service.state.selected_product_id = product_id
        self._on_product_hovered(product_id, point)

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
        path = Path(str(item.data(Qt.UserRole)))
        if path.exists():
            self.service.load_project(path)
            self._refresh_all()

    def _open_preset_item(self, item: QListWidgetItem) -> None:
        preset_id = str(item.data(Qt.UserRole))
        self.service.create_project_from_template(f"preset:{preset_id}")
        self.service.ensure_project_registered()
        self._refresh_all()

    def _start_vision_thread(self, product_id: str) -> None:
        if product_id in self._vision_threads:
            return
        thread = QThread(self)
        worker = VisionWorker(self.service, product_id)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_vision_finished)
        worker.failed.connect(self._on_vision_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(lambda pid=product_id: self._cleanup_vision_thread(pid))
        self._vision_threads[product_id] = (thread, worker)
        thread.start()

    def _on_product_hovered(self, product_id: str, global_pos: QPoint) -> None:
        product = self.service.product_by_id(product_id)
        if product is None:
            return
        self._popup_product_id = product_id
        self.vision_popup.move(global_pos + QPoint(18, 18))
        if not product.image_path:
            self.vision_popup.show_error(product.name, "Attach a product screenshot first.")
            return
        if product.vision_cache.status == "ready" and product.vision_cache.image_hash:
            self.vision_popup.show_ready(product)
            return
        self.vision_popup.show_loading(product.name)
        self._start_vision_thread(product_id)
        self._rebuild_matrix()

    def _clear_popup_product(self) -> None:
        self._popup_product_id = None

    def _cleanup_vision_thread(self, product_id: str) -> None:
        thread_worker = self._vision_threads.pop(product_id, None)
        if thread_worker:
            thread, worker = thread_worker
            worker.deleteLater()
            thread.deleteLater()
        self._rebuild_matrix()

    def _on_vision_finished(self, product_id: str, _cache) -> None:
        self._refresh_all()
        if self._popup_product_id == product_id:
            product = self.service.product_by_id(product_id)
            if product:
                self.vision_popup.show_ready(product)

    def _on_vision_failed(self, product_id: str, message: str) -> None:
        self._refresh_all()
        product = self.service.product_by_id(product_id)
        if self._popup_product_id == product_id and product:
            self.vision_popup.show_error(product.name, message)

    def _review_popup_product(self) -> None:
        if self._popup_product_id is None:
            return
        product = self.service.product_by_id(self._popup_product_id)
        if product is None:
            return
        dialog = ProposalReviewDialog(product.vision_cache.proposals, self)
        if dialog.exec() != QDialog.Accepted:
            return
        proposals = dialog.approved_proposals()
        applied = self.service.apply_vision_proposals(product.id, proposals)
        self._refresh_all()
        QMessageBox.information(self, APP_TITLE, "\n".join(applied) if applied else "No proposal was applied.")

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
