from __future__ import annotations

from contexthub.ui.qt.shell import build_shell_stylesheet, get_shell_accent_cycle, get_shell_palette
from features.versus_up.versus_up_state import CriterionRecord, ProductRecord, VisionProposal

try:
    from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPoint, QRectF, Qt, Signal
    from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError("PySide6 is required for versus_up.") from exc

def donut_colors() -> list[str]:
    return get_shell_accent_cycle()[:6]


DONUT_COLORS = donut_colors()


def alpha_hex(color_value: str, alpha: int) -> str:
    color = QColor(color_value)
    color.setAlpha(max(0, min(255, alpha)))
    return color.name(QColor.HexArgb)


class TextEntryDialog(QDialog):
    def __init__(self, title: str, prompt: str, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.value = value

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        prompt_label = QLabel(prompt)
        prompt_label.setWordWrap(True)
        self.input_edit = QLineEdit(value)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        ok_btn = QPushButton("OK")
        ok_btn.setProperty("buttonRole", "primary")
        cancel_btn.clicked.connect(self.reject)
        ok_btn.clicked.connect(self._accept_value)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(ok_btn)

        outer.addWidget(title_label)
        outer.addWidget(prompt_label)
        outer.addWidget(self.input_edit)
        outer.addLayout(buttons)

    def _accept_value(self) -> None:
        text = self.input_edit.text().strip()
        self.value = text or self.value
        self.accept()


class HoverProductList(QListWidget):
    product_hovered = Signal(str, QPoint)
    hover_left = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setMouseTracking(True)
        self._last_hovered: str | None = None

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        item = self.itemAt(event.pos())
        product_id = item.data(Qt.UserRole) if item else None
        if product_id and product_id != self._last_hovered:
            self._last_hovered = product_id
            self.product_hovered.emit(str(product_id), self.viewport().mapToGlobal(event.pos()))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._last_hovered = None
        self.hover_left.emit()
        super().leaveEvent(event)


class MatrixTableModel(QAbstractTableModel):
    def __init__(self, service) -> None:
        super().__init__()
        self.service = service
        self.header_rows = 1
        self.header_cols = 1

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.service.state.criteria) + self.header_rows + 1

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.service.state.products) + self.header_cols + 1

    def is_corner_cell(self, row: int, column: int) -> bool:
        return row == 0 and column == 0

    def is_product_header(self, row: int, column: int) -> bool:
        return row == 0 and 0 < column < self.columnCount() - 1

    def is_criterion_header(self, row: int, column: int) -> bool:
        return column == 0 and 0 < row < self.rowCount() - 1

    def is_add_product_cell(self, row: int, column: int) -> bool:
        return row == 0 and column == self.columnCount() - 1

    def is_add_criterion_cell(self, row: int, column: int) -> bool:
        return column == 0 and row == self.rowCount() - 1

    def is_data_cell(self, row: int, column: int) -> bool:
        return 0 < row < self.rowCount() - 1 and 0 < column < self.columnCount() - 1

    def criterion_at_row(self, row: int):
        if 0 < row < self.rowCount() - 1:
            return self.service.state.criteria[row - 1]
        return None

    def product_at_column(self, column: int):
        if 0 < column < self.columnCount() - 1:
            return self.service.state.products[column - 1]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None
        row = index.row()
        column = index.column()
        if self.is_corner_cell(row, column):
            if role == Qt.DisplayRole:
                return "Criteria / Products"
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return None
        if self.is_add_product_cell(row, column):
            if role == Qt.DisplayRole:
                return "+ Product"
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            if role == Qt.ToolTipRole:
                return "Add a new product column"
            return None
        if self.is_add_criterion_cell(row, column):
            if role == Qt.DisplayRole:
                return "+ Criterion"
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            if role == Qt.ToolTipRole:
                return "Add a new criterion row"
            return None
        if self.is_product_header(row, column):
            product = self.product_at_column(column)
            if product is None:
                return None
            palette = get_shell_palette()
            if role == Qt.DisplayRole:
                return f"{product.name}\n{self.service.state.scores.get(product.id, 0.0):.2f}"
            if role == Qt.ToolTipRole:
                return product.vision_summary or "Product header"
            if role == Qt.BackgroundRole:
                return QColor(palette.card_bg)
            return None
        if self.is_criterion_header(row, column):
            criterion = self.criterion_at_row(row)
            if criterion is None:
                return None
            palette = get_shell_palette()
            meta = []
            if criterion.unit:
                meta.append(criterion.unit)
            meta.append(criterion.direction)
            meta.append(f"W {criterion.weight:.1f}")
            if role == Qt.DisplayRole:
                return f"{criterion.label}\n{' • '.join(meta)}"
            if role == Qt.ToolTipRole:
                desc = criterion.description.strip() or "No description"
                return f"{criterion.label}\n{desc}"
            if role == Qt.TextAlignmentRole:
                return Qt.AlignLeft | Qt.AlignVCenter
            if role == Qt.BackgroundRole:
                return QColor(palette.card_bg)
            return None
        if not self.is_data_cell(row, column):
            return None
        criterion = self.service.state.criteria[row - 1]
        product = self.service.state.products[column - 1]
        value = self.service.cell_value(product.id, criterion.id)
        if role == Qt.DisplayRole:
            if value and criterion.unit and criterion.type == "number":
                return f"{value} {criterion.unit}"
            return value
        if role == Qt.EditRole:
            return value
        if role == Qt.ToolTipRole:
            desc = criterion.description.strip() or "No description"
            return f"{criterion.label}\n{desc}\nWeight: {criterion.weight:.2f} / {criterion.direction}"
        if role == Qt.BackgroundRole:
            palette = get_shell_palette()
            if self.is_corner_cell(row, column) or self.is_product_header(row, column) or self.is_criterion_header(row, column):
                return QColor(palette.card_bg)
            if self.is_add_product_cell(row, column) or self.is_add_criterion_cell(row, column):
                return QColor(palette.control_bg)
        if role == Qt.BackgroundRole and criterion.type == "number" and criterion.include_in_score:
            palette = get_shell_palette()
            values: list[float] = []
            for candidate in self.service.state.products:
                try:
                    values.append(float(self.service.cell_value(candidate.id, criterion.id)))
                except Exception:
                    continue
            if values:
                try:
                    current = float(value)
                except Exception:
                    return None
                best = max(values) if criterion.direction == "high" else min(values)
                worst = min(values) if criterion.direction == "high" else max(values)
                if current == best:
                    return QColor(palette.success)
                if current == worst and len(values) > 1:
                    return QColor(palette.error)
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole):  # noqa: N802
        if role != Qt.EditRole or not index.isValid() or not self.is_data_cell(index.row(), index.column()):
            return False
        criterion = self.service.state.criteria[index.row() - 1]
        product = self.service.state.products[index.column() - 1]
        self.service.set_cell_value(product.id, criterion.id, str(value))
        self.service.recalculate_scores()
        self.refresh()
        return True

    def flags(self, index: QModelIndex):  # noqa: N802
        if not index.isValid():
            return Qt.ItemIsEnabled
        if self.is_data_cell(index.row(), index.column()):
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        if self.is_product_header(index.row(), index.column()) or self.is_criterion_header(index.row(), index.column()):
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if self.is_add_product_cell(index.row(), index.column()) or self.is_add_criterion_cell(index.row(), index.column()):
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # noqa: N802
        return None

    def refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()


