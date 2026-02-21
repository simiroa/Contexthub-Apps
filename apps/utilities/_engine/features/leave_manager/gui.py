import customtkinter as ctk
import tkinter as tk
from datetime import datetime, date, timedelta
import sys
from pathlib import Path

# --- BOOTSTRAP ---
def _bootstrap():
    root = Path(__file__).resolve().parent
    while not (root / 'src').exists() and root.parent != root:
        root = root.parent
    if (root / 'src').exists():
        sys.path.append(str(root / 'src')) # Add src to path
        try: import utils.bootstrap
        except: pass
_bootstrap()
# -----------------

from contexthub.utils.i18n import t
from utils.gui_lib import (
    BaseWindow, THEME_BG, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, 
    THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER,
    THEME_TEXT_MAIN, THEME_TEXT_DIM
)

try:
    # Absolute imports (works if src is in path)
    from features.leave_manager.logic import LeaveManagerCore
    from features.leave_manager.storage import LeaveManagerStorage
    from features.leave_manager.services import Integrations
    from features.leave_manager.ui_components import YearlyProgressCard, VacationTicket, StatsBar
except ImportError:
    # Fallback for relative (if run as module without bootstrap needing help)
    from .logic import LeaveManagerCore
    from .storage import LeaveManagerStorage
    from .services import Integrations
    from .ui_components import YearlyProgressCard, VacationTicket, StatsBar

# Unified color constant
TICKET_BLUE = "#1a237e"
TICKET_BLUE_HOVER = "#0d47a1"
TICKET_BLUE_LIGHT = "#3949ab"

def is_already_running():
    import os
    import tempfile
    lock_file = os.path.join(tempfile.gettempdir(), "leave_manager.lock")
    try:
        if os.path.exists(lock_file):
            import time
            # Check if file is old or locked
            try:
                os.remove(lock_file)
            except:
                return True # Still locked
        
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        return False
    except:
        return False

