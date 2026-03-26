from __future__ import annotations

from contexthub.ui.qt.shell import get_shell_palette
from features.versus_up.versus_up_qt_widgets import DONUT_COLORS, CriterionMatrixCellWidget, EdgeAddButton, ProductMatrixCellWidget

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPixmap
    from PySide6.QtWidgets import QTableWidgetItem
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for versus_up.") from exc


def matrix_row_count(window) -> int:
    return len(window.service.state.criteria) + 2


def matrix_col_count(window) -> int:
    return len(window.service.state.products) + 2


def is_data_cell(window, row: int, column: int) -> bool:
    return 0 < row < matrix_row_count(window) - 1 and 0 < column < matrix_col_count(window) - 1


def is_product_header(window, row: int, column: int) -> bool:
    return row == 0 and 0 < column < matrix_col_count(window) - 1


def is_criterion_header(window, row: int, column: int) -> bool:
    return column == 0 and 0 < row < matrix_row_count(window) - 1


def criterion_for_row(window, row: int):
    if not is_criterion_header(window, row, 0) and not (0 < row < matrix_row_count(window) - 1):
        return None
    return window.service.state.criteria[row - 1]


def product_for_col(window, column: int):
    if not is_product_header(window, 0, column) and not (0 < column < matrix_col_count(window) - 1):
        return None
    products = window._display_products()
    return products[column - 1] if 0 <= column - 1 < len(products) else None


def display_cell_value(window, product_id: str, criterion) -> str:
    raw = window.service.cell_value(product_id, criterion.id)
    if raw and criterion.unit and criterion.type == "number":
        return f"{raw} {criterion.unit}"
    return raw


def make_table_item(window, text: str, *, role: str, raw_value: str = "", criterion=None) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignCenter)
    item.setData(Qt.UserRole, role)
    if raw_value:
        item.setData(Qt.UserRole + 1, raw_value)
    if criterion is not None:
        item.setToolTip(f"{criterion.label}\n{criterion.description or 'No description'}\nWeight: {criterion.weight:.2f} / {criterion.direction}")
    return item


def apply_data_cell_style(window, item: QTableWidgetItem, criterion, raw_value: str) -> None:
    palette = get_shell_palette()
    item.setForeground(Qt.white)
    if criterion.type == "number" and criterion.include_in_score:
        values = []
        for product in window._display_products():
            try:
                values.append(float(window.service.cell_value(product.id, criterion.id)))
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


def rebuild_matrix(window) -> None:
    table = window.workspace_panel.matrix_table
    window._building_matrix = True
    table.blockSignals(True)
    table.clear()
    table.setRowCount(matrix_row_count(window))
    table.setColumnCount(matrix_col_count(window))
    window._product_header_cards = {}
    window._criterion_header_cards = {}
    window.workspace_panel.matrix_context_label.setText(f"{window.service.state.project_meta.name} / {window.service.state.project_meta.category}")
    products = window._display_products()
    product_count = max(1, len(products))
    product_width = 196 if product_count <= 2 else 170 if product_count <= 4 else 152
    for row in range(matrix_row_count(window)):
        table.setRowHeight(row, 158 if row == 0 else 56)
    for column in range(matrix_col_count(window)):
        if column == 0:
            table.setColumnWidth(column, 250)
        elif column == matrix_col_count(window) - 1:
            table.setColumnWidth(column, 110)
        else:
            table.setColumnWidth(column, product_width)
    table.setItem(0, 0, make_table_item(window, "Criteria / Products", role="corner"))
    for product_index, product in enumerate(products, start=1):
        table.setItem(0, product_index, make_table_item(window, "", role="product_header"))
        widget = ProductMatrixCellWidget(product.id, table)
        accent = product.color or DONUT_COLORS[(product_index - 1) % len(DONUT_COLORS)]
        widget.set_product(product, window.service.state.scores.get(product.id, 0.0), accent)
        widget.selected.connect(lambda product_id, column=product_index: window._select_product_header(column, product_id))
        table.setCellWidget(0, product_index, widget)
        window._product_header_cards[product.id] = widget
    table.setItem(0, matrix_col_count(window) - 1, make_table_item(window, "", role="add_product"))
    add_product_button = EdgeAddButton("+ Product", table)
    add_product_button.clicked.connect(window._add_product)
    table.setCellWidget(0, matrix_col_count(window) - 1, add_product_button)
    for row_index, criterion in enumerate(window.service.state.criteria, start=1):
        table.setItem(row_index, 0, make_table_item(window, "", role="criterion_header", criterion=criterion))
        criterion_widget = CriterionMatrixCellWidget(criterion.id, table)
        criterion_widget.set_criterion(criterion)
        table.setCellWidget(row_index, 0, criterion_widget)
        window._criterion_header_cards[criterion.id] = criterion_widget
        for col_index, product in enumerate(products, start=1):
            raw = window.service.cell_value(product.id, criterion.id)
            data_item = make_table_item(window, display_cell_value(window, product.id, criterion), role="data", raw_value=raw, criterion=criterion)
            apply_data_cell_style(window, data_item, criterion, raw)
            table.setItem(row_index, col_index, data_item)
        table.setItem(row_index, matrix_col_count(window) - 1, make_table_item(window, "", role="filler"))
    table.setItem(matrix_row_count(window) - 1, 0, make_table_item(window, "", role="add_criterion"))
    add_criterion_button = EdgeAddButton("+ Criterion", table)
    add_criterion_button.clicked.connect(window._add_criterion)
    table.setCellWidget(matrix_row_count(window) - 1, 0, add_criterion_button)
    for column in range(1, matrix_col_count(window)):
        table.setItem(matrix_row_count(window) - 1, column, make_table_item(window, "", role="filler"))
    table.blockSignals(False)
    window._building_matrix = False
    window._refresh_product_header_selection()
    window._refresh_criterion_header_selection()