class VisionWorker(QObject):
    finished = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, service, product_id: str) -> None:
        super().__init__()
        self.service = service
        self.product_id = product_id

    def run(self) -> None:
        try:
            cache = self.service.analyze_product_image(self.product_id)
            self.finished.emit(self.product_id, cache)
        except Exception as exc:
            self.service.set_vision_error(self.product_id, str(exc))
            self.failed.emit(self.product_id, str(exc))


class VisionPopup(QDialog):
    apply_requested = Signal()
    dismissed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setModal(False)
        self.setMinimumWidth(360)
        self.setStyleSheet(build_shell_stylesheet())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        chrome = QHBoxLayout()
        self.title = QLabel("Vision")
        self.title.setObjectName("sectionTitle")
        chrome.addWidget(self.title)
        chrome.addStretch(1)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self._dismiss)
        chrome.addWidget(self.close_btn)
        self.status = QLabel("")

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole):  # noqa: N802
        if role != Qt.EditRole or not index.isValid() or not self.is_data_cell(index.row(), index.column()):
            return False
        criterion = self.service.state.criteria[index.row() - 1]
        product = self.service.state.products[index.column() - 1]
        self.service.set_cell_value(product.id, criterion.id, str(value))
        self.service.recalculate_scores()
        self.refresh()
        return True

    def flags(self, index: QModelIndex):  # noqa: N802
        if not index.isValid():
            return Qt.ItemIsEnabled
        if self.is_data_cell(index.row(), index.column()):
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        if self.is_product_header(index.row(), index.column()) or self.is_criterion_header(index.row(), index.column()):
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if self.is_add_product_cell(index.row(), index.column()) or self.is_add_criterion_cell(index.row(), index.column()):
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # noqa: N802
        return None

    def refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()


