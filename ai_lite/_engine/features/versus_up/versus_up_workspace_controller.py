from __future__ import annotations

from contexthub.ui.qt.shell import get_shell_palette

try:
    from PySide6.QtCore import QPoint
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for versus_up.") from exc


def sync_selection_from_product_list(window) -> None:
    product_id = window.service.state.selected_product_id or (window.service.state.products[0].id if window.service.state.products else None)
    if product_id is None:
        return
    window.service.state.selected_product_id = product_id
    product_index = next((i for i, product in enumerate(window._display_products()) if product.id == product_id), 0)
    row = next((i for i, criterion in enumerate(window.service.state.criteria) if criterion.id == window.service.state.selected_criterion_id), 0)
    if window.service.state.criteria:
        window.workspace_panel.matrix_table.setCurrentCell(row + 1, product_index + 1)
    window._refresh_detail_panel()
    window._refresh_server_status()


def refresh_palette_selection(window, selected_color: str | None) -> None:
    normalized = (selected_color or "").lower()
    palette = get_shell_palette()
    for button in window.detail_panel.product_color_buttons:
        color = str(button.property("swatchColor"))
        is_selected = color.lower() == normalized
        button.setStyleSheet(
            f"background:{color}; border:{'3px solid ' + palette.text if is_selected else '1px solid ' + color}; "
            f"border-radius:17px; {'padding:1px;' if is_selected else ''}"
        )


def select_product_header(window, column: int, product_id: str) -> None:
    window.service.state.selected_product_id = product_id
    window._detail_mode = "product"
    window.workspace_panel.matrix_table.setCurrentCell(0, column)


def rename_product(window, product_id: str, value: str) -> None:
    product = window.service.product_by_id(product_id)
    if product is None:
        return
    window.service.update_product(product_id, name=value.strip() or product.name)
    window._refresh_all()


def rename_criterion(window, criterion_id: str, value: str) -> None:
    criterion = window.service.criterion_by_id(criterion_id)
    if criterion is None:
        return
    window.service.update_criterion(criterion_id, label=value.strip() or criterion.label)
    window._refresh_all()


def toggle_product_favorite(window, product_id: str, favorite: bool) -> None:
    window.service.update_product(product_id, favorite=favorite)
    window._refresh_all()


def delete_product_from_header(window, product_id: str) -> None:
    window.service.remove_product(product_id)
    window._refresh_all()


def add_criterion(window) -> None:
    window.service.add_criterion(description="Describe how this field should be judged.")
    window._refresh_all()


def remove_selected_criterion(window) -> None:
    criterion = window._selected_criterion()
    if criterion is None:
        return
    window.service.remove_criterion(criterion.id)
    window._refresh_all()


def open_detail_for_cell(window, row: int, column: int) -> None:
    table = window.workspace_panel.matrix_table
    if row < 0 or column < 0:
        return
    table.setCurrentCell(row, column)
    product = window._product_for_col(column) if column > 0 else None
    criterion = window._criterion_for_row(row) if row > 0 else None
    window._vision_focus_product_id = product.id if product else window.service.state.selected_product_id
    window._vision_focus_criterion_id = criterion.id if criterion else window.service.state.selected_criterion_id
    window._open_detail_dialog()


def open_detail_from_matrix_cell(window, row: int, column: int) -> None:
    open_detail_for_cell(window, row, column)


def open_detail_from_context_menu(window, pos: QPoint) -> None:
    index = window.workspace_panel.matrix_table.indexAt(pos)
    if not index.isValid():
        return
    open_detail_for_cell(window, index.row(), index.column())