def refresh_detail_panel(window) -> None:
    criterion = window._selected_criterion()
    product = window._selected_product()
    product_mode = window._detail_mode == "product" and product is not None
    panel = window.detail_panel
    for widget in (
        panel.criterion_label_edit,
        panel.criterion_description_edit,
        panel.criterion_type_combo,
        panel.criterion_direction_combo,
        panel.criterion_unit_edit,
        panel.criterion_include_box,
        panel.criterion_weight_slider,
        panel.product_name_edit,
        panel.product_color_edit,
        panel.product_notes_edit,
        panel.product_favorite_box,
    ):
        widget.blockSignals(True)
    panel.mode_label.setText("Editing product" if product_mode else "Editing criterion")
    panel.title.setText(product.name if product_mode and product else criterion.label if criterion else "Selection")
    panel.selected_product_label.setText(f"Product: {product.name if product else '-'}")
    panel.selected_criterion_label.setText(f"Criterion: {criterion.label if (criterion and not product_mode) else '-'}")
    panel.product_name_edit.setText(product.name if product else "")
    panel.product_color_edit.setText(product.color if product else "")
    panel.product_notes_edit.setPlainText(product.notes if product else "")
    panel.product_favorite_box.setChecked(product.favorite if product else False)
    product_color = window._product_accent(product)
    window._clear_product_gallery()
    if product:
        for image_path in product.image_paths or ([product.image_path] if product.image_path else []):
            window._append_gallery_item(product, image_path, image_path == product.image_path)
    if product and product.image_path:
        pixmap = QPixmap(product.image_path)
        if not pixmap.isNull():
            panel.product_thumbnail.setPixmap(pixmap.scaled(360, 188, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            panel.product_thumbnail.setText("")
            panel.product_thumbnail.setStyleSheet("background:transparent; border:none; border-radius:18px; padding:0px;")
        else:
            panel.product_thumbnail.setPixmap(QPixmap())
            panel.product_thumbnail.setText("Image unavailable")
            panel.product_thumbnail.setStyleSheet(f"background:{product_color}2E; border:1px solid {product_color}88; border-radius:18px; color:{product_color}; font-weight:600; padding:8px;")
    else:
        panel.product_thumbnail.setPixmap(QPixmap())
        panel.product_thumbnail.setText("No image")
        panel.product_thumbnail.setStyleSheet(f"background:{product_color}2E; border:1px solid {product_color}88; border-radius:18px; color:{product_color}; font-weight:600; padding:8px;")
    panel.product_color_chip.setText("Color")
    panel.product_color_chip.setStyleSheet(f"background:{product_color}22; color:{product_color}; border:1px solid {product_color}66; border-radius:10px; padding:4px 8px; font-weight:600;")
    panel.product_preview_card.setStyleSheet(f"QFrame#card {{ background: #162033; border:1px solid {product_color}44; border-radius:18px; }}")
    panel.product_identity_card.setStyleSheet("QFrame#subtlePanel { border-radius:18px; }")
    panel.product_notes_edit.setStyleSheet("QPlainTextEdit { background:#111722; border:1px solid #2a3852; border-radius:14px; padding:10px; color:#edf3ff; }")
    panel.product_image_btn.setStyleSheet("QPushButton { background:#192436; border:1px solid #334767; border-radius:16px; padding:10px 14px; }")
    panel.product_remove_image_btn.setStyleSheet("QPushButton { background:#192436; border:1px solid #334767; border-radius:16px; padding:10px 14px; }")
    panel.product_delete_btn.setStyleSheet("QPushButton { background:#1b2231; border:1px solid #42506a; border-radius:16px; padding:10px 14px; }")
    panel.criterion_card.setStyleSheet("QFrame#subtlePanel { background:#162033; border:1px solid #2a3852; border-radius:18px; }")
    panel.criterion_description_edit.setStyleSheet("QPlainTextEdit { background:#111722; border:1px solid #2a3852; border-radius:14px; padding:10px; color:#edf3ff; }")
    panel.criterion_label_edit.setText(criterion.label if criterion else "")
    panel.criterion_description_edit.setPlainText(criterion.description if criterion else "")
    panel.criterion_type_combo.setCurrentText(criterion.type if criterion else "number")
    panel.criterion_direction_combo.setCurrentText(criterion.direction if criterion else "high")
    panel.criterion_unit_edit.setText(criterion.unit if criterion else "")
    panel.criterion_include_box.setChecked(criterion.include_in_score if criterion else False)
    weight = int(round((criterion.weight if criterion else 1.0) * 100))
    panel.criterion_weight_slider.setValue(weight)
    panel.weight_value_label.setText(f"{(weight / 100):.2f}")
    criterion_enabled = criterion is not None and not product_mode
    product_enabled = product is not None and product_mode
    for widget in (panel.product_name_edit, panel.product_color_edit, panel.product_notes_edit, panel.product_favorite_box, panel.product_image_btn, panel.product_vision_btn, panel.product_delete_btn):
        widget.setEnabled(product_enabled)
    panel.product_thumbnail.setEnabled(product_enabled)
    panel.product_gallery_scroll.setEnabled(product_enabled)
    panel.product_remove_image_btn.setEnabled(product_enabled and product is not None and bool(product.image_path))
    panel.selected_product_label.setVisible(not product_mode)
    panel.selected_criterion_label.setVisible(not product_mode)
    for widget in (panel.criterion_label_edit, panel.criterion_description_edit, panel.criterion_type_combo, panel.criterion_direction_combo, panel.criterion_unit_edit, panel.criterion_include_box, panel.criterion_weight_slider):
        widget.setEnabled(criterion_enabled)
    panel.detail_stack.setCurrentIndex(0 if product_mode else 1)
    window._refresh_palette_selection(product_color if product_mode else None)
    window._refresh_product_header_selection()
    window._refresh_criterion_header_selection()
    for widget in (
        panel.criterion_label_edit,
        panel.criterion_description_edit,
        panel.criterion_type_combo,
        panel.criterion_direction_combo,
        panel.criterion_unit_edit,
        panel.criterion_include_box,
        panel.criterion_weight_slider,
        panel.product_name_edit,
        panel.product_color_edit,
        panel.product_notes_edit,
        panel.product_favorite_box,
    ):
        widget.blockSignals(False)


def refresh_compare_summary(window) -> None:
    products = window._display_products()
    if not products:
        window.compare_panel.subtitle.setText("No products")
        window.compare_panel.radar.set_data([], [], None)
        return
    numeric = [criterion for criterion in window.service.state.criteria if criterion.type == "number" and criterion.include_in_score]
    axes = [criterion.label for criterion in numeric]
    series = []
    for index, product in enumerate(products):
        values = []
        for criterion in numeric:
            try:
                current = float(window.service.cell_value(product.id, criterion.id))
                peers = [float(window.service.cell_value(peer.id, criterion.id)) for peer in products if window.service.cell_value(peer.id, criterion.id)]
                lo = min(peers) if peers else current
                hi = max(peers) if peers else current
                span = hi - lo
                normalized = 1.0 if span == 0 else (current - lo) / span
                if criterion.direction == "low":
                    normalized = 1.0 - normalized
                values.append(max(0.05, normalized))
            except Exception:
                values.append(0.05)
        series.append((product.name, values, window._product_accent(product, index)))
    selected_name = window._selected_product().name if window._selected_product() else None
    window.compare_panel.subtitle.setText(
        f"Normalized multi-axis comparison. {selected_name} is highlighted." if selected_name else "Normalized multi-axis comparison across numeric criteria."
    )
    window.compare_panel.radar.set_data(axes, series, selected_name)


def refresh_header(window) -> None:
    window.asset_count_badge.setText(f"{len(window.service.state.products)} products / {len(window.service.state.criteria)} criteria")
    status, _mode = window.service.build_runtime_status()
    window.runtime_status_badge.setText(status)


def refresh_server_status(window) -> None:
    window.server_panel.server_runtime_label.setText(window.service.state.status_text)
    product = window._selected_product()
    error = product.vision_cache.error if product and product.vision_status == "error" else ""
    window.server_panel.server_last_error.setText(error or "No active issue.")


def sync_selection_from_table(window, current_row: int, current_column: int, _previous_row: int, _previous_column: int) -> None:
    if window._building_matrix or current_row < 0 or current_column < 0:
        return
    if is_data_cell(window, current_row, current_column):
        window._detail_mode = "criterion"
        window.service.select_cell(current_row - 1, current_column - 1)
    elif is_product_header(window, current_row, current_column):
        window._detail_mode = "product"
        product = product_for_col(window, current_column)
        window.service.state.selected_product_id = product.id if product else None
    elif is_criterion_header(window, current_row, current_column):
        window._detail_mode = "criterion"
        criterion = criterion_for_row(window, current_row)
        window.service.state.selected_criterion_id = criterion.id if criterion else None
    refresh_detail_panel(window)
    refresh_compare_summary(window)
    refresh_header(window)
    window._refresh_product_header_selection()


def handle_matrix_item_changed(window, item: QTableWidgetItem) -> None:
    if window._building_matrix:
        return
    row = item.row()
    column = item.column()
    if not is_data_cell(window, row, column):
        return
    criterion = criterion_for_row(window, row)
    product = product_for_col(window, column)
    if criterion is None or product is None:
        return
    text = item.text().strip()
    if criterion.unit and criterion.type == "number" and text.endswith(f" {criterion.unit}"):
        text = text[: -(len(criterion.unit) + 1)].rstrip()
    window.service.set_cell_value(product.id, criterion.id, text)
    window.service.recalculate_scores()
    window._refresh_all()


def commit_criterion_detail(window) -> None:
    criterion = window._selected_criterion()
    if criterion is None:
        return
    weight = window.detail_panel.criterion_weight_slider.value() / 100.0
    window.detail_panel.weight_value_label.setText(f"{weight:.2f}")
    window.service.update_criterion(
        criterion.id,
        label=window.detail_panel.criterion_label_edit.text().strip() or criterion.label,
        description=window.detail_panel.criterion_description_edit.toPlainText().strip(),
        data_type=window.detail_panel.criterion_type_combo.currentText(),
        weight=weight,
        direction=window.detail_panel.criterion_direction_combo.currentText(),
        unit=window.detail_panel.criterion_unit_edit.text().strip(),
        include_in_score=window.detail_panel.criterion_include_box.isChecked(),
    )
    window.service.autosave_project()
    rebuild_matrix(window)
    refresh_compare_summary(window)
    refresh_header(window)


def commit_product_detail(window) -> None:
    product = window._selected_product()
    if product is None or window._detail_mode != "product":
        return
    color = window.detail_panel.product_color_edit.text().strip()
    window.service.update_product(
        product.id,
        name=window.detail_panel.product_name_edit.text().strip() or product.name,
        color=color,
        notes=window.detail_panel.product_notes_edit.toPlainText().strip(),
        favorite=window.detail_panel.product_favorite_box.isChecked(),
    )
    rebuild_matrix(window)
    refresh_compare_summary(window)
    refresh_header(window)
    refresh_server_status(window)
    refresh_detail_panel(window)


def select_product_color(window, color: str) -> None:
    window.detail_panel.product_color_edit.setText(color)
    commit_product_detail(window)
