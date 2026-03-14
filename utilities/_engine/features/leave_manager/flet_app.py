"""Leave Manager – Flet UI."""

from __future__ import annotations

import threading
from datetime import date, datetime, timedelta
from typing import List

import flet as ft

from contexthub.ui.flet.tokens import COLORS, SPACING, RADII, WINDOWS
from contexthub.ui.flet.theme import configure_page
from utils.i18n import t

from features.leave_manager.logic import LeaveManagerCore
from features.leave_manager.storage import LeaveManagerStorage
from features.leave_manager.services import Integrations
from features.leave_manager.state import LeaveManagerState

# ── color tokens (matching legacy) ──
TICKET_BLUE = "#1a237e"
TICKET_BLUE_HOVER = "#0d47a1"

# ── event → color mapping ──
def _event_color(event: dict) -> str | None:
    """Returns bg color for a calendar day based on event type."""
    amt = event.get("amount", 0)
    etype = event.get("type", "").lower()
    is_half = abs(amt) == 0.5

    if amt < 0:
        if "연차" in etype or "annual" in etype:
            return "#5c9ce6" if is_half else "#1976d2"
        if "대체휴가" in etype or "credit" in etype:
            return "#a5d6a7" if is_half else "#66bb6a"
        if "병가" in etype or "sick" in etype:
            return "#4dd0e1" if is_half else "#00acc1"
        return "#5c9ce6" if is_half else "#1976d2"
    if amt > 0:
        return "#a5d6a7" if is_half else "#66bb6a"
    return None


# ── window ──
def _apply_window(page: ft.Page, title: str):
    configure_page(page, title)
    page.window_width = 540
    page.window_height = 860
    page.window_min_width = 480
    page.window_min_height = 700