class VisionWorker(QObject):
    finished = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, service, product_id: str) -> None:
        super().__init__()
        self.service = service
        self.product_id = product_id

    def run(self) -> None:
        try:
            cache = self.service.analyze_product_image(self.product_id)
            self.finished.emit(self.product_id, cache)
        except Exception as exc:
            self.service.set_vision_error(self.product_id, str(exc))
            self.failed.emit(self.product_id, str(exc))


class VisionPopup(QDialog):
    apply_requested = Signal()
    dismissed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setModal(False)
        self.setMinimumWidth(360)
        self.setStyleSheet(build_shell_stylesheet())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        chrome = QHBoxLayout()
        self.title = QLabel("Vision")
        self.title.setObjectName("sectionTitle")
        chrome.addWidget(self.title)
        chrome.addStretch(1)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self._dismiss)
        chrome.addWidget(self.close_btn)
        self.status = QLabel("")
        self.status.setObjectName("eyebrow")
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.raw_text = QLabel("")
        self.raw_text.setObjectName("muted")
        self.raw_text.setWordWrap(True)
        self.apply_btn = QPushButton("Review proposals")
        self.apply_btn.setProperty("buttonRole", "primary")
        self.apply_btn.clicked.connect(self.apply_requested.emit)
        layout.addLayout(chrome)
        layout.addWidget(self.status)
        layout.addWidget(self.summary)
        layout.addWidget(self.raw_text)
        layout.addWidget(self.apply_btn)
        outer.addWidget(card)

    def _dismiss(self) -> None:
        self.hide()
        self.dismissed.emit()

    def show_loading(self, product_name: str) -> None:
        self.title.setText(product_name)
        self.status.setText("Analyzing screenshot with Ollama Vision...")
        self.summary.setText("OCR/VQA is running on hover.")
        self.raw_text.setText("")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setVisible(False)
        self.show()

    def show_error(self, product_name: str, message: str) -> None:
        self.title.setText(product_name)
        self.status.setText("Vision failed")
        self.summary.setText(message)
        self.raw_text.setText("")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setVisible(False)
        self.show()

    def show_ready(self, product: ProductRecord) -> None:
        self.title.setText(product.name)
        self.status.setText("Vision ready")
        self.summary.setText(product.vision_cache.summary or "No summary returned.")
        raw = product.vision_cache.raw_text.strip()
        self.raw_text.setText(raw[:260] + ("..." if len(raw) > 260 else ""))
        has_proposals = bool(product.vision_cache.proposals)
        self.apply_btn.setEnabled(has_proposals)
        self.apply_btn.setVisible(has_proposals)
        self.show()


