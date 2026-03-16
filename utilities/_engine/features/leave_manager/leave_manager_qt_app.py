"""Leave Manager – Simplified Vertical Qt GUI implementation (V3)."""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal, QSize, QSettings, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateTimeEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from contexthub.ui.qt.shell import (
    HeaderSurface,
    apply_app_icon,
    build_shell_stylesheet,
    build_size_grip,
    get_shell_metrics,
    get_shell_palette,
    qt_t,
)
from features.leave_manager.leave_manager_service import LeaveManagerService

# --- UI Constants ---
ACCENT_COLOR = "#818cf8"
ACCENT_GLASS = "rgba(129, 140, 248, 0.15)"


def get_event_color(event: Dict[str, Any]) -> str | None:
    amt = event.get("amount", 0.0)
    etype = event.get("type", "").lower()
    is_half = abs(amt) == 0.5

    if amt < 0:
        if "연차" in etype or "annual" in etype:
            return "#4e9af1" if is_half else "#1e88e5"
        if "대체휴가" in etype or "credit" in etype:
            return "#81c784" if is_half else "#43a047"
        if "병가" in etype or "sick" in etype:
            return "#4dd0e1" if is_half else "#00acc1"
        return "#4e9af1" if is_half else "#1e88e5"
    if amt > 0:
        return "#81c784" if is_half else "#43a047"
    return None