# ── entry point ──
def start_app(targets: List[str] | None = None):

    def main(page: ft.Page):
        storage = LeaveManagerStorage()
        core = LeaveManagerCore(storage)
        state = LeaveManagerState()

        leave_types = core.get_leave_types()
        if leave_types:
            state.use_type = leave_types[0]
        state.add_type = t("leave_manager_gui.credit_leave")

        _apply_window(page, t("leave_manager_gui.title"))

        # ══════════ CALENDAR WIDGET ══════════

        cal_header_text = ft.Text("", size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"])
        cal_grid = ft.Column(spacing=2)

        def _render_calendar():
            yr = state.current_month_year
            mo = state.current_month_month
            cal_header_text.value = f"{yr}년 {mo}월"

            events = core.get_events_for_month(yr, mo)
            first = date(yr, mo, 1)
            start_wd = first.weekday()
            next_mo = date(yr + 1, 1, 1) if mo == 12 else date(yr, mo + 1, 1)
            days_in = (next_mo - first).days
            today_s = date.today().isoformat()

            # holidays
            holidays_map = {}
            try:
                import holidays as hl
                holidays_map = hl.KR(years=yr)
            except Exception:
                pass

            cal_grid.controls.clear()

            # day headers
            day_names = [t("utilities_common.mon"), t("utilities_common.tue"),
                         t("utilities_common.wed"), t("utilities_common.thu"),
                         t("utilities_common.fri"), t("utilities_common.sat"),
                         t("utilities_common.sun")]
            header_row = ft.Row(
                controls=[ft.Container(
                    content=ft.Text(d, size=10, weight=ft.FontWeight.BOLD,
                                    color=COLORS["text_muted"], text_align=ft.TextAlign.CENTER),
                    width=48, alignment=ft.alignment.Alignment(0, 0),
                ) for d in day_names],
                spacing=2,
                alignment=ft.MainAxisAlignment.CENTER,
            )
            cal_grid.controls.append(header_row)

            # day cells
            row_cells = []
            # fill blanks before first day
            for _ in range(start_wd):
                row_cells.append(ft.Container(width=48, height=36))

            for d in range(1, days_in + 1):
                ds = f"{yr}-{mo:02d}-{d:02d}"
                col_idx = (start_wd + d - 1) % 7

                bg = "transparent"
                tc = COLORS["text"]
                border_c = COLORS["line"]
                border_w = 1

                # weekend / holiday
                cur_date = date(yr, mo, d)
                hol_name = holidays_map.get(cur_date)
                if col_idx >= 5 or hol_name:
                    tc = "#ef5350"

                # events
                day_events = events.get(d, [])
                if day_events:
                    ec = _event_color(day_events[0])
                    if ec:
                        bg = ec
                        tc = "#ffffff"

                # preview
                if ds in state.preview_dates:
                    bg = "#616161"
                    tc = "#ffffff"

                # today
                if ds == today_s:
                    border_c = TICKET_BLUE
                    border_w = 2

                # tooltip
                tip = ""
                if hol_name:
                    tip += f"{t('leave_manager_gui.holiday')}: {hol_name}\n"
                if day_events:
                    ev = day_events[0]
                    tip += f"{ev.get('type', '')}\n{ev.get('note', '')}"
                    if ev.get("amount"):
                        tip += f"\n{t('leave_manager_gui.days_label')}: {abs(ev['amount'])}"

                cell_content = ft.Text(str(d), size=11, color=tc, text_align=ft.TextAlign.CENTER)
                cell = ft.Container(
                    content=cell_content,
                    tooltip=tip.strip() or str(d) if tip.strip() else None,
                    width=48,
                    height=36,
                    bgcolor=bg,
                    border_radius=6,
                    border=ft.border.all(border_w, border_c),
                    alignment=ft.alignment.Alignment(0, 0),
                    on_click=lambda e, _ds=ds: _on_date_click(_ds),
                    on_long_press=lambda e, _ds=ds: _on_date_delete(_ds),
                )
                row_cells.append(cell)

                if col_idx == 6:
                    cal_grid.controls.append(ft.Row(controls=row_cells, spacing=2,
                                                     alignment=ft.MainAxisAlignment.CENTER))
                    row_cells = []

            # last row
            if row_cells:
                while len(row_cells) < 7:
                    row_cells.append(ft.Container(width=48, height=36))
                cal_grid.controls.append(ft.Row(controls=row_cells, spacing=2,
                                                 alignment=ft.MainAxisAlignment.CENTER))

        def _prev_month(e):
            if state.current_month_month == 1:
                state.current_month_year -= 1
                state.current_month_month = 12
            else:
                state.current_month_month -= 1
            _render_calendar()
            page.update()

        def _next_month(e):
            if state.current_month_month == 12:
                state.current_month_year += 1
                state.current_month_month = 1
            else:
                state.current_month_month += 1
            _render_calendar()
            page.update()

        def _on_date_click(ds: str):
            state.selected_date = ds
            use_date_field.value = ds
            add_date_field.value = ds
            _update_preview()
            page.update()

        def _on_date_delete(ds: str):
            """Long-press on a day → delete events."""
            yr = int(ds[:4])
            mo = int(ds[5:7])
            dy = int(ds[8:10])
            evts = core.get_events_for_month(yr, mo).get(dy, [])
            if not evts:
                return
            for ev in evts:
                core.delete_history_item_by_content(ev)
            _refresh_all()

        # ══════════ STATS CARD ══════════

        stat_annual = ft.Text("", size=13, color=COLORS["text"])
        stat_credit = ft.Text("", size=13, color=COLORS["text"])
        stat_sick = ft.Text("", size=13, color=COLORS["text"])

        def _refresh_stats():
            stats = core.calculate_balance()
            state.stats = stats
            a = stats.get("annual", {})
            c = stats.get("credit", {})
            sk = stats.get("sick", {})
            stat_annual.value = f"{t('leave_manager_gui.annual_leave')}: {a.get('remaining', 0):.1f} / {a.get('total', 0):.0f} {t('leave_manager_gui.days')}"
            stat_credit.value = f"{t('leave_manager_gui.credit_leave')}: {c.get('remaining', 0):.1f} / {c.get('total', 0):.0f} {t('leave_manager_gui.days')}"
            stat_sick.value = f"{t('leave_manager_gui.sick_leave')}: {sk.get('used', 0):.1f} {t('leave_manager_gui.days')}"

        stats_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        t("leave_manager_gui.status_title", year=date.today().year),
                        size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"],
                    ),
                    stat_annual, stat_credit, stat_sick,
                ],
                spacing=4,
            ),
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
            padding=SPACING["sm"],
        )

        # ══════════ USE LEAVE TAB ══════════

        use_date_field = ft.TextField(
            value=state.selected_date, hint_text="YYYY-MM-DD",
            border_color=COLORS["line"], bgcolor=COLORS["field_bg"],
            color=COLORS["text"], height=36, text_size=12, expand=True,
            on_change=lambda e: _update_preview(),
        )
        use_type_dd = ft.Dropdown(
            options=[ft.dropdown.Option(lt) for lt in leave_types],
            value=state.use_type if state.use_type else (leave_types[0] if leave_types else ""),
            border_color=COLORS["line"], bgcolor=COLORS["field_bg"], color=COLORS["text"],
            height=36, text_size=12, expand=True,
        )

        use_amt_label = ft.Text("1.0", size=12, color=COLORS["text"], width=30)
        use_amt_slider = ft.Slider(
            min=0.5, max=5.0, divisions=9, value=1.0,
            active_color=COLORS["accent"],
            on_change=lambda e: _on_use_slider(e),
            expand=True,
        )

        def _on_use_slider(e):
            v = round(e.control.value * 2) / 2  # snap to 0.5
            use_amt_label.value = f"{v:.1f}"
            state.use_amount = v
            _update_preview()
            page.update()

        use_note_field = ft.TextField(
            hint_text=t("leave_manager_gui.reason_note"),
            border_color=COLORS["line"], bgcolor=COLORS["field_bg"],
            color=COLORS["text"], height=36, text_size=12,
        )

        def _update_preview():
            ds = use_date_field.value or ""
            if len(ds) == 10:
                state.preview_dates = core.get_preview_dates(ds, state.use_amount)
            else:
                state.preview_dates = []
            _render_calendar()

        def _submit_use(e):
            d = use_date_field.value or ""
            tp = use_type_dd.value or ""
            a = state.use_amount
            n = use_note_field.value or ""

            # credit balance check
            if "대체휴가" in tp or "credit" in tp.lower():
                stats = core.calculate_balance()
                cr = stats.get("credit", {}).get("remaining", 0)
                if cr < a:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(
                            t("leave_manager_gui.insufficient_credit_msg").format(avail=cr, requested=a),
                            color=COLORS["text"],
                        ),
                        bgcolor=COLORS["danger"],
                    )
                    page.snack_bar.open = True
                    page.update()
                    return

            dates = core.get_preview_dates(d, a)
            if not dates:
                return
            whole = int(a)
            remainder = a - whole
            for i, ds in enumerate(dates):
                amt = -1.0 if i < whole else (-remainder if remainder > 0 else 0)
                if amt != 0:
                    core.add_history_item(ds, tp, amt, n)

            _refresh_all()

        btn_use = ft.ElevatedButton(
            content=ft.Text(t("leave_manager_gui.use_leave_tab"), weight=ft.FontWeight.BOLD, color="#ffffff"),
            bgcolor=TICKET_BLUE, height=36,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
            on_click=_submit_use,
        )

        use_tab = ft.Column(
            controls=[
                ft.Row([ft.Text(t("leave_manager_gui.date"), width=50, size=12, color=COLORS["text_muted"]),
                        use_date_field]),
                ft.Row([ft.Text(t("leave_manager_gui.type"), width=50, size=12, color=COLORS["text_muted"]),
                        use_type_dd]),
                ft.Row([ft.Text(t("leave_manager_gui.days_label"), width=50, size=12, color=COLORS["text_muted"]),
                        use_amt_slider, use_amt_label]),
                use_note_field,
                btn_use,
            ],
            spacing=6,
        )

        # ══════════ ADD CREDIT TAB ══════════

        add_date_field = ft.TextField(
            value=state.selected_date, hint_text="YYYY-MM-DD",
            border_color=COLORS["line"], bgcolor=COLORS["field_bg"],
            color=COLORS["text"], height=36, text_size=12, expand=True,
        )
        add_type_field = ft.TextField(
            value=state.add_type,
            border_color=COLORS["line"], bgcolor=COLORS["field_bg"],
            color=COLORS["text"], height=36, text_size=12, expand=True,
        )
        add_amt_label = ft.Text("1.0", size=12, color=COLORS["text"], width=30)
        add_amt_slider = ft.Slider(
            min=0.5, max=5.0, divisions=9, value=1.0,
            active_color=COLORS["success"],
            on_change=lambda e: _on_add_slider(e),
            expand=True,
        )

        def _on_add_slider(e):
            v = round(e.control.value * 2) / 2
            add_amt_label.value = f"{v:.1f}"
            state.add_amount = v
            page.update()

        def _submit_add(e):
            d = add_date_field.value or ""
            tp = add_type_field.value or ""
            a = state.add_amount
            core.add_history_item(d, tp, a, "Credit Added")
            _refresh_all()

        def _export_html(e):
            import os
            import webbrowser
            fname = f"leave_report_{datetime.now().strftime('%Y%m%d')}.html"
            out = Path(os.environ.get("CTX_APP_ROOT", ".")) / fname

            if core.generate_html_report(str(out)):
                webbrowser.open(f"file:///{out.resolve()}")
                page.snack_bar = ft.SnackBar(content=ft.Text(f"Exported: {fname}", color=COLORS["text"]),
                                              bgcolor=COLORS["success"])
                page.snack_bar.open = True
                page.update()

        btn_add = ft.ElevatedButton(
            content=ft.Text(t("leave_manager_gui.add_credit_tab"), weight=ft.FontWeight.BOLD, color="#ffffff"),
            bgcolor=COLORS["success"], height=36,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
            on_click=_submit_add,
        )
        btn_report = ft.ElevatedButton(
            content=ft.Text(t("leave_manager_gui.export_report"), size=11, color="#ffffff"),
            bgcolor=TICKET_BLUE, height=32,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
            on_click=_export_html,
        )

        add_tab = ft.Column(
            controls=[
                ft.Row([ft.Text(t("leave_manager_gui.date"), width=50, size=12, color=COLORS["text_muted"]),
                        add_date_field]),
                ft.Row([ft.Text(t("leave_manager_gui.type"), width=50, size=12, color=COLORS["text_muted"]),
                        add_type_field]),
                ft.Row([ft.Text(t("leave_manager_gui.days_label"), width=50, size=12, color=COLORS["text_muted"]),
                        add_amt_slider, add_amt_label]),
                btn_add,
                btn_report,
            ],
            spacing=6,
        )

        # ══════════ SETTINGS TAB ══════════

        settings_data = core.get_settings()
        set_total = ft.TextField(
            value=str(settings_data.get("total_days", 15.0)),
            border_color=COLORS["line"], bgcolor=COLORS["field_bg"],
            color=COLORS["text"], height=36, text_size=12, expand=True,
        )
        set_reset = ft.TextField(
            value=str(settings_data.get("reset_date", "01-01")),
            border_color=COLORS["line"], bgcolor=COLORS["field_bg"],
            color=COLORS["text"], height=36, text_size=12, expand=True,
        )
        set_exp = ft.TextField(
            value=str(settings_data.get("expiration_date", "")),
            border_color=COLORS["line"], bgcolor=COLORS["field_bg"],
            color=COLORS["text"], height=36, text_size=12, expand=True,
        )

        def _save_settings(e):
            try:
                core.save_settings(
                    total_days=float(set_total.value),
                    reset_date=set_reset.value,
                    expiration_date=set_exp.value,
                )
                _refresh_all()
            except ValueError:
                pass

        def _export_data(e):
            fname = f"leave_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            out = Path(os.environ.get("CTX_APP_ROOT", ".")) / fname
            if storage.export_all_data(str(out)):
                page.snack_bar = ft.SnackBar(content=ft.Text(f"Exported: {fname}", color=COLORS["text"]),
                                              bgcolor=COLORS["success"])
                page.snack_bar.open = True
                page.update()

        def _import_data(e):
            import_picker.pick_files(
                dialog_title=t("leave_manager_gui.import_data"),
                allowed_extensions=["json"],
            )

        import_picker = ft.FilePicker()
        page.overlay.append(import_picker)

        def _on_import_result(e: ft.FilePickerResultEvent):
            if e.files and e.files[0]:
                fpath = e.files[0].path
                if storage.import_all_data(fpath):
                    # refresh settings fields
                    new_s = core.get_settings()
                    set_total.value = str(new_s.get("total_days", 15.0))
                    set_reset.value = str(new_s.get("reset_date", "01-01"))
                    set_exp.value = str(new_s.get("expiration_date", ""))
                    _refresh_all()

        import_picker.on_result = _on_import_result

        import os

        settings_tab = ft.Column(
            controls=[
                ft.Row([ft.Text(t("leave_manager_gui.given_days"), width=80, size=12, color=COLORS["text_muted"]),
                        set_total]),
                ft.Row([ft.Text(t("leave_manager_gui.reset_date"), width=80, size=12, color=COLORS["text_muted"]),
                        set_reset]),
                ft.Row([ft.Text(t("leave_manager_gui.expiry"), width=80, size=12, color=COLORS["text_muted"]),
                        set_exp]),
                ft.ElevatedButton(
                    content=ft.Text(t("leave_manager_gui.save_settings"), weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    bgcolor=COLORS["accent"], height=32,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADII["sm"])),
                    on_click=_save_settings,
                ),
                ft.Divider(height=1, color=COLORS["line"]),
                ft.Text(t("leave_manager_gui.data_management"), size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                ft.Row([
                    ft.ElevatedButton(
                        content=ft.Text(t("leave_manager_gui.import_data"), size=11, color=COLORS["text"]),
                        bgcolor=COLORS["surface"], height=30,
                        style=ft.ButtonStyle(side=ft.BorderSide(1, COLORS["line"]),
                                              shape=ft.RoundedRectangleBorder(radius=8)),
                        on_click=_import_data, expand=True,
                    ),
                    ft.ElevatedButton(
                        content=ft.Text(t("leave_manager_gui.export_data"), size=11, color=COLORS["text"]),
                        bgcolor=COLORS["surface"], height=30,
                        style=ft.ButtonStyle(side=ft.BorderSide(1, COLORS["line"]),
                                              shape=ft.RoundedRectangleBorder(radius=8)),
                        on_click=_export_data, expand=True,
                    ),
                ], spacing=8),
            ],
            spacing=6,
        )

        # ══════════ TABS ══════════

        tabs = ft.Tabs(
            length=3,
            selected_index=0,
            content=ft.Column([
                ft.TabBar(
                    tabs=[
                        ft.Tab(label=t("leave_manager_gui.use_leave_tab")),
                        ft.Tab(label=t("leave_manager_gui.add_credit_tab")),
                        ft.Tab(label=t("leave_manager_gui.settings_tab")),
                    ],
                    indicator_color=COLORS["accent"],
                    label_color=COLORS["text"],
                    unselected_label_color=COLORS["text_muted"],
                ),
                ft.TabBarView(
                    controls=[
                        ft.Container(content=use_tab, padding=8),
                        ft.Container(content=add_tab, padding=8),
                        ft.Container(content=settings_tab, padding=8),
                    ],
                    expand=True,
                )
            ], expand=True, spacing=0),
        )

        tabs_card = ft.Container(
            content=tabs,
            bgcolor=COLORS["surface"],
            border_radius=RADII["md"],
            border=ft.border.all(1, COLORS["line"]),
            height=260,
        )

        # ══════════ HISTORY ══════════

        history_column = ft.Column(controls=[], spacing=2, scroll=ft.ScrollMode.AUTO, height=0, visible=False)
        btn_history_toggle = ft.TextButton(
            content=ft.Text(f"{t('leave_manager_gui.history')} ▼", size=12, color=COLORS["text_muted"]),
            on_click=lambda e: _toggle_history(),
        )

        def _toggle_history():
            state.history_expanded = not state.history_expanded
            if state.history_expanded:
                history_column.visible = True
                history_column.height = 200
                btn_history_toggle.content = ft.Text(
                    f"{t('leave_manager_gui.history')} ▲", size=12, color=COLORS["text_muted"])
                _render_history()
            else:
                history_column.visible = False
                history_column.height = 0
                btn_history_toggle.content = ft.Text(
                    f"{t('leave_manager_gui.history')} ▼", size=12, color=COLORS["text_muted"])
            page.update()

        def _render_history():
            history_column.controls.clear()
            history = core.get_history()
            history.sort(key=lambda x: x.get("date", ""), reverse=True)

            if not history:
                history_column.controls.append(
                    ft.Text(t("leave_manager_gui.no_items"), size=11, color=COLORS["text_muted"]))
                return

            for item in history[:30]:  # limit for performance
                icon = "➖" if item.get("amount", 0) < 0 else "➕"
                col = COLORS["danger"] if item.get("amount", 0) < 0 else COLORS["success"]
                tp = item.get("type", "")
                if len(tp) > 8:
                    tp = tp[:7] + ".."

                row = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(icon, size=12),
                            ft.Text(item.get("date", ""), size=11, weight=ft.FontWeight.BOLD,
                                    color=COLORS["text"]),
                            ft.Text(tp, size=11, color=COLORS["text_muted"]),
                            ft.Container(expand=True),
                            ft.Text(f"{abs(item.get('amount', 0))}d", size=11,
                                    weight=ft.FontWeight.BOLD, color=col),
                            ft.IconButton(
                                icon="close", icon_size=14, icon_color=COLORS["text_soft"],
                                tooltip=t("utilities_common.cancel"),
                                on_click=lambda e, _i=item: _delete_item(_i),
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                            ),
                            ft.IconButton(
                                icon="calendar_today", icon_size=14, icon_color=COLORS["text_soft"],
                                tooltip="Google Calendar",
                                on_click=lambda e, _i=item: _export_to_gcal(_i),
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=COLORS["surface"],
                    border_radius=8,
                    border=ft.border.all(1, COLORS["line"]),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                )
                history_column.controls.append(row)

        def _delete_item(item):
            core.delete_history_item_by_content(item)
            _refresh_all()

        def _export_to_gcal(item):
            Integrations.open_google_calendar(
                title=f"Vacance: {item.get('type', '')} ({item.get('note', '')})",
                date_str=item.get("date", ""),
                days=abs(item.get("amount", 0)),
            )

        # ══════════ UNDO/REDO ══════════

        def _undo(e):
            if core.undo():
                _refresh_all()

        def _redo(e):
            if core.redo():
                _refresh_all()

        # ══════════ REFRESH ALL ══════════

        def _refresh_all():
            _refresh_stats()
            _render_calendar()
            if state.history_expanded:
                _render_history()
            page.update()

        # ══════════ LAYOUT ══════════

        _refresh_stats()
        _render_calendar()

        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["app_bg"],
                padding=SPACING["md"],
                content=ft.Column(
                    expand=True,
                    spacing=SPACING["xs"],
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        # undo/redo header
                        ft.Row(
                            controls=[
                                ft.TextButton(
                                    content=ft.Text(f"↩️ {t('utilities_common.undo')}", size=11, color=COLORS["text_muted"]),
                                    on_click=_undo,
                                ),
                                ft.TextButton(
                                    content=ft.Text(f"↪️ {t('utilities_common.redo')}", size=11, color=COLORS["text_muted"]),
                                    on_click=_redo,
                                ),
                            ],
                            spacing=4,
                        ),
                        # stats card
                        stats_card,
                        # tabs
                        tabs_card,
                        # history
                        btn_history_toggle,
                        ft.Container(
                            content=history_column,
                            bgcolor=COLORS["surface"],
                            border_radius=RADII["md"],
                            border=ft.border.all(1, COLORS["line"]),
                            padding=SPACING["xs"],
                            visible=state.history_expanded,
                        ),
                        # calendar
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.IconButton(
                                                icon="chevron_left", icon_size=18,
                                                icon_color=COLORS["text"], on_click=_prev_month,
                                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                                            ),
                                            ft.Container(expand=True, content=cal_header_text,
                                                         alignment=ft.alignment.Alignment(0, 0)),
                                            ft.IconButton(
                                                icon="chevron_right", icon_size=18,
                                                icon_color=COLORS["text"], on_click=_next_month,
                                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                                            ),
                                        ],
                                    ),
                                    cal_grid,
                                ],
                                spacing=4,
                            ),
                            bgcolor=COLORS["surface"],
                            border_radius=RADII["md"],
                            border=ft.border.all(1, COLORS["line"]),
                            padding=SPACING["sm"],
                        ),
                    ],
                ),
            )
        )

    ft.app(target=main)