class ProposalReviewDialog(QDialog):
    def __init__(self, proposals: list[VisionProposal], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Review Vision Proposals")
        self.resize(860, 420)
        self.setStyleSheet(build_shell_stylesheet())
        self.proposals = proposals
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        headline = QLabel("Apply OCR/VQA results to the comparison matrix")
        headline.setObjectName("sectionTitle")
        hint = QLabel("Approve which proposals replace existing criteria or add new criteria.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(headline)
        layout.addWidget(hint)
        self.table = QTableWidget(len(proposals), 6)
        self.table.setHorizontalHeaderLabels(["Use", "Action", "Criterion", "Value", "Confidence", "Reason"])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        for row, proposal in enumerate(proposals):
            use_box = QCheckBox()
            use_box.setChecked(True)
            self.table.setCellWidget(row, 0, use_box)
            action_combo = QComboBox()
            action_combo.addItems(["replace", "add"])
            action_combo.setCurrentText("add" if proposal.action == "add" or proposal.criterion_id is None else "replace")
            self.table.setCellWidget(row, 1, action_combo)
            self.table.setItem(row, 2, QTableWidgetItem(proposal.criterion_name))
            self.table.setItem(row, 3, QTableWidgetItem(proposal.value))
            self.table.setItem(row, 4, QTableWidgetItem(f"{proposal.confidence:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(proposal.reason))
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        apply_btn = QPushButton("Apply")
        apply_btn.setProperty("buttonRole", "primary")
        cancel_btn.clicked.connect(self.reject)
        apply_btn.clicked.connect(self.accept)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(apply_btn)
        layout.addLayout(buttons)

    def approved_proposals(self) -> list[VisionProposal]:
        approved: list[VisionProposal] = []
        for row, proposal in enumerate(self.proposals):
            proposal.approved = bool(self.table.cellWidget(row, 0).isChecked())  # type: ignore[union-attr]
            proposal.action = str(self.table.cellWidget(row, 1).currentText())  # type: ignore[union-attr]
            proposal.criterion_name = self.table.item(row, 2).text()
            proposal.value = self.table.item(row, 3).text()
            approved.append(proposal)
        return approved


class DonutWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[tuple[str, float, str]] = []
        self.center_text = "No data"
        self.setMinimumSize(140, 140)

    def set_segments(self, values: list[tuple[str, float, str]], center_text: str) -> None:
        self.values = values
        self.center_text = center_text
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        palette = get_shell_palette()
        rect = QRectF(12, 12, self.width() - 24, self.height() - 24)
        painter.setPen(QPen(QColor(palette.control_bg), 14))
        painter.drawArc(rect, 0, 360 * 16)
        if self.values:
            start = 90 * 16
            for index, (_label, value, color) in enumerate(self.values):
                span = -max(1, int(360 * 16 * value))
                colors = donut_colors()
                painter.setPen(QPen(QColor(color or colors[index % len(colors)]), 14))
                painter.drawArc(rect, start, span)
                start += span
        painter.setPen(QColor(palette.text))
        painter.drawText(self.rect(), Qt.AlignCenter, self.center_text)


class InsightCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("subtlePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.title = QLabel("")
        self.title.setObjectName("sectionTitle")
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("muted")
        self.subtitle.setWordWrap(True)
        self.donut = DonutWidget()
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.donut, 1)

    def set_content(self, title: str, subtitle: str, values: list[tuple[str, float, str]], center_text: str) -> None:
        self.title.setText(title)
        self.subtitle.setText(subtitle)
        self.donut.set_segments(values, center_text)


class RadarCompareWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.axes: list[str] = []
        self.series: list[tuple[str, list[float], str]] = []
        self.selected_name: str | None = None
        self.setMinimumHeight(220)

    def set_data(self, axes: list[str], series: list[tuple[str, list[float], str]], selected_name: str | None = None) -> None:
        self.axes = axes
        self.series = series
        self.selected_name = selected_name
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        palette = get_shell_palette()
        center = self.rect().center()
        radius = min(self.width(), self.height()) * 0.34
        if not self.axes:
            painter.setPen(QColor(palette.muted))
            painter.drawText(self.rect(), Qt.AlignCenter, "No criteria")
            return
        count = len(self.axes)
        for ring in range(1, 5):
            points = []
            r = radius * (ring / 4.0)
            for index in range(count):
                angle = (-90 + (360 / count) * index) * 3.141592 / 180.0
                points.append(
                    QPoint(int(center.x() + r * __import__("math").cos(angle)), int(center.y() + r * __import__("math").sin(angle)))
                )
            painter.setPen(QPen(QColor(palette.border), 1))
            for index in range(count):
                painter.drawLine(points[index], points[(index + 1) % count])
        for index, label in enumerate(self.axes):
            angle = (-90 + (360 / count) * index) * 3.141592 / 180.0
            end = QPoint(int(center.x() + radius * __import__("math").cos(angle)), int(center.y() + radius * __import__("math").sin(angle)))
            painter.setPen(QPen(QColor(palette.border), 1))
            painter.drawLine(center, end)
            label_point = QPoint(int(center.x() + (radius + 18) * __import__("math").cos(angle)), int(center.y() + (radius + 18) * __import__("math").sin(angle)))
            painter.setPen(QColor(palette.muted))
            painter.drawText(QRectF(label_point.x() - 40, label_point.y() - 10, 80, 20), Qt.AlignCenter, label[:12])
        for name, values, color in self.series:
            points = []
            for index, value in enumerate(values):
                angle = (-90 + (360 / count) * index) * 3.141592 / 180.0
                r = radius * max(0.05, min(1.0, value))
                points.append(QPoint(int(center.x() + r * __import__("math").cos(angle)), int(center.y() + r * __import__("math").sin(angle))))
            is_selected = self.selected_name == name
            pen_color = QColor(color)
            pen_color.setAlpha(255 if is_selected or self.selected_name is None else 130)
            painter.setPen(QPen(pen_color, 4 if is_selected else 2))
            for index in range(count):
                painter.drawLine(points[index], points[(index + 1) % count])
            if is_selected:
                for point in points:
                    painter.setBrush(QColor(color))
                    painter.setPen(QPen(QColor(color), 1))
                    painter.drawEllipse(point, 3, 3)
        legend_y = self.height() - 20
        x = 16
        for name, _values, color in self.series:
            is_selected = self.selected_name == name
            painter.setPen(QPen(QColor(color), 8 if is_selected else 6))
            painter.drawLine(x, legend_y, x + 14, legend_y)
            painter.setPen(QColor(palette.text))
            painter.drawText(x + 20, legend_y + 5, name[:18])
            x += 110


class TemplatePickerDialog(QDialog):
    def __init__(self, templates: list[tuple[str, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.resize(360, 320)
        self.setStyleSheet(build_shell_stylesheet())
        self.selected_template = templates[0][0] if templates else "laptop"
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        chrome = QHBoxLayout()
        chrome.addWidget(QLabel("Choose Template"))
        chrome.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        chrome.addWidget(close_btn)
        title = QLabel("Start From Template")
        title.setObjectName("sectionTitle")
        hint = QLabel("Pick a comparison starter such as CPU, GPU, or laptop.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        self.template_list = QListWidget()
        for key, label in templates:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, key)
            self.template_list.addItem(item)
        if self.template_list.count():
            self.template_list.setCurrentRow(0)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        confirm_btn = QPushButton("Use Template")
        confirm_btn.setProperty("buttonRole", "primary")
        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self._accept_choice)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(confirm_btn)
        layout.addLayout(chrome)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.template_list, 1)
        layout.addLayout(buttons)
        outer.addWidget(card)

    def _accept_choice(self) -> None:
        item = self.template_list.currentItem()
        if item is not None:
            self.selected_template = str(item.data(Qt.UserRole))
        self.accept()


class ProductMatrixCellWidget(QFrame):
    selected = Signal(str)
    rename_requested = Signal(str, str)

    def __init__(self, product_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.product_id = product_id
        self.setObjectName("subtlePanel")
        self._accent = donut_colors()[0]
        self._selected = False
        self._score = 0.0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.body = QFrame()
        self.body.setObjectName("productHeaderBody")
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(8, 7, 8, 7)
        body_layout.setSpacing(5)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)
        self.name_edit = QLineEdit("Product")
        self.name_edit.setFrame(False)
        self.name_edit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.name_edit.setPlaceholderText("Product")
        self.name_edit.setStyleSheet(
            "QLineEdit { background:transparent; border:none; font-weight:600; padding:0px; }"
            "QLineEdit:hover { border-bottom:1px solid rgba(255,255,255,0.18); }"
            "QLineEdit:focus { border-bottom:1px solid rgba(255,255,255,0.35); }"
        )
        self.score_chip = QLabel("0.00")
        self.score_chip.setAlignment(Qt.AlignCenter)
        self.score_chip.setMinimumWidth(40)
        self.score_chip.setObjectName("mutedSmall")
        top_row.addWidget(self.name_edit, 1)
        top_row.addWidget(self.score_chip, 0)
        self.preview_strip = QLabel("")
        self.preview_strip.setAlignment(Qt.AlignCenter)
        self.preview_strip.setMinimumHeight(22)
        self.preview_strip.setMaximumHeight(22)
        self.preview_strip.setCursor(Qt.PointingHandCursor)
        top_row_widget = QWidget()
        top_row_widget.setLayout(top_row)
        body_layout.addWidget(top_row_widget, 0)
        body_layout.addWidget(self.preview_strip, 0)
        layout.addWidget(self.body, 1)
        self.body.mousePressEvent = self._select_requested  # type: ignore[method-assign]
        self.preview_strip.mousePressEvent = self._select_requested  # type: ignore[method-assign]
        self.score_chip.mousePressEvent = self._select_requested  # type: ignore[method-assign]
        self.name_edit.editingFinished.connect(self._emit_rename_requested)

    def _select_requested(self, _event) -> None:
        self.selected.emit(self.product_id)

    def _emit_rename_requested(self) -> None:
        self.rename_requested.emit(self.product_id, self.name_edit.text().strip())

    def set_product(self, product: ProductRecord, score: float, accent_color: str) -> None:
        self._accent = accent_color
        self._score = score
        self.name_edit.blockSignals(True)
        self.name_edit.setText(product.name)
        self.name_edit.blockSignals(False)
        self.score_chip.setText(f"{score:.1f}")
        palette = get_shell_palette()
        if product.image_path:
            pixmap = QPixmap(product.image_path)
            if not pixmap.isNull():
                self.preview_strip.setPixmap(pixmap.scaled(220, 22, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                self.preview_strip.setText("")
                self.preview_strip.setStyleSheet("background:transparent; border:none; border-radius:8px;")
            else:
                self.preview_strip.setPixmap(QPixmap())
                self.preview_strip.setText("Preview")
                self.preview_strip.setStyleSheet(
                    f"background:{palette.control_bg}; color:{accent_color}; border:1px solid {alpha_hex(accent_color, 72)}; border-radius:8px; font-size:11px;"
                )
        else:
            self.preview_strip.setPixmap(QPixmap())
            self.preview_strip.setText("No image")
            self.preview_strip.setStyleSheet(
                f"background:{palette.control_bg}; color:{palette.muted}; border:1px solid {palette.control_border}; border-radius:8px; font-size:11px;"
            )
        self._apply_selected_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_selected_style()

    def _apply_selected_style(self) -> None:
        palette = get_shell_palette()
        border = f"1px solid {alpha_hex(self._accent, 145)}" if self._selected else f"1px solid {palette.control_border}"
        background = alpha_hex(self._accent, 12) if self._selected else palette.surface_subtle
        self.setStyleSheet(f"background:{background}; border:{border}; border-radius:10px;")
        self.body.setStyleSheet(
            f"QFrame#productHeaderBody {{ background:transparent; border:none; }}"
        )
        self.name_edit.setStyleSheet(
            "QLineEdit { background:transparent; border:none; font-weight:600; padding:0px; }"
            f"QLineEdit:hover {{ border-bottom:1px solid {alpha_hex(self._accent, 80) if self._selected else alpha_hex(palette.text, 45)}; }}"
            f"QLineEdit:focus {{ border-bottom:1px solid {alpha_hex(self._accent, 140) if self._selected else palette.text}; }}"
        )
        self.score_chip.setStyleSheet(
            f"background:{alpha_hex(self._accent, 12) if self._selected else palette.control_bg}; "
            f"color:{self._accent if self._selected else palette.muted}; "
            f"border:1px solid {alpha_hex(self._accent, 48) if self._selected else palette.control_border}; "
            "border-radius:9px; padding:1px 7px; font-weight:600;"
        )


class CriterionMatrixCellWidget(QFrame):
    rename_requested = Signal(str, str)

    def __init__(self, criterion_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.criterion_id = criterion_id
        self._selected = False
        self._direction = "high"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(2)
        self.label_edit = QLineEdit("Criterion")
        self.label_edit.setFrame(False)
        self.label_edit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_edit.setStyleSheet(
            "QLineEdit { background:transparent; border:none; font-weight:600; padding:0px; }"
            "QLineEdit:hover { border-bottom:1px solid rgba(255,255,255,0.18); }"
            "QLineEdit:focus { border-bottom:1px solid rgba(255,255,255,0.35); }"
        )
        self.meta = QLabel("")
        self.meta.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.meta.setObjectName("mutedSmall")
        self.meta.setStyleSheet("background:transparent; border:none;")
        layout.addWidget(self.label_edit)
        layout.addWidget(self.meta)
        self._apply_style()
        self.label_edit.editingFinished.connect(self._emit_rename_requested)

    def _emit_rename_requested(self) -> None:
        self.rename_requested.emit(self.criterion_id, self.label_edit.text().strip())

    def set_criterion(self, criterion: CriterionRecord) -> None:
        self._direction = criterion.direction
        self.label_edit.blockSignals(True)
        self.label_edit.setText(criterion.label)
        self.label_edit.blockSignals(False)
        unit = criterion.unit if criterion.unit else "-"
        direction = "High" if criterion.direction == "high" else "Low"
        self.meta.setText(f"{unit}  •  {direction}  •  W{criterion.weight:.1f}")

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()

    def _apply_style(self) -> None:
        palette = get_shell_palette()
        accent = palette.accent if self._direction == "high" else palette.muted
        border = f"1px solid {alpha_hex(accent, 120)}" if self._selected else f"1px solid {palette.control_border}"
        bg = alpha_hex(accent, 10) if self._selected else palette.surface_subtle
        self.setStyleSheet(f"background:{bg}; border:{border}; border-radius:10px;")
        self.label_edit.setStyleSheet(
            "QLineEdit { background:transparent; border:none; font-weight:600; padding:0px; }"
            f"QLineEdit:hover {{ border-bottom:1px solid {alpha_hex(accent, 70) if self._selected else alpha_hex(palette.text, 45)}; }}"
            f"QLineEdit:focus {{ border-bottom:1px solid {alpha_hex(accent, 120) if self._selected else palette.text}; }}"
        )
        self.meta.setStyleSheet(f"background:transparent; border:none; color:{palette.muted}; font-size:11px;")


class EdgeAddButton(QPushButton):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.setObjectName("ghostAddButton")
        self.setCursor(Qt.PointingHandCursor)
        palette = get_shell_palette()
        self.setStyleSheet(
            f"QPushButton#ghostAddButton {{ border: 1px dashed {palette.control_border}; border-radius: 12px; padding: 8px 10px; color: {palette.muted}; background: {palette.surface_subtle}; }}"
            f"QPushButton#ghostAddButton:hover {{ border-color: {palette.chip_border}; color: {palette.text}; background: {palette.control_bg}; }}"
        )