class CalendarCell(QFrame):
    clicked = Signal(str)
    entered = Signal(str)
    drag_started = Signal(str)

    def __init__(self, day: int, date_str: str, is_today: bool = False, is_weekend: bool = False, holiday_name: str | None = None):
        super().__init__()
        self.day = day
        self.date_str = date_str
        self.is_today = is_today
        self.is_weekend = is_weekend
        self.holiday_name = holiday_name
        self.event_color: str | None = None
        self.is_preview: bool = False
        
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(40, 40)
        self.setObjectName("calendarCell")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        
        self.label = QLabel(str(day))
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        if holiday_name:
            self.setToolTip(f"Holiday: {holiday_name}")
            
        self._update_style()

    def set_event(self, color: str | None, tooltip: str | None = None):
        self.event_color = color
        if tooltip:
            self.setToolTip(tooltip)
        self._update_style()

    def set_preview(self, is_preview: bool):
        self.is_preview = is_preview
        self._update_style()

    def _update_style(self):
        palette = get_shell_palette()
        bg = "transparent"
        text_color = palette.text
        border = palette.border
        border_width = 1
        
        if self.is_weekend or self.holiday_name:
            text_color = "#f87171"
            
        if self.event_color:
            bg = self.event_color
            text_color = "#ffffff"
            border = "transparent"
            
        if self.is_preview:
            bg = ACCENT_GLASS
            border = ACCENT_COLOR
            border_width = 1
            
        if self.is_today:
            border = ACCENT_COLOR
            border_width = 2
            
        self.setStyleSheet(f"""
            QFrame#calendarCell {{
                background-color: {bg};
                color: {text_color};
                border: {border_width}px solid {border};
                border_radius: 8px;
            }}
            QLabel {{
                color: {text_color};
                font-family: 'Inter', sans-serif;
                font-weight: {"800" if self.is_today else "500"};
                font-size: 14px;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.date_str)
            self.drag_started.emit(self.date_str)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.entered.emit(self.date_str)
        super().enterEvent(event)


class CalendarPanel(QFrame):
    date_selected = Signal(str)
    range_selected = Signal(str, str)
    range_dragging = Signal(str, str)

    def __init__(self, service: LeaveManagerService):
        super().__init__()
        self.service = service
        self.setObjectName("subtlePanel")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 20)
        layout.setSpacing(12)
        
        # Calendar Header
        header = QHBoxLayout()
        header.setSpacing(12)
        
        self.prev_btn = QPushButton("‹")
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setObjectName("iconBtn")
        
        self.month_label = QLabel("")
        self.month_label.setObjectName("sectionTitle")
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setStyleSheet("font-size: 20px; font-weight: 800;")
        
        self.next_btn = QPushButton("›")
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setObjectName("iconBtn")
        
        header.addWidget(self.prev_btn)
        header.addWidget(self.month_label, 1)
        header.addWidget(self.next_btn)
        layout.addLayout(header)
        
        # Grid
        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(6)
        layout.addWidget(self.grid_container, 1)
        
        self.prev_btn.clicked.connect(self._prev_month)
        self.next_btn.clicked.connect(self._next_month)
        
        self._cells: List[CalendarCell] = []
        self._drag_start_date: str | None = None
        self.refresh()

    def mouseReleaseEvent(self, event):
        if self._drag_start_date and event.button() == Qt.LeftButton:
            self._drag_start_date = None
        super().mouseReleaseEvent(event)

    def _on_cell_drag_start(self, ds: str):
        self._drag_start_date = ds

    def _on_cell_entered(self, ds: str):
        if self._drag_start_date:
            self.range_dragging.emit(self._drag_start_date, ds)
            self.range_selected.emit(self._drag_start_date, ds)

    def _prev_month(self):
        s = self.service.state
        if s.current_month_month == 1:
            s.current_month_year -= 1
            s.current_month_month = 12
        else:
            s.current_month_month -= 1
        self.refresh()

    def _next_month(self):
        s = self.service.state
        if s.current_month_month == 12:
            s.current_month_year += 1
            s.current_month_month = 1
        else:
            s.current_month_month += 1
        self.refresh()

    def refresh(self):
        for cell in self._cells:
            self.grid.removeWidget(cell)
            cell.deleteLater()
        self._cells.clear()
        
        s = self.service.state
        yr, mo = s.current_month_year, s.current_month_month
        self.month_label.setText(f"{yr}년 {mo}월")
        
        day_names = ["월", "화", "수", "목", "금", "토", "일"]
        for i, name in enumerate(day_names):
            label = QLabel(name)
            label.setAlignment(Qt.AlignCenter)
            label.setObjectName("eyebrow")
            label.setStyleSheet("padding-bottom: 4px; color: #94a3b8; font-weight: 700;")
            self.grid.addWidget(label, 0, i)
        
        first_day = date(yr, mo, 1)
        start_wd = first_day.weekday() 
        
        next_mo = date(yr + 1, 1, 1) if mo == 12 else date(yr, mo + 1, 1)
        days_in_month = (next_mo - first_day).days
        
        today = date.today()
        events = self.service.get_events_for_month(yr, mo)
        
        holidays_map = {}
        try:
            import holidays
            holidays_map = holidays.KR(years=yr)
        except: pass

        row, col = 1, start_wd
        for d in range(1, days_in_month + 1):
            cur_date = date(yr, mo, d)
            ds = cur_date.isoformat()
            
            is_today = (cur_date == today)
            is_weekend = (col >= 5)
            hol_name = holidays_map.get(cur_date)
            
            cell = CalendarCell(d, ds, is_today, is_weekend, hol_name)
            cell.clicked.connect(self.date_selected.emit)
            cell.drag_started.connect(self._on_cell_drag_start)
            cell.entered.connect(self._on_cell_entered)
            
            if ds in s.preview_dates:
                cell.set_preview(True)
            
            day_events = events.get(d, [])
            if day_events:
                ev = day_events[0]
                color = get_event_color(ev)
                tip = f"{ev.get('type')}\n{ev.get('note')}"
                if ev.get("amount"):
                    tip += f"\nDays: {abs(ev['amount'])}"
                cell.set_event(color, tip)
                
            self.grid.addWidget(cell, row, col)
            self._cells.append(cell)
            
            col += 1
            if col > 6:
                col = 0
                row += 1
        
        self.grid.setRowStretch(row + 1, 1)


class DashboardLayer(QFrame):
    def __init__(self, service: LeaveManagerService):
        super().__init__()
        self.service = service
        self.setObjectName("card")
        self.setFixedHeight(180)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(24)
        
        # 1. Stats Section (Left)
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(8)
        self.annual_lbl = self._build_stat_row("Annual")
        self.credit_lbl = self._build_stat_row("Credit")
        self.sick_lbl = self._build_stat_row("Sick")
        stats_layout.addLayout(self.annual_lbl)
        stats_layout.addLayout(self.credit_lbl)
        stats_layout.addLayout(self.sick_lbl)
        layout.addLayout(stats_layout, 1)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setObjectName("separator")
        line.setStyleSheet("background: rgba(255,255,255,0.1); width: 1px;")
        layout.addWidget(line)
        
        # 2. Form Section (Middle)
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)
        
        row1 = QHBoxLayout()
        self.use_date = QLineEdit()
        self.use_date.setPlaceholderText("YYYY-MM-DD")
        self.use_date.setFixedWidth(120)
        self.use_type = QComboBox()
        self.use_type.addItems(self.service.get_leave_types())
        self.use_type.setFixedWidth(120)
        row1.addWidget(QLabel("Date:"))
        row1.addWidget(self.use_date)
        row1.addWidget(QLabel("Type:"))
        row1.addWidget(self.use_type)
        row1.addStretch()
        
        row2 = QHBoxLayout()
        self.use_amt_lbl = QLabel("1.0 d")
        self.use_amt_lbl.setStyleSheet(f"font-weight: 700; color: {ACCENT_COLOR};")
        self.use_amt_slider = QSlider(Qt.Horizontal)
        self.use_amt_slider.setRange(1, 10)
        self.use_amt_slider.setValue(2)
        row2.addWidget(QLabel("Amt:"))
        row2.addWidget(self.use_amt_slider)
        row2.addWidget(self.use_amt_lbl)
        
        row3 = QHBoxLayout()
        self.use_note = QLineEdit()
        self.use_note.setPlaceholderText("Note (Optional)...")
        self.submit_btn = QPushButton("Submit Use Leave")
        self.submit_btn.setObjectName("primary")
        self.submit_btn.setFixedHeight(32)
        row3.addWidget(self.use_note)
        row3.addWidget(self.submit_btn)
        
        form_layout.addLayout(row1)
        form_layout.addLayout(row2)
        form_layout.addLayout(row3)
        layout.addLayout(form_layout, 2)
        
        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.VLine)
        line2.setObjectName("separator")
        line2.setStyleSheet("background: rgba(255,255,255,0.1); width: 1px;")
        layout.addWidget(line2)
        
        # 3. Actions Section (Right)
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)
        
        self.undo_btn = QPushButton("↩ Undo")
        self.redo_btn = QPushButton("↪ Redo")
        self.report_btn = QPushButton("📊 Report")
        self.report_btn.setObjectName("primary")
        self.report_btn.setFixedHeight(40)
        
        h_row = QHBoxLayout()
        h_row.addWidget(self.undo_btn)
        h_row.addWidget(self.redo_btn)
        
        actions_layout.addLayout(h_row)
        actions_layout.addWidget(self.report_btn)
        layout.addLayout(actions_layout, 1)

    def _build_stat_row(self, label: str) -> QLabel:
        lt = QHBoxLayout()
        l = QLabel(f"{label}:")
        l.setObjectName("muted")
        l.setStyleSheet("font-size: 11px;")
        v = QLabel("0.0d")
        v.setStyleSheet("font-weight: 700; font-size: 14px;")
        lt.addWidget(l)
        lt.addStretch()
        lt.addWidget(v)
        parent_lt = QVBoxLayout()
        parent_lt.addLayout(lt)
        return v

    def refresh_stats(self):
        stats = self.service.state.stats
        if not stats: return
        a = stats.get("annual", {})
        c = stats.get("credit", {})
        sk = stats.get("sick", {})
        self.annual_lbl.setText(f"{a.get('remaining', 0):.1f} / {a.get('total', 0):.0f} d")
        self.credit_lbl.setText(f"{c.get('remaining', 0):.1f} / {c.get('total', 0):.0f} d")
        self.sick_lbl.setText(f"{sk.get('used', 0):.1f} d")


class LeaveManagerWindow(QMainWindow):
    def __init__(self, service: LeaveManagerService, app_root: Path) -> None:
        super().__init__()
        self.service = service
        self.app_root = app_root
        self._settings = QSettings("Contexthub", "leave_manager_v3")
        
        self.setWindowTitle("Leave Manager")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1000, 800)
        self.setMinimumSize(800, 650)
        apply_app_icon(self, self.app_root)
        
        self.setStyleSheet(build_shell_stylesheet())
        self._build_ui()
        self._restore_window_state()
        self._refresh_all()

    def _build_ui(self) -> None:
        m = get_shell_metrics()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(m.shell_margin-2, m.shell_margin-2, m.shell_margin-2, m.shell_margin-2)
        
        self.shell = QFrame()
        self.shell.setObjectName("windowShell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        
        # Header
        self.header = HeaderSurface(self, "Leave Manager", "Simplified Attendance", self.app_root)
        self.header.asset_count_badge.hide()
        self.header.runtime_status_badge.hide()
        shell_layout.addWidget(self.header)
        
        # Content
        content = QVBoxLayout()
        content.setContentsMargins(m.shell_margin, m.shell_margin, m.shell_margin, m.shell_margin)
        content.setSpacing(m.section_gap)
        
        self.dashboard = DashboardLayer(self.service)
        content.addWidget(self.dashboard)
        
        self.calendar = CalendarPanel(self.service)
        content.addWidget(self.calendar, 1)
        
        shell_layout.addLayout(content)
        
        # Grip
        grip_row = QHBoxLayout()
        grip_row.addStretch()
        grip_row.addWidget(build_size_grip())
        shell_layout.addLayout(grip_row)
        
        root.addWidget(self.shell)
        
        # Signals
        self.calendar.date_selected.connect(self._on_date_selected)
        self.calendar.range_selected.connect(self._on_range_selected)
        self.calendar.range_dragging.connect(self._on_range_selected)
        
        self.dashboard.use_amt_slider.valueChanged.connect(self._on_amt_slider_changed)
        self.dashboard.submit_btn.clicked.connect(self._submit_use)
        self.dashboard.undo_btn.clicked.connect(self._undo)
        self.dashboard.redo_btn.clicked.connect(self._redo)
        self.dashboard.report_btn.clicked.connect(self._generate_report)

    def _on_date_selected(self, ds: str):
        self.dashboard.use_date.setText(ds)
        self.service.update_preview_dates(ds, self.service.state.use_amount)
        self.calendar.refresh()

    def _on_range_selected(self, s_ds: str, e_ds: str):
        self.dashboard.use_date.setText(s_ds)
        amt = self.service.update_preview_range(s_ds, e_ds)
        self.dashboard.use_amt_slider.blockSignals(True)
        self.dashboard.use_amt_slider.setValue(int(min(amt*2, 10)))
        self.dashboard.use_amt_slider.blockSignals(False)
        self.dashboard.use_amt_lbl.setText(f"{amt:.1f} d")
        self.service.state.use_amount = amt
        self.calendar.refresh()

    def _on_amt_slider_changed(self, val):
        amt = val / 2.0
        self.dashboard.use_amt_lbl.setText(f"{amt:.1f} d")
        self.service.state.use_amount = amt
        if self.dashboard.use_date.text():
            self._on_date_selected(self.dashboard.use_date.text())

    def _submit_use(self):
        if self.service.submit_use_leave(
            self.dashboard.use_date.text(),
            self.dashboard.use_type.currentText(),
            self.service.state.use_amount,
            self.dashboard.use_note.text()
        ):
            self._refresh_all()

    def _undo(self): 
        if self.service.undo(): self._refresh_all()
    def _redo(self): 
        if self.service.redo(): self._refresh_all()
    def _generate_report(self):
        p = self.service.generate_report(self.app_root)
        if p: import webbrowser; webbrowser.open(f"file:///{Path(p).resolve()}")

    def _refresh_all(self):
        self.dashboard.refresh_stats()
        self.calendar.refresh()

    def _restore_window_state(self):
        geo = self._settings.value("geometry")
        if geo: self.restoreGeometry(geo)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def start_app(targets: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    service = LeaveManagerService()
    window = LeaveManagerWindow(service, Path(__file__).resolve().parents[3] / "utilities" / "leave_manager")
    window.show()
    return app.exec()