class ToolTip:
    """Simple tooltip widget for showing hover information"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify='left',
                        background="#2b2b2b", foreground="white",
                        relief='solid', borderwidth=1,
                        font=("Arial", 9), padx=8, pady=4)
        label.pack()
    
    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class CustomCalendar(ctk.CTkFrame):
    def __init__(self, parent, on_date_click, on_date_right_click, get_events_func):
        super().__init__(parent, fg_color="transparent")
        self.on_date_click = on_date_click
        self.on_date_right_click = on_date_right_click
        self.get_events = get_events_func
        self.current_date = datetime.now()
        self.preview_dates = [] # List of "YYYY-MM-DD"
        
        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", pady=(0, 5))
        
        self.btn_prev = ctk.CTkButton(self.header, text="<", width=30, height=24, command=self.prev_month, fg_color="transparent", 
                                       border_width=1, border_color=THEME_BORDER, text_color=THEME_TEXT_MAIN)
        self.btn_prev.pack(side="left")
        
        self.lbl_month = ctk.CTkLabel(self.header, text="Month Year", font=("Arial", 14, "bold"), text_color=THEME_TEXT_MAIN)
        self.lbl_month.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.header, text=">", width=30, height=24, command=self.next_month, fg_color="transparent", 
                                       border_width=1, border_color=THEME_BORDER, text_color=THEME_TEXT_MAIN)
        self.btn_next.pack(side="right")
        
        # Grid
        self.grid_frame = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=12, border_width=1, border_color=THEME_BORDER)
        self.grid_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        days = [t("common.mon"), t("common.tue"), t("common.wed"), t("common.thu"), t("common.fri"), t("common.sat"), t("common.sun")]
        for i, d in enumerate(days):
            l = ctk.CTkLabel(self.grid_frame, text=d, font=("Arial", 10, "bold"), text_color=THEME_TEXT_DIM)
            l.grid(row=0, column=i, sticky="nsew", padx=1) # Shortened days

        for i in range(7): self.grid_frame.grid_columnconfigure(i, weight=1)
        
        self.day_buttons = []
        self.day_frames = [] # Keep track of frames for cleanup
        self.render()

    def set_preview_dates(self, dates):
        self.preview_dates = dates
        self.render()

    def prev_month(self):
        first = self.current_date.replace(day=1)
        prev = first - timedelta(days=1)
        self.current_date = prev
        self.render()

    def next_month(self):
        # rough next month logic
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year+1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month+1)
        self.render()

    def render(self):
        self.lbl_month.configure(text=self.current_date.strftime("%B %Y"))
        
        events = self.get_events(self.current_date.year, self.current_date.month)
        
        # Get holidays for the current year
        holidays_in_year = {}
        try:
            import holidays
            holidays_in_year = holidays.KR(years=self.current_date.year)
        except:
            pass
        
        # Logic to find start day and number of days
        year, month = self.current_date.year, self.current_date.month
        first_day = date(year, month, 1)
        start_weekday = first_day.weekday() # 0=Mon
        
        # Days in month
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        days_in_month = (next_month - first_day).days
        
        # Clear old widgets
        for f in self.day_frames:
            f.destroy()
        self.day_frames.clear()
        self.day_buttons.clear()
        
        row = 1
        col = start_weekday
        
        today_str = datetime.now().strftime("%Y-%m-%d")

        for d in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{d:02d}"
            
            fg = "transparent"
            border_color = THEME_BORDER
            border_width = 1
            text_color = THEME_TEXT_MAIN
            hover_color = THEME_DROPDOWN_HOVER
            
            # Weekend text color (Sat=col 5, Sun=col 6)
            # Check for holiday
            current_day_date = date(year, month, d)
            holiday_name = holidays_in_year.get(current_day_date)
            
            if col >= 5 or holiday_name:  # Saturday, Sunday or holiday
                text_color = "#ef5350"  # Red for weekend/holiday

            # Check events for this day
            day_events = events.get(d, [])
            
            # Type-based coloring (prioritize by checking types)
            if day_events:
                # Get first event's type for coloring (assuming one event per day after duplicate prevention)
                event_type = day_events[0].get("type", "").lower()
                amount = day_events[0].get("amount", 0)
                is_half = abs(amount) == 0.5  # Half-day check
                
                if amount < 0:  # Usage (not credit)
                    if "연차" in event_type or "annual" in event_type:
                        if is_half:
                            fg = "#5c9ce6"  # Light Blue - Annual 0.5
                            border_color = "#4a8ad4"
                        else:
                            fg = "#1976d2"  # Blue - Annual
                            border_color = "#1565c0"
                    elif "대체휴가" in event_type or "credit" in event_type:
                        if is_half:
                            fg = "#a5d6a7"  # Light Green - Credit usage 0.5
                            border_color = "#81c784"
                        else:
                            fg = "#66bb6a"  # Green - Credit usage
                            border_color = "#4caf50"
                    elif "병가" in event_type or "sick" in event_type:
                        if is_half:
                            fg = "#4dd0e1"  # Light Teal - Sick 0.5
                            border_color = "#26c6da"
                        else:
                            fg = "#00acc1"  # Teal - Sick
                            border_color = "#00838f"
                    else:
                        # Default to 연차 style
                        fg = "#1976d2"
                        border_color = "#1565c0"
                elif amount > 0:  # Credit added (alternative leave)
                    if is_half:
                        fg = "#a5d6a7"  # Light Green - Credit 0.5
                        border_color = "#81c784"
                    else:
                        fg = "#66bb6a"  # Green - Credit
                        border_color = "#4caf50"
            
            # Preview Override (gray for selection)
            if date_str in self.preview_dates:
                fg = "#616161"  # Gray for preview
                border_color = "#9e9e9e"
                text_color = "white"
            
            if date_str == today_str:
                border_color = TICKET_BLUE  # Unified ticket blue for today
                border_width = 2

            # Cell Container
            cell = ctk.CTkFrame(self.grid_frame, width=28, height=28, fg_color="transparent")
            cell.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")
            self.day_frames.append(cell)

            is_half = False
            if day_events:
                amount = day_events[0].get("amount", 0)
                is_half = abs(amount) == 0.5
            
            # Half-fill background
            if is_half:
                # Use solid color for the half fill
                fill_color = fg
                fill_frame = ctk.CTkFrame(cell, fg_color=fill_color, corner_radius=0)
                # Position it on the left half
                fill_frame.place(relx=0, rely=0, relwidth=0.5, relheight=1.0)
                fg = "transparent" # Make button transparent to show fill

            btn = ctk.CTkButton(
                cell,
                text=str(d),
                width=28, height=28,
                fg_color=fg,
                border_color=border_color,
                border_width=border_width,
                text_color=text_color,
                hover_color=hover_color,
                command=lambda ds=date_str: self.on_date_click(ds)
            )
            btn.place(relx=0, rely=0, relwidth=1, relheight=1)
            btn.bind("<Button-3>", lambda e, ds=date_str: self.on_date_right_click(ds))
            self.day_buttons.append(btn)
            
            # Add tooltip if there's an event or holiday
            if day_events or holiday_name:
                tooltip_text = ""
                if holiday_name:
                    tooltip_text += f"{t('leave_manager_gui.holiday')}: {holiday_name}\n"
                
                if day_events:
                    event = day_events[0]
                    tooltip_text += f"{event.get('type', 'Event')}\n{event.get('note', '')}"
                    if event.get('amount'):
                        tooltip_text += f"\n{t('leave_manager_gui.days_label')}: {abs(event.get('amount'))}"  
                
                if tooltip_text:
                    ToolTip(btn, tooltip_text.strip())
            
            col += 1
            if col > 6:
                col = 0
                row += 1

class LeaveManagerGUI(BaseWindow):
    def __init__(self):
        super().__init__(title="leave_manager_gui.title", width=500, height=850)
        
        self.storage = LeaveManagerStorage()
        self.core = LeaveManagerCore(self.storage)
        
        self.selected_date = datetime.now().strftime("%Y-%m-%d")
        self.selected_items = [] # For batch actions
        
        # Search & Filter variables
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._on_filter_changed())
        self.filter_type_var = ctk.StringVar(value="All")
        
        # --- UI Setup ---
        self._setup_ui()
        self._refresh_stats()

    def _setup_ui(self):
        # Header with Undo/Redo inside main_frame
        self.header_actions = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_actions.pack(fill="x", padx=15, pady=(0, 5))
        
        self.btn_undo = ctk.CTkButton(self.header_actions, text=f"↩️ {t('utilities_common.undo')}", width=70, height=22, font=("Arial", 10), 
                                       fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER, command=self._undo_handler)
        self.btn_undo.pack(side="left", padx=2)
        
        self.btn_redo = ctk.CTkButton(self.header_actions, text=f"↪️ {t('utilities_common.redo')}", width=70, height=22, font=("Arial", 10), 
                                       fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER, command=self._redo_handler)
        self.btn_redo.pack(side="left", padx=2)

        # 1. Yearly Progress Card
        self.yearly_card = YearlyProgressCard(self.main_frame)
        self.yearly_card.pack(fill="x", padx=15, pady=(5, 5))

        # 3. Main Action Tabs
        self.tabview = ctk.CTkTabview(self.main_frame, height=220, fg_color=THEME_CARD,
                                      segmented_button_selected_color=THEME_BTN_PRIMARY,
                                      segmented_button_selected_hover_color=THEME_BTN_HOVER,
                                      segmented_button_unselected_color=THEME_DROPDOWN_FG,
                                      segmented_button_unselected_hover_color=THEME_DROPDOWN_BTN,
                                      border_width=1, border_color=THEME_BORDER,
                                      text_color="#E0E0E0")
        self.tabview.pack(fill="x", padx=15, pady=(0, 3))
        
        self.tab_use = self.tabview.add(t("leave_manager_gui.use_leave_tab"))
        self.tab_add = self.tabview.add(t("leave_manager_gui.add_credit_tab"))
        self.tab_settings = self.tabview.add(t("leave_manager_gui.settings_tab"))
        
        self._build_use_tab()
        self._build_add_tab()
        self._build_settings_tab()
        
        # 4. History (Collapsible)
        self.history_expanded = False
        self.frame_history_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frame_history_container.pack(fill="x", padx=15, pady=0)
        
        self.btn_history_toggle = ctk.CTkButton(
            self.frame_history_container, 
            text=f"{t('leave_manager_gui.history')} ▼", 
            command=self._toggle_history,
            fg_color=THEME_CARD, 
            hover_color=THEME_DROPDOWN_HOVER,
            border_width=1,
            border_color=THEME_BORDER,
            height=28,
            anchor="w"
        )
        self.btn_history_toggle.pack(fill="x")
        
        self.frame_history_content = ctk.CTkScrollableFrame(self.frame_history_container, height=0, fg_color="transparent") # Initially hidden
        self.btn_export_all = ctk.CTkButton(self.frame_history_container, text=t("leave_manager_gui.export_csv"), 
                                            fg_color=THEME_CARD, hover_color=THEME_DROPDOWN_HOVER, 
                                            border_width=1, border_color=THEME_BORDER,
                                            height=24, command=self._export_all_handler)
        # content pack handled in toggle
        
        # 5. Calendar
        self.frame_calendar = ctk.CTkFrame(self.main_frame, fg_color=THEME_CARD, corner_radius=12, border_width=1, border_color=THEME_BORDER)
        self.frame_calendar.pack(fill="both", expand=True, padx=15, pady=(5, 10))
        
        self.calendar = CustomCalendar(self.frame_calendar, self._on_date_selected, self._on_date_right_click, self.core.get_events_for_month)
        self.calendar.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_use_tab(self):
        # Date
        row1 = ctk.CTkFrame(self.tab_use, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text=t("leave_manager_gui.date"), width=60, anchor="w").pack(side="left")
        
        self.ent_use_date_var = ctk.StringVar(value=self.selected_date)
        self.ent_use_date_var.trace_add("write", lambda *args: self._update_preview())
        
        self.ent_use_date = ctk.CTkEntry(row1, placeholder_text="YYYY-MM-DD", textvariable=self.ent_use_date_var,
                                        fg_color=THEME_DROPDOWN_FG, border_color=THEME_BORDER)
        self.ent_use_date.pack(side="left", fill="x", expand=True)
        
        # Type
        row2 = ctk.CTkFrame(self.tab_use, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text=t("leave_manager_gui.type"), width=60, anchor="w").pack(side="left")
        self.var_use_type = ctk.StringVar(value="Annual")
        self.cmb_use_type = ctk.CTkComboBox(row2, variable=self.var_use_type, values=self.core.get_leave_types(),
                                          fg_color=THEME_DROPDOWN_FG, border_color=THEME_BORDER,
                                          button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER,
                                          dropdown_fg_color=THEME_DROPDOWN_FG)
        self.cmb_use_type.pack(side="left", fill="x", expand=True)
        
        # Amount
        row3 = ctk.CTkFrame(self.tab_use, fg_color="transparent")
        row3.pack(fill="x", pady=5)
        ctk.CTkLabel(row3, text=t("leave_manager_gui.days_label"), width=60, anchor="w").pack(side="left")
        self.slider_use_amt = ctk.CTkSlider(row3, from_=0.5, to=5, number_of_steps=9, command=self._on_slider_change)
        self.slider_use_amt.set(1.0)
        self.slider_use_amt.pack(side="left", fill="x", expand=True, padx=5)
        self.lbl_use_amt_val = ctk.CTkLabel(row3, text="1.0", width=30)
        self.lbl_use_amt_val.pack(side="left")
        
        # Note
        row4 = ctk.CTkFrame(self.tab_use, fg_color="transparent")
        row4.pack(fill="x", pady=5)
        self.ent_use_note = ctk.CTkEntry(row4, placeholder_text=t("leave_manager_gui.reason_note"),
                                         fg_color=THEME_DROPDOWN_FG, border_color=THEME_BORDER)
        self.ent_use_note.pack(fill="x")
        
        # Button
        self.btn_use_confirm = ctk.CTkButton(self.tab_use, text=t("leave_manager_gui.use_leave_tab"), fg_color=TICKET_BLUE, hover_color=TICKET_BLUE_HOVER, command=self._submit_use)
        self.btn_use_confirm.pack(fill="x", pady=(10, 0))

    def _on_slider_change(self, value):
        self.lbl_use_amt_val.configure(text=f"{value:.1f}")
        self._update_preview()

    def _update_preview(self):
        # Only if Use tab is active? Or always if input has valid values
        # For simplicity, calculate based on field values
        date_str = self.ent_use_date_var.get()
        days = self.slider_use_amt.get()
        
        if len(date_str) == 10: # Rough validation "YYYY-MM-DD"
             preview = self.core.get_preview_dates(date_str, days)
             self.calendar.set_preview_dates(preview)
        else:
             self.calendar.set_preview_dates([])

    def _build_add_tab(self):
         # Date
        row1 = ctk.CTkFrame(self.tab_add, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text=t("leave_manager_gui.date"), width=60, anchor="w").pack(side="left")
        self.ent_add_date = ctk.CTkEntry(row1, placeholder_text="YYYY-MM-DD",
                                         fg_color=THEME_DROPDOWN_FG, border_color=THEME_BORDER)
        self.ent_add_date.insert(0, self.selected_date)
        self.ent_add_date.pack(side="left", fill="x", expand=True)
        
        # Type (Usually 'Overtime' or similar, but reuse list)
        row2 = ctk.CTkFrame(self.tab_add, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text=t("leave_manager_gui.type"), width=60, anchor="w").pack(side="left")
        self.ent_add_type = ctk.CTkEntry(row2, placeholder_text="Credit Type (e.g. Overtime)",
                                         fg_color=THEME_DROPDOWN_FG, border_color=THEME_BORDER)
        self.ent_add_type.insert(0, t("leave_manager_gui.credit_leave"))
        self.ent_add_type.pack(side="left", fill="x", expand=True)

        # Amount
        row3 = ctk.CTkFrame(self.tab_add, fg_color="transparent")
        row3.pack(fill="x", pady=5)
        ctk.CTkLabel(row3, text=t("leave_manager_gui.days_label"), width=60, anchor="w").pack(side="left")
        self.slider_add_amt = ctk.CTkSlider(row3, from_=0.5, to=5, number_of_steps=9, command=lambda v: self.lbl_add_amt_val.configure(text=f"{v:.1f}"))
        self.slider_add_amt.set(1.0)
        self.slider_add_amt.pack(side="left", fill="x", expand=True, padx=5)
        self.lbl_add_amt_val = ctk.CTkLabel(row3, text="1.0", width=30)
        self.lbl_add_amt_val.pack(side="left")
        
        # Button
        self.btn_add_confirm = ctk.CTkButton(self.tab_add, text=t("leave_manager_gui.add_credit_tab"), fg_color="#388E3C", hover_color="#1B5E20", command=self._submit_add)
        self.btn_add_confirm.pack(fill="x", pady=(20, 0))

        # Report Button (✨)
        self.btn_report = ctk.CTkButton(self.tab_add, text=t("leave_manager.export_report"), 
                                         fg_color="#1A237E", hover_color="#0D47A1", 
                                         command=self._export_html_report)
        self.btn_report.pack(fill="x", pady=(10, 0))

    def _build_settings_tab(self):
        # Settings Fields
        self.frame_settings_fields = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.frame_settings_fields.pack(fill="x", pady=5)
        
        settings = self.core.get_settings()
        
        self.ent_total_days = self._add_setting_row(t("leave_manager_gui.given_days"), str(settings.get("total_days", 15.0)))
        self.ent_reset_date = self._add_setting_row(t("leave_manager_gui.reset_date"), str(settings.get("reset_date", "01-01")))
        self.ent_exp_date = self._add_setting_row(t("leave_manager_gui.expiry"), str(settings.get("expiration_date", "")))



        # Save Button
        ctk.CTkButton(self.tab_settings, text=t("leave_manager_gui.save_settings"), command=self._save_settings_handler).pack(fill="x", pady=15)

        # Data Management
        ctk.CTkLabel(self.tab_settings, text=t("leave_manager_gui.data_management"), font=("Arial", 12, "bold")).pack(pady=(10, 5), anchor="w")
        row_data = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        row_data.pack(fill="x")
        ctk.CTkButton(row_data, text=t("leave_manager_gui.import_data"), width=80, command=self._import_data_handler).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ctk.CTkButton(row_data, text=t("leave_manager_gui.export_data"), width=80, command=self._export_data_handler).pack(side="left", expand=True, fill="x", padx=(2, 0))

    def _add_setting_row(self, label, value):
        f = ctk.CTkFrame(self.frame_settings_fields, fg_color="transparent")
        f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=label, width=80, anchor="w").pack(side="left")
        e = ctk.CTkEntry(f, fg_color=THEME_DROPDOWN_FG, border_color=THEME_BORDER)
        e.insert(0, value)
        e.pack(side="left", fill="x", expand=True)
        return e

    def _toggle_history(self):
        if self.history_expanded:
            self.frame_history_content.pack_forget()
            self.frame_history_controls.pack_forget() # Hide search/filter
            self.btn_export_all.pack_forget()
            self.frame_history_content.configure(height=0) 
            self.btn_history_toggle.configure(text=f"{t('leave_manager_gui.history')} ▼")
            self.history_expanded = False
        else:
            self._build_history_controls()
            self.frame_history_content.pack(fill="both", expand=True, padx=5, pady=5)
            self.btn_export_all.pack(fill="x", padx=5, pady=(0, 5))
            self.frame_history_content.configure(height=200) 
            self.btn_history_toggle.configure(text=f"{t('leave_manager_gui.history')} ▲")
            self._render_history_list()
            self.history_expanded = True

    def _build_history_controls(self):
        if hasattr(self, 'frame_history_controls'):
            self.frame_history_controls.pack(fill="x", padx=5, pady=(5, 0))
            return

        self.frame_history_controls = ctk.CTkFrame(self.frame_history_container, fg_color="transparent")
        self.frame_history_controls.pack(fill="x", padx=5, pady=(5, 0))

        # Search
        self.ent_search = ctk.CTkEntry(self.frame_history_controls, placeholder_text=t("common.search") + "...", 
                                        textvariable=self.search_var, height=24, font=("Arial", 11),
                                        fg_color=THEME_DROPDOWN_FG, border_color=THEME_BORDER)
        self.ent_search.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Filter Type
        types = [t("common.all")] + self.core.get_leave_types()
        self.cmb_filter_type = ctk.CTkComboBox(self.frame_history_controls, values=types, 
                                                variable=self.filter_type_var, width=100, height=24, 
                                                font=("Arial", 11), command=lambda v: self._on_filter_changed(),
                                                fg_color=THEME_DROPDOWN_FG, border_color=THEME_BORDER,
                                                button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER,
                                                dropdown_fg_color=THEME_DROPDOWN_FG)
        self.cmb_filter_type.pack(side="right")

    def _on_filter_changed(self):
        if self.history_expanded:
            self._render_history_list()

    def _undo_handler(self):
        if self.core.undo():
            self._on_action_complete()
            
    def _redo_handler(self):
        if self.core.redo():
            self._on_action_complete()
            
    def _export_all_handler(self):
        filename = f"vacance_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        # In a real app, use filedialog.asksaveasfilename
        # For this quick implementation, saving to user dir or current dir is fine, 
        # but ask_save_as is better.
        try:
            from tkinter import filedialog
            f = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=filename)
            if f:
                if self.core.export_history_to_csv(f):
                    tk.messagebox.showinfo("Export", f"Successfully exported to {f}")
                else:
                    tk.messagebox.showerror("Export", "Failed to export data.")
        except:
            pass

    def _render_history_list(self):
        for w in self.frame_history_content.winfo_children(): w.destroy()
        
        history = self.core.get_history()
        # Apply Search & Filter
        search_q = self.search_var.get().lower()
        filter_type = self.filter_type_var.get()

        filtered_history = []
        for item in history:
            if filter_type != "All" and item.get("type") != filter_type:
                continue
            if search_q and search_q not in item.get("note", "").lower() and search_q not in item.get("date", ""):
                continue
            filtered_history.append(item)

        # Sort by date desc
        filtered_history.sort(key=lambda x: x["date"], reverse=True)

        if not filtered_history:
            ctk.CTkLabel(self.frame_history_content, text=t("leave_manager_gui.no_items")).pack(pady=10)
            return

        # Batch Action Bar
        batch_bar = ctk.CTkFrame(self.frame_history_content, fg_color="transparent")
        batch_bar.pack(fill="x", pady=2)
        
        self.batch_vars = {} # item_timestamp -> IntVar

        def toggle_all():
            val = all_var.get()
            for v in self.batch_vars.values():
                v.set(val)

        all_var = tk.IntVar(value=0)
        ctk.CTkCheckBox(batch_bar, text="", variable=all_var, command=toggle_all, width=20).pack(side="left", padx=5)
        
        ctk.CTkButton(batch_bar, text="🗑️", width=30, height=24, fg_color="#C62828", hover_color="#B71C1C", 
                       command=self._batch_delete).pack(side="right", padx=2)
        ctk.CTkButton(batch_bar, text="📅 Sync", width=60, height=24, fg_color=TICKET_BLUE, hover_color=TICKET_BLUE_HOVER,
                       command=self._batch_sync).pack(side="right", padx=2)
        ctk.CTkButton(batch_bar, text="💾 ICS", width=60, height=24, fg_color="#455A64", hover_color="#37474F",
                       command=self._batch_ics_export).pack(side="right", padx=2)

        for idx, item in enumerate(filtered_history):
            timestamp = item.get("timestamp", f"{item['date']}_{idx}")
            var = tk.IntVar(value=0)
            self.batch_vars[timestamp] = var

            f = ctk.CTkFrame(self.frame_history_content, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
            f.pack(fill="x", pady=2)
            
            ctk.CTkCheckBox(f, text="", variable=var, width=20).pack(side="left", padx=5)
            
            icon = "➖" if item["amount"] < 0 else "➕"
            col = "#EF5350" if item["amount"] < 0 else "#66BB6A"
            
            ctk.CTkLabel(f, text=icon, width=20).pack(side="left")
            ctk.CTkLabel(f, text=item["date"], font=("Arial", 11, "bold")).pack(side="left", padx=5)
            # Shorten type if needed
            type_text = item['type']
            if len(type_text) > 8: type_text = type_text[:7] + ".."
            ctk.CTkLabel(f, text=type_text, font=("Arial", 11)).pack(side="left", padx=5)
            
            ctk.CTkLabel(f, text=f"{abs(item['amount'])}d", text_color=col, font=("Arial", 11, "bold")).pack(side="right", padx=10)
            
            # Delete button (Small 'x')
            btn_del = ctk.CTkButton(f, text="×", width=24, height=24, fg_color="transparent", hover_color="gray30",
                                    command=lambda i=item: self._delete_history_item(i))
            btn_del.pack(side="right")
            
            # Export button (Calendar icon placeholder)
            btn_exp = ctk.CTkButton(f, text="📅", width=24, height=24, fg_color="transparent", hover_color="gray30",
                                    command=lambda i=item: self._export_item(i))
            btn_exp.pack(side="right")

    def _get_selected_items(self):
        history = self.core.get_history()
        selected = []
        for item in history:
            ts = item.get("timestamp")
            if ts in self.batch_vars and self.batch_vars[ts].get() == 1:
                selected.append(item)
        return selected

    def _batch_delete(self):
        items = self._get_selected_items()
        if not items: return
        if tk.messagebox.askyesno(t("common.delete"), t("common.delete_confirm").format(len(items))):
            for item in items:
                self.core.delete_history_item_by_content(item)
            self._on_action_complete()

    def _batch_sync(self):
        items = self._get_selected_items()
        if not items: return
        # Logic for sync to Google Calendar (open multiple tabs or sequence)
        # For now, let's just open them sequentially (might be too many tabs if not careful)
        if len(items) > 5:
            if not tk.messagebox.askyesno("Sync", f"Sync {len(items)} items to Calendar?\nThis will open multiple browser tabs."):
                return
        
        for item in items:
            self._export_item(item)

    def _batch_ics_export(self):
        items = self._get_selected_items()
        if not items: return
        
        from tkinter import filedialog
        filename = f"leave_history_{datetime.now().strftime('%Y%m%d')}.ics"
        f = filedialog.asksaveasfilename(defaultextension=".ics", initialfile=filename, title="Export to ICS")
        if f:
            # We need to temporarily pass the selected items to the logic export
            # Since logic.py uses get_history(), we might need a temporary override or 
            # we can filter the resulting ICS file. 
            # For simplicity, let's implement a specific method in logic.py if needed, 
            # but currently it exports ALL history. 
            # The USER requested "whole history" in the task.md for ICS.
            if self.core.export_history_to_ics(f):
                tk.messagebox.showinfo("Export", f"Successfully exported to {f}")
            else:
                tk.messagebox.showerror("Export", "Failed to export ICS.")

    def _export_html_report(self):
        from tkinter import filedialog
        import webbrowser
        import os
        
        filename = f"leave_report_{datetime.now().strftime('%Y%m%d')}.html"
        f = filedialog.asksaveasfilename(defaultextension=".html", initialfile=filename, title="Export Modern Report")
        if f:
            if self.core.generate_html_report(f):
                if tk.messagebox.askyesno("Export", f"Successfully exported to {f}\nOpen in browser?"):
                    webbrowser.open(f"file:///{os.path.abspath(f)}")
            else:
                tk.messagebox.showerror("Export", "Failed to generate report.")

    def _refresh_stats(self):
        stats = self.core.calculate_balance()
        if hasattr(self, 'yearly_card'):
            self.yearly_card.update_stats(stats)
        
        self.calendar.render()

    def _on_date_selected(self, date_str):
        self.selected_date = date_str
        # Update inputs
        self.ent_use_date_var.set(date_str)
        self.ent_add_date.delete(0, "end")
        self.ent_add_date.insert(0, date_str)

    def _on_date_right_click(self, date_str):
        events = self.core.get_events_for_month(
            datetime.strptime(date_str, "%Y-%m-%d").year,
            datetime.strptime(date_str, "%Y-%m-%d").month
        ).get(int(date_str.split("-")[2]), [])
        
        if not events:
            return
            
        confirm = tk.messagebox.askyesno(
            t("common.delete"),
            t("leave_manager_gui.delete_confirm").format(date_str)
        )
        
        if confirm:
            # Delete all events on this date
            for event in events:
                self.core.delete_history_item_by_content(event)
            self._on_action_complete()

    def _submit_use(self):
        d = self.ent_use_date_var.get()
        t = self.var_use_type.get()
        a = self.slider_use_amt.get()
        n = self.ent_use_note.get()
        
        # Check credit balance if using 대체휴가
        if "대체휴가" in t or "credit" in t.lower():
            stats = self.core.calculate_balance()
            credit_available = stats.get("total_added", 0)
            
            # Calculate how much credit is already used
            credit_used = 0.0
            for item in self.core.get_history():
                item_type = item.get("type", "").lower()
                amt = item.get("amount", 0)
                if ("대체휴가" in item_type or "credit" in item_type) and amt < 0:
                    credit_used += abs(amt)
            
            credit_remaining = credit_available - credit_used
            
            if credit_remaining < a:
                tk.messagebox.showwarning(
                    t("leave_manager_gui.insufficient_credit"), 
                    t("leave_manager_gui.insufficient_credit_msg").format(credit_remaining, a)
                )
                return
        
        # Get all dates in the range
        dates = self.core.get_preview_dates(d, a)
        
        if not dates:
            return
        
        # Calculate per-day deduction
        # For whole days: each day gets -1.0
        # For partial: first days get -1.0, last day gets the remainder
        days_count = len(dates)
        whole_days = int(a)
        remainder = a - whole_days
        
        # Register each day individually
        for i, date_str in enumerate(dates):
            if i < whole_days:
                # Full days get -1.0
                amount = -1.0
            else:
                # Last partial day gets the remainder
                amount = -remainder if remainder > 0 else 0
            
            if amount != 0:  # Only register if there's an amount
                self.core.add_history_item(date_str, t, amount, n)
        
        self._on_action_complete()

    def _submit_add(self):
        d = self.ent_add_date.get()
        t = self.ent_add_type.get()
        a = self.slider_add_amt.get() # Positive
        n = "Credit Added"
        self.core.add_history_item(d, t, a, n)
        self._on_action_complete()

    def _on_action_complete(self):
        self._refresh_stats()
        if self.history_expanded:
            self._render_history_list()
        
    def _delete_history_item(self, item):
        self.core.delete_history_item_by_content(item)
        self._on_action_complete()
        
    def _export_item(self, item):
        # Google Calendar Export
        Integrations.open_google_calendar(
            title=f"Vacance: {item['type']} ({item['note']})",
            date_str=item['date'],
            days=abs(item['amount'])
        )



    def _save_settings_handler(self):
        try:
            self.core.save_settings(
                total_days=float(self.ent_total_days.get()),
                reset_date=self.ent_reset_date.get(),
                expiration_date=self.ent_exp_date.get()
            )
            self._refresh_stats()
        except ValueError:
            pass # Invalid number

    def _export_data_handler(self):
        filename = f"vacance_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            from tkinter import filedialog
            f = filedialog.asksaveasfilename(defaultextension=".json", initialfile=filename, title=t("leave_manager_gui.export_data"))
            if f:
                if self.core.storage.export_all_data(f):
                    tk.messagebox.showinfo(t("leave_manager_gui.export_success"), t("leave_manager_gui.export_success_msg", path=f))
                else:
                    tk.messagebox.showerror(t("leave_manager_gui.export_fail"), t("leave_manager_gui.export_fail_msg"))
        except Exception as e:
            tk.messagebox.showerror("Error", str(e))

    def _import_data_handler(self):
        if not tk.messagebox.askyesno(t("leave_manager_gui.confirm_import"), t("leave_manager_gui.confirm_import_msg")):
            return
            
        try:
            from tkinter import filedialog
            f = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], title=t("leave_manager_gui.import_data"))
            if f:
                if self.core.storage.import_all_data(f):
                    tk.messagebox.showinfo(t("leave_manager_gui.import_success"), t("leave_manager_gui.import_success_msg"))
                    self._refresh_stats()
                    self._render_history_list()
                    # Settings Input Refresh
                    settings = self.core.get_settings()
                    self.ent_total_days.delete(0, "end")
                    self.ent_total_days.insert(0, str(settings.get("total_days", 15.0)))
                    self.ent_reset_date.delete(0, "end")
                    self.ent_reset_date.insert(0, str(settings.get("reset_date", "01-01")))
                else:
                    tk.messagebox.showerror(t("leave_manager_gui.import_fail"), t("leave_manager_gui.import_fail_msg"))
        except Exception as e:
            tk.messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    if is_already_running():
        tk.messagebox.showwarning("Warning", "Leave Manager is already running.")
        sys.exit()
    app = LeaveManagerGUI()
    app.mainloop()
