import customtkinter as ctk
from datetime import datetime
import tkinter as tk
import sys
from pathlib import Path

# --- BOOTSTRAP ---
def _bootstrap():
    root = Path(__file__).resolve().parent
    while not (root / 'src').exists() and root.parent != root:
        root = root.parent
    if (root / 'src').exists():
        if str(root / 'src') not in sys.path:
            sys.path.append(str(root / 'src'))
        try: import utils.bootstrap
        except: pass
_bootstrap()
# -----------------

from utils.i18n import t
from utils.gui_lib import THEME_CARD, THEME_BG, THEME_TEXT_MAIN, THEME_TEXT_DIM, THEME_BORDER

class YearlyProgressCard(ctk.CTkFrame):
    """휴가 현황 카드 - 테마 지원"""
    
    # (Light, Dark)
    COLOR_ANNUAL = ("#1976D2", "#42a5f5")
    COLOR_CREDIT = ("#388E3C", "#66bb6a")
    COLOR_SICK = ("#0097A7", "#26c6da")
    COLOR_BG = ("#E0E0E0", THEME_BG)
    COLOR_TEXT = ("#212121", THEME_TEXT_MAIN)
    COLOR_SUB = ("#757575", THEME_TEXT_DIM)
    COLOR_SUB_DARK = ("#9E9E9E", "#555")
    
    def __init__(self, parent, stats=None):
        super().__init__(parent, fg_color=THEME_CARD, corner_radius=12, border_width=1, border_color=THEME_BORDER)
        self.configure(height=130)
        self.pack_propagate(False)
        
        # 타이틀
        ctk.CTkLabel(
            self, 
            text=t("leave_manager_gui.status_title", year=datetime.now().year),
            font=("Arial", 12, "bold"), 
            text_color=self.COLOR_TEXT
        ).pack(anchor="w", padx=15, pady=(8, 5))
        
        # 통계 영역
        stats_container = ctk.CTkFrame(self, fg_color="transparent")
        stats_container.pack(fill="x", padx=15, pady=(0, 5))
        
        # === 연차 (왼쪽) ===
        left_box = ctk.CTkFrame(stats_container, fg_color="transparent")
        left_box.pack(side="left", expand=True)
        
        left_row = ctk.CTkFrame(left_box, fg_color="transparent")
        left_row.pack()
        
        ctk.CTkLabel(left_row, text=t("leave_manager_gui.annual_leave") + " ", font=("Arial", 14, "bold"), text_color=self.COLOR_SUB).pack(side="left", pady=(4, 0))
        
        self.lbl_annual = ctk.CTkLabel(left_row, text="11.0", font=("Arial", 28, "bold"), text_color=self.COLOR_ANNUAL)
        self.lbl_annual.pack(side="left")
        
        self.lbl_annual_total = ctk.CTkLabel(left_row, text="/17", font=("Arial", 16), text_color=self.COLOR_SUB_DARK)
        self.lbl_annual_total.pack(side="left", pady=(4, 0))
        
        # 구분선
        sep = ctk.CTkFrame(stats_container, width=1, height=40, fg_color=("#E0E0E0", THEME_BORDER))
        sep.pack(side="left", padx=10)
        
        # === 대체휴가 (오른쪽) ===
        right_box = ctk.CTkFrame(stats_container, fg_color="transparent")
        right_box.pack(side="left", expand=True)
        
        right_row = ctk.CTkFrame(right_box, fg_color="transparent")
        right_row.pack()
        
        ctk.CTkLabel(right_row, text=t("leave_manager_gui.credit_leave") + " ", font=("Arial", 14, "bold"), text_color=self.COLOR_SUB).pack(side="left", pady=(4, 0))
        
        self.lbl_credit = ctk.CTkLabel(right_row, text="1.5", font=("Arial", 28, "bold"), text_color=self.COLOR_CREDIT)
        self.lbl_credit.pack(side="left")
        
        self.lbl_credit_total = ctk.CTkLabel(right_row, text="/1.5", font=("Arial", 16), text_color=self.COLOR_SUB_DARK)
        self.lbl_credit_total.pack(side="left", pady=(4, 0))
        
        # 프로그레스 바
        self.bar = ctk.CTkFrame(self, height=8, corner_radius=4, fg_color=self.COLOR_BG)
        self.bar.pack(fill="x", padx=15, pady=(0, 5))
        self.bar.pack_propagate(False)
        self.bar_segments = []
        
        # 병가
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=15, pady=(0, 8))
        ctk.CTkFrame(footer, width=8, height=8, corner_radius=4, fg_color=self.COLOR_SICK).pack(side="left")
        self.lbl_sick = ctk.CTkLabel(footer, text=f" {t('leave_manager_gui.sick_leave')}: 0{t('leave_manager_gui.days')}", font=("Arial", 10), text_color=self.COLOR_SUB)
        self.lbl_sick.pack(side="left")
        
        if stats:
            self.update_stats(stats)
    
    def update_stats(self, stats):
        annual = stats.get("annual", {"total": 15, "used": 0, "remaining": 15})
        credit = stats.get("credit", {"total": 0, "used": 0, "remaining": 0})
        sick = stats.get("sick", {"used": 0})
        
        # 연차
        self.lbl_annual.configure(text=f"{annual['remaining']:.1f}")
        self.lbl_annual_total.configure(text=f"/{annual['total']:.0f}")
        
        if annual['remaining'] < 0:
            self.lbl_annual.configure(text_color=("#D32F2F", "#ef5350")) # Red
        elif annual['remaining'] <= 3:
            self.lbl_annual.configure(text_color=("#F57C00", "#ffa726")) # Orange
        else:
            self.lbl_annual.configure(text_color=self.COLOR_ANNUAL)
        
        # 대체휴가
        self.lbl_credit.configure(text=f"{credit['remaining']:.1f}")
        self.lbl_credit_total.configure(text=f"/{credit['total']:.1f}")
        
        # 병가
        self.lbl_sick.configure(text=f" {t('leave_manager_gui.sick_leave')}: {sick['used']:.1f}{t('leave_manager_gui.days')}")
        
        self.after(10, lambda: self._draw_bar(annual, credit, sick))
    
    def _draw_bar(self, annual, credit, sick):
        w = self.bar.winfo_width()
        if w <= 1:
            self.after(50, lambda: self._draw_bar(annual, credit, sick))
            return
        
        for seg, _ in self.bar_segments:
            seg.destroy()
        self.bar_segments.clear()
        
        total = annual['total'] + credit['total']
        if total <= 0:
            return
        
        for amt, color in [(annual['used'], self.COLOR_ANNUAL), 
                           (credit['used'], self.COLOR_CREDIT),
                           (sick['used'], self.COLOR_SICK)]:
            if amt > 0:
                # Color tuple handling required? 
                # CTkFrame fg_color accepts tuple.
                seg = ctk.CTkFrame(self.bar, fg_color=color, corner_radius=0)
                seg.pack(side="left", fill="y")
                seg.configure(width=max(2, int(w * amt / total)))
                self.bar_segments.append((seg, None))


# 하위 호환성
class StatsBar(ctk.CTkFrame):
    def __init__(self, parent, stats=None):
        super().__init__(parent, fg_color="transparent", height=0)
    def update_stats(self, stats):
        pass

class VacationTicket(ctk.CTkFrame):
    def __init__(self, parent, next_vacation=None):
        super().__init__(parent, fg_color="transparent", height=0)
    def update_ticket(self, next_vacation):
        pass
