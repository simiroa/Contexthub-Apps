import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import customtkinter as ctk
from PIL import Image, ImageTk
import math

# Shim for local/installed runtime
try:
    from utils import gui_lib
    from utils.gui_lib import (
        BaseWindow, THEME_ACCENT, THEME_CARD, THEME_TEXT_MAIN, 
        THEME_BORDER, THEME_TEXT_DIM, THEME_BG, THEME_BTN_DANGER, THEME_BTN_SUCCESS,
        ask_string_modern
    )
except ImportError:
    BaseWindow = ctk.CTk
    THEME_ACCENT = "#0123B4"
    THEME_CARD = "#121212"
    THEME_TEXT_MAIN = "#E0E0E0"
    THEME_BORDER = "#1a1a1a"
    THEME_TEXT_DIM = "#666666"
    THEME_BG = "#050505"
    THEME_BTN_DANGER = "#C0392B"
    THEME_BTN_SUCCESS = "#27AE60"
    def ask_string_modern(t, x): return simpledialog.askstring(t, x)

from db_handler import DBHandler
from export_util import ExportUtil
from ai_handler import AIHandler

ctk.set_appearance_mode("Dark")

PRODUCT_COLORS = ["#3498DB", "#E74C3C", "#2ECC71", "#F1C40F", "#9B59B6"]

PRESETS = {
    "Smartphone": [("Price", "number", 1, -1, "$"), ("Display Size", "number", 2, 1, '"'), ("Battery", "number", 2, 1, "mAh"), ("Cam Pixels", "number", 3, 1, "MP"), ("Weight", "number", 1, -1, "g")],
    "Car": [("Price", "number", 1, -1, "$"), ("Efficiency", "number", 3, 1, "km/l"), ("Zero-100", "number", 2, -1, "sec"), ("Safety", "number", 3, 1, "/10"), ("Space", "number", 2, 1, "/10")],
    "Travel": [("Daily Cost", "number", 1, -1, "$"), ("Distance", "number", 1, -1, "km"), ("Attractions", "number", 3, 1, "/10"), ("Safety", "number", 3, 1, "/10"), ("Food Score", "number", 3, 1, "/10")],
    "Bag": [("Price", "number", 1, -1, "$"), ("Weight", "number", 1, -1, "kg"), ("Volume", "number", 2, 1, "L"), ("Durability", "number", 3, 1, "/10")],
    "Computer": [("Price", "number", 1, -1, "$"), ("CPU Perf", "number", 3, 1, "pts"), ("RAM", "number", 2, 1, "GB"), ("Weight", "number", 1, -1, "kg")],
    "Lens": [("Price", "number", 1, -1, "$"), ("Aperture", "number", 2, 1, "f/"), ("Weight", "number", 1, -1, "g"), ("Sharpness", "number", 3, 1, "/10")],
    "Empty": []
}

class RadarChart(ctk.CTkCanvas):
    def __init__(self, master, size=150, show_labels=False, **kwargs):
        super().__init__(master, width=size, height=size, bg=THEME_BG, highlightthickness=0, **kwargs)
        self.size = size
        self.center = size / 2
        self.radius = (size / 2) * 0.7 if show_labels else (size / 2) * 0.85
        self.show_labels = show_labels

    def draw(self, products, criteria, val_map, scores):
        self.delete("all")
        if not criteria or not products: return
        active_criteria = [c for c in criteria if not (len(c) > 6 and c[6])]
        num_active = len(active_criteria)
        if num_active < 3:
            self.create_text(self.center, self.center, text="Need 3+ active", fill=THEME_TEXT_DIM, font=ctk.CTkFont(size=8))
            return
        angle_step = (2 * math.pi) / num_active
        for i in range(1, 6):
            r = (self.radius / 5) * i
            points = []
            for j in range(num_active):
                angle = j * angle_step - math.pi / 2
                x = self.center + r * math.cos(angle); y = self.center + r * math.sin(angle)
                points.extend([x, y])
            self.create_polygon(points, outline="#222222", fill="", width=1)
        for j in range(num_active):
            angle = j * angle_step - math.pi / 2
            x = self.center + self.radius * math.cos(angle); y = self.center + self.radius * math.sin(angle)
            self.create_line(self.center, self.center, x, y, fill="#222222")
            if self.show_labels:
                lx = self.center + (self.radius + 15) * math.cos(angle); ly = self.center + (self.radius + 15) * math.sin(angle)
                text = active_criteria[j][2]
                if len(text) > 8: text = text[:6] + ".."
                self.create_text(lx, ly, text=text, fill=THEME_TEXT_MAIN, font=ctk.CTkFont(size=9))
        crit_stats = {}
        for crit in active_criteria:
            vals = []
            for prod in products:
                raw = val_map.get((prod[0], crit[0]), "")
                try: vals.append(float(raw))
                except: pass
            if vals: crit_stats[crit[0]] = (min(vals), max(vals))
        for i, prod in enumerate(products[:5]):
            points = []
            color = PRODUCT_COLORS[i % len(PRODUCT_COLORS)]
            for j, crit in enumerate(active_criteria):
                angle = j * angle_step - math.pi / 2
                raw = val_map.get((prod[0], crit[0]), "")
                try:
                    val = float(raw)
                    c_min, c_max = crit_stats.get(crit[0], (0, 1))
                    norm = (val - c_min) / (c_max - c_min) if c_max != c_min else 0.5
                    if len(crit) > 5 and crit[5] == -1: norm = 1.0 - norm
                except: norm = 0
                r = norm * self.radius
                x = self.center + r * math.cos(angle); y = self.center + r * math.sin(angle)
                points.extend([x, y])
                if not self.show_labels: # Mini-Radar: Add vertex dots for polish
                    self.create_oval(x-2, y-2, x+2, y+2, fill=color, outline=color)
            if len(points) >= 6:
                self.create_polygon(points, outline=color, fill=color, stipple="gray25" if not self.show_labels else "", width=2)

class PresetDialog(ctk.CTkToplevel):
    def __init__(self, master, on_confirm):
        super().__init__(master)
        self.title("Select Preset")
        self.geometry("300x400")
        self.on_confirm = on_confirm
        self.attributes("-topmost", True)
        self.resizable(False, False)
        
        ctk.CTkLabel(self, text="Choose a Preset", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        self.choice = tk.StringVar(value="Empty")
        
        for name in PRESETS.keys():
            ctk.CTkRadioButton(self, text=name, variable=self.choice, value=name).pack(pady=10)
            
        ctk.CTkButton(self, text="Create", fg_color=THEME_ACCENT, command=self.confirm).pack(pady=30)
        
    def confirm(self):
        self.on_confirm(self.choice.get())
        self.destroy()

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_select, on_new, on_export, on_delete, on_reset, on_ai, **kwargs):
        super().__init__(master, width=220, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER, **kwargs)
        self.on_select = on_select
        self.on_new = on_new
        self.on_export = on_export
        self.on_delete = on_delete
        self.on_reset = on_reset
        self.on_ai = on_ai
        self.pack_propagate(False)
        
        lbl_f = ctk.CTkFrame(self, fg_color="transparent")
        lbl_f.pack(fill="x", padx=15, pady=20)
        ctk.CTkLabel(lbl_f, text="PROJECTS", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME_TEXT_DIM).pack(side="left")
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=5)
        
        self.btn_f = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_f.pack(fill="x", side="bottom", padx=10, pady=15)
        
        ctk.CTkButton(self.btn_f, text="+ New Project", fg_color=THEME_ACCENT, height=35, command=self.on_new).pack(fill="x", pady=2)
        ctk.CTkButton(self.btn_f, text="AI Assistant (Beta)", fg_color="#6366f1", height=35, command=self.on_ai).pack(fill="x", pady=2)
        ctk.CTkButton(self.btn_f, text="Export Project", fg_color=THEME_BTN_SUCCESS, height=35, command=self.on_export).pack(fill="x", pady=2)
        ctk.CTkButton(self.btn_f, text="Reset All Data", fg_color="transparent", border_width=1, border_color=THEME_BTN_DANGER, text_color=THEME_TEXT_DIM, height=30, font=ctk.CTkFont(size=10), command=self.on_reset).pack(fill="x", pady=(10, 0))

    def on_reset(self):
        if messagebox.askyesno("Reset All", "Delete ALL projects and start clean?"):
            self.master.master.master.db.clear_all_data() # Access app db
            self.master.master.master.init_data()

    def refresh(self, projects, active_id):
        for w in self.scroll.winfo_children(): w.destroy()
        for p in projects:
            is_active = p[0] == active_id
            bg = THEME_ACCENT if is_active else "transparent"
            item_f = ctk.CTkFrame(self.scroll, fg_color="transparent")
            item_f.pack(fill="x", pady=1)
            
            btn = ctk.CTkButton(item_f, text=p[1], fg_color=bg, text_color=THEME_TEXT_MAIN, anchor="w", height=38, corner_radius=6, command=lambda pid=p[0]: self.on_select(pid))
            btn.pack(side="left", fill="x", expand=True, padx=(2, 0))
            
            del_btn = ctk.CTkButton(item_f, text="✕", width=25, height=25, fg_color="transparent", hover_color=THEME_BTN_DANGER, text_color=THEME_TEXT_DIM, command=lambda pid=p[0]: self.on_delete(pid))
            del_btn.pack(side="right", padx=5)
            
            # Hover visibility for delete button
            del_btn.pack_forget()
            item_f.bind("<Enter>", lambda e, db=del_btn: db.pack(side="right", padx=5))
            item_f.bind("<Leave>", lambda e, db=del_btn: db.pack_forget())

class CriterionPopup(ctk.CTkToplevel):
    def __init__(self, master, criterion, on_save, on_delete, x, y):
        super().__init__(master)
        self.title("Settings")
        self.geometry(f"280x480+{x}+{y}")
        self.criterion = criterion
        self.on_save = on_save
        self.on_delete = on_delete
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        # Safe extraction of database values (handle None)
        c_name = criterion[2] if criterion[2] else ""
        c_unit = (criterion[7] if len(criterion)>7 else "") or ""
        c_weight = criterion[4] if criterion[4] is not None else 1.0
        c_dir = (criterion[5] if len(criterion)>5 else 1) or 1
        c_ign = bool(criterion[6]) if len(criterion)>6 else False

        hdr = ctk.CTkFrame(self, fg_color=THEME_ACCENT, height=30)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=f"Edit: {c_name}", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10)
        ctk.CTkButton(hdr, text="✕", width=30, height=30, fg_color="transparent", command=self.destroy).pack(side="right")

        content = ctk.CTkFrame(self, fg_color=THEME_CARD)
        content.pack(fill="both", expand=True, padx=2, pady=2)

        ctk.CTkLabel(content, text="Name:").pack(pady=(10, 0))
        self.name_ent = ctk.CTkEntry(content, width=200); self.name_ent.insert(0, c_name); self.name_ent.pack()
        ctk.CTkLabel(content, text="Unit:").pack(pady=(10, 0))
        self.unit_ent = ctk.CTkEntry(content, width=200); self.unit_ent.insert(0, c_unit); self.unit_ent.pack()
        
        ctk.CTkLabel(content, text="Weight:").pack(pady=(10, 0))
        self.weight_var = tk.DoubleVar(value=c_weight)
        self.sl = ctk.CTkSlider(content, from_=0.1, to=5.0, variable=self.weight_var); self.sl.pack(pady=5)
        self.wl = ctk.CTkLabel(content, text=f"{c_weight:.1f}"); self.wl.pack()
        self.weight_var.trace_add("write", lambda *a: self.wl.configure(text=f"{self.weight_var.get():.1f}"))
        
        self.dir_var = tk.IntVar(value=c_dir)
        ctk.CTkRadioButton(content, text="Higher Better (+)", variable=self.dir_var, value=1).pack(pady=1)
        ctk.CTkRadioButton(content, text="Lower Better (-)", variable=self.dir_var, value=-1).pack(pady=1)
        
        self.ign_var = tk.BooleanVar(value=c_ign)
        ctk.CTkCheckBox(content, text="Ignore Scoring", variable=self.ign_var).pack(pady=10)
        
        bf = ctk.CTkFrame(content, fg_color="transparent"); bf.pack(pady=10)
        ctk.CTkButton(bf, text="Save", width=90, fg_color=THEME_BTN_SUCCESS, command=self.save).pack(side="left", padx=5)
        ctk.CTkButton(bf, text="Delete", width=90, fg_color=THEME_BTN_DANGER, command=self.delete).pack(side="left", padx=5)

    def save(self):
        self.on_save(self.criterion[0], self.name_ent.get(), self.weight_var.get(), self.dir_var.get(), int(self.ign_var.get()), self.unit_ent.get())
        self.destroy()
    def delete(self):
        if messagebox.askyesno("Delete", "Delete?"): self.on_delete(self.criterion[0]); self.destroy()

class VersusUpApp(BaseWindow):
    def __init__(self):
        super().__init__(title="VersusUp - Comparison Engine", width=1280, height=850)
        self.db = DBHandler()
        self.db.insert_dummy_data()
        self.current_project_id = None
        self.sidebar_visible = True
        self.cell_widgets_flat = {} # (pid, cid) -> entry
        
        # UI Setup with Resizing in mind
        self.resizable(True, True)
        
        # Main Layout: Sidebar | Workspace
        if hasattr(self, "main_frame") and self.main_frame:
            self.main_frame.grid_rowconfigure(0, weight=1)
            self.main_frame.grid_columnconfigure(1, weight=1)

        self.sidebar = Sidebar(self.main_frame if hasattr(self, "main_frame") else self, self.switch_project, self.pre_new_project, self.export_current, self.delete_project, self.reset_all_data, self.open_ai_assistant)
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))
        
        self.work_f = ctk.CTkFrame(self.main_frame if hasattr(self, "main_frame") else self, fg_color="transparent")
        self.work_f.pack(side="left", fill="both", expand=True)
        
        self.header = ctk.CTkFrame(self.work_f, fg_color="transparent")
        self.header.pack(fill="x", pady=(10, 10))
        ctk.CTkButton(self.header, text="☰", width=35, height=35, fg_color=THEME_CARD, command=self.tgl_sb).pack(side="left", padx=5)
        self.title_lbl = ctk.CTkLabel(self.header, text="Dashboard", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_lbl.pack(side="left", padx=10)

        self.scroll = ctk.CTkScrollableFrame(self.work_f, fg_color=THEME_CARD, corner_radius=12, border_width=1, border_color=THEME_BORDER)
        self.scroll.pack(fill="both", expand=True, padx=5, pady=(0, 10))

        self.init_data()

    def init_data(self):
        projects = self.db.get_projects()
        if projects: self.switch_project(projects[0][0])
        else: self.sidebar.refresh([], None)

    def tgl_sb(self):
        if self.sidebar_visible: self.sidebar.pack_forget()
        else: self.sidebar.pack(side="left", fill="y", padx=(0, 10), before=self.work_f)
        self.sidebar_visible = not self.sidebar_visible

    def switch_project(self, pid):
        self.current_project_id = pid
        projects = self.db.get_projects()
        p = next((x for x in projects if x[0]==pid), None)
        if p: self.title_lbl.configure(text=f"VersusUp: {p[1]}")
        self.render_grid()
        self.sidebar.refresh(projects, pid)

    def pre_new_project(self):
        if hasattr(self, "active_preset_pop") and self.active_preset_pop:
            try: self.active_preset_pop.destroy()
            except: pass
        self.active_preset_pop = PresetDialog(self, self.create_new_project)

    def create_new_project(self, preset_name):
        name = ask_string_modern("New Project", f"Name for your {preset_name} comparison:")
        if name:
            self.db.create_project(name, preset_name, "")
            projects = self.db.get_projects()
            new_id = projects[-1][0]
            # Add preset criteria
            for cn, ct, w, d, u in PRESETS.get(preset_name, []):
                self.db.add_criterion(new_id, cn, ct)
                # update settings right after
                cids = self.db.get_criteria(new_id)
                last_cid = cids[-1][0]
                self.db.update_criterion_settings(last_cid, w, d, 0, u)
            self.switch_project(new_id)

    def delete_project(self, pid):
        if messagebox.askyesno("Delete Project", "Delete this project and all data?"):
            self.db.delete_project(pid)
            self.init_data()

    def reset_all_data(self):
        if messagebox.askyesno("Reset All Data", "This will permanently delete ALL projects and records. Proceed?"):
            self.db.clear_all_data()
            self.current_project_id = None
            self.init_data()
            messagebox.showinfo("Reset Complete", "All data has been cleared.")

    def render_grid(self):
        for w in self.scroll.winfo_children(): w.destroy()
        if not self.current_project_id: return
        self.cell_widgets_flat = {}
        ps = self.db.get_products(self.current_project_id)
        cs = self.db.get_criteria(self.current_project_id)
        vs = self.db.get_values_for_project(self.current_project_id)
        vm = {(v[0], v[1]): (v[2] if v[2] is not None else "") for v in vs}

        # Header Viz (Reduced to 25% prominence via smaller size)
        vf = ctk.CTkFrame(self.scroll, fg_color="transparent")
        vf.grid(row=0, column=0, padx=10, pady=10)
        self.radar = RadarChart(vf, size=110); self.radar.pack() # Smaller preview
        self.radar.bind("<Button-1>", lambda e: self.expand_radar())

        # Product Headers
        self.score_labels = {}
        for i, p in enumerate(ps):
            p_f = ctk.CTkFrame(self.scroll, fg_color=THEME_CARD, corner_radius=12, width=170, height=200) # Card-style header
            p_f.grid(row=0, column=i+1, padx=10, pady=10)
            p_f.pack_propagate(False)

            sl = ctk.CTkLabel(p_f, text="0.0", font=ctk.CTkFont(size=24, weight="bold"), text_color=THEME_ACCENT)
            sl.pack(pady=(15, 5))
            self.score_labels[p[0]] = sl
            
            nf = ctk.CTkFrame(p_f, fg_color="transparent"); nf.pack(fill="x", padx=10)
            e = ctk.CTkEntry(nf, width=120, border_width=0, fg_color="transparent", justify="center", font=ctk.CTkFont(size=13, weight="bold"))
            e.insert(0, p[2]); e.pack(side="left", expand=True)
            e.bind("<FocusOut>", lambda ev, pid=p[0], ent=e: self.db.update_product_name(pid, ent.get()))
            ctk.CTkButton(nf, text="✕", width=18, height=18, fg_color="transparent", text_color=THEME_TEXT_DIM, command=lambda pid=p[0]: self.on_del_p(pid)).pack(side="left")
            
            # Placeholder for product image
            im_btn = ctk.CTkButton(p_f, text="Add Image", width=130, height=80, fg_color=THEME_BG, border_width=1, border_color=THEME_BORDER, command=lambda pid=p[0]: self.on_img(pid))
            im_btn.pack(pady=10)
            if p[3]:
                try:
                    from PIL import Image
                    img = Image.open(p[3])
                    img.thumbnail((130, 80))
                    import customtkinter as ctk_lib # ensure visibility if needed
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                    im_btn.configure(image=ctk_img, text="")
                except: pass
            

        ctk.CTkButton(self.scroll, text="+ PRODUCT", width=100, height=40, font=ctk.CTkFont(size=11), fg_color="transparent", border_width=2, border_color=THEME_ACCENT, command=self.add_p).grid(row=0, column=len(ps)+1, padx=20)

        # Criteria Rows
        for r, cr in enumerate(cs):
            lf = ctk.CTkFrame(self.scroll, fg_color="transparent")
            lf.grid(row=r+1, column=0, sticky="e", padx=5, pady=2)
            icb = ctk.CTkCheckBox(lf, text="", width=18, height=18, command=lambda c=cr: self.tgl_ign(c))
            if len(cr)>6 and cr[6]: icb.select()
            icb.pack_forget() if not icb.get() else icb.pack(side="left", padx=2)
            ut = cr[7] if len(cr)>7 and cr[7] else ""
            b = ctk.CTkButton(lf, text=cr[2], width=120, height=30, fg_color="transparent", anchor="e", font=ctk.CTkFont(size=11, weight="bold"), command=lambda c=cr: self.open_settings(c))
            b.pack(side="right")
            lf.bind("<Enter>", lambda e, cb=icb: cb.pack(side="left", padx=2))
            lf.bind("<Leave>", lambda e, cb=icb: cb.pack_forget() if not cb.get() else None)
            
            for c, p in enumerate(ps):
                v = vm.get((p[0], cr[0]), "")
                cf = ctk.CTkFrame(self.scroll, width=145, height=30, fg_color="transparent")
                cf.grid(row=r+1, column=c+1, padx=2, pady=1); cf.pack_propagate(False)
                en = ctk.CTkEntry(cf, border_color=THEME_BORDER, fg_color=THEME_BG if v else "transparent", height=30)
                en.insert(0, str(v)); en.pack(fill="both", expand=True)
                if ut: ctk.CTkLabel(cf, text=ut, font=ctk.CTkFont(size=9), text_color=THEME_TEXT_DIM).place(relx=0.95, rely=0.5, anchor="e")
                self.cell_widgets_flat[(p[0], cr[0])] = en
                en.bind("<FocusOut>", lambda ev, pid=p[0], cid=cr[0], ent=en: self.on_ed(pid, cid, ent))

        ctk.CTkButton(self.scroll, text="+ CRITERION", width=140, height=40, font=ctk.CTkFont(size=11), fg_color="transparent", border_width=2, border_color=THEME_ACCENT, command=self.add_c).grid(row=len(cs)+1, column=0, pady=20)
        self.update_scores()

    def update_scores(self):
        ps = self.db.get_products(self.current_project_id)
        cs = self.db.get_criteria(self.current_project_id)
        vs = self.db.get_values_for_project(self.current_project_id)
        vm = {(v[0], v[1]): (v[2] if v[2] is not None else "") for v in vs}
        
        scores = {p[0]: 0.0 for p in ps}
        crit_vals_per_row = {} # cid -> list of (pid, float_val)
        for cr in cs:
            row_vs = []
            for p in ps:
                raw = vm.get((p[0], cr[0]), "")
                try: 
                    fv = float(raw)
                    row_vs.append((p[0], fv))
                except: pass
            if row_vs: crit_vals_per_row[cr[0]] = row_vs

        # Scoring & Highlighting
        for cr in cs:
            is_ignored = len(cr) > 6 and cr[6]
            if cr[0] in crit_vals_per_row and not is_ignored:
                rvs = [x[1] for x in crit_vals_per_row[cr[0]]]
                mi, ma = min(rvs), max(rvs)
                direction = cr[5] if len(cr)>5 else 1
                
                # Apply Highlighting (Green for best, Red for worst)
                best_val = ma if direction == 1 else mi
                worst_val = mi if direction == 1 else ma
                
                for pid, fv in crit_vals_per_row[cr[0]]:
                    # Update cell entry color
                    if (pid, cr[0]) in self.cell_widgets_flat:
                        en = self.cell_widgets_flat[(pid, cr[0])]
                        if fv == best_val and ma != mi:
                            en.configure(border_color="#81C784", border_width=2, fg_color="#1B3A2C") # Faint Green Tint
                        elif fv == worst_val and ma != mi:
                            en.configure(border_color="#E57373", border_width=2, fg_color="#3A1B1B") # Faint Red Tint
                        else:
                            en.configure(border_color=THEME_BORDER, border_width=1, fg_color=THEME_CARD)
                    
                    # Accumulate score
                    norm = (fv - mi) / (ma - mi) if ma != mi else 1.0
                    if direction == -1: norm = 1.0 - norm
                    scores[pid] += norm * cr[4]
            else:
                # Reset highlight if ignored or no values
                for p in ps:
                    if (p[0], cr[0]) in self.cell_widgets_flat:
                        self.cell_widgets_flat[(p[0], cr[0])].configure(border_color=THEME_BORDER, border_width=1, fg_color=THEME_CARD)

        for p in ps:
            tot = scores[p[0]]
            if p[0] in self.score_labels: self.score_labels[p[0]].configure(text=f"{tot:.1f}", text_color=THEME_ACCENT if tot > 0 else THEME_TEXT_DIM)
        if hasattr(self, "radar"): self.radar.draw(ps, cs, vm, scores)

    def on_ed(self, pid, cid, en):
        self.db.update_value(pid, cid, en.get())
        self.update_scores()
    def tgl_ign(self, cr):
        i = 1 if not (len(cr)>6 and cr[6]) else 0
        self.db.update_criterion_settings(cr[0], cr[4], cr[5] if len(cr)>5 else 1, i, cr[7] if len(cr)>7 else "")
        self.render_grid()
    def on_save_cr(self, cid, name, w, d, i, u):
        self.db.update_criterion_name(cid, name)
        self.db.update_criterion_settings(cid, w, d, i, u); self.render_grid()
    def on_del_p(self, pid):
        if messagebox.askyesno("Delete", "Delete product?"): self.db.delete_product(pid); self.render_grid()
    def on_del_cr(self, cid): self.db.delete_criterion(cid); self.render_grid()
    def on_img(self, pid):
        path = filedialog.askopenfilename()
        if path: self.db.update_product_image(pid, path); self.render_grid()
    def add_p(self): self.db.add_product(self.current_project_id, f"Product {len(self.db.get_products(self.current_project_id))+1}"); self.render_grid()
    def add_c(self): self.db.add_criterion(self.current_project_id, f"Criterion {len(self.db.get_criteria(self.current_project_id))+1}", "number"); self.render_grid()
    def open_settings(self, cr):
        if hasattr(self, "active_popup") and self.active_popup:
            try: self.active_popup.destroy()
            except: pass
        self.active_popup = CriterionPopup(self, cr, self.on_save_cr, self.on_del_cr, self.winfo_pointerx(), self.winfo_pointery())

    def expand_radar(self):
        if hasattr(self, "active_radar_pop") and self.active_radar_pop:
            try: self.active_radar_pop.destroy()
            except: pass
        self.active_radar_pop = ctk.CTkToplevel(self)
        pop = self.active_radar_pop
        pop.title("Analysis Expanded"); pop.geometry("800x800")
        f = ctk.CTkFrame(pop, fg_color=THEME_BG, corner_radius=12); f.pack(fill="both", expand=True, padx=20, pady=20)
        c = RadarChart(f, size=700, show_labels=True); c.pack(expand=True)
        ps = self.db.get_products(self.current_project_id); cs = self.db.get_criteria(self.current_project_id)
        vs = self.db.get_values_for_project(self.current_project_id); vm = {(v[0], v[1]): (v[2] if v[2] is not None else "") for v in vs}
        c.draw(ps, cs, vm, {})
    def export_current(self):
        if not self.current_project_id: return
        ps = self.db.get_projects(); p = next(x for x in ps if x[0] == self.current_project_id)
        md = ExportUtil.to_markdown(p, self.db.get_products(p[0]), self.db.get_criteria(p[0]), self.db.get_values_for_project(p[0]))
        path = filedialog.asksaveasfilename(defaultextension=".md", initialfile=f"VersusUp_{p[1]}.md")
        if path: ExportUtil.save_to_file(md, path); messagebox.showinfo("Success", "Exported.")

    def open_ai_assistant(self):
        if not self.current_project_id:
            messagebox.showwarning("Warning", "Please select a project first.")
            return
        
        if hasattr(self, "active_ai_pop") and self.active_ai_pop:
            try: self.active_ai_pop.destroy()
            except: pass
            
        self.active_ai_pop = AIAnalysisDialog(self, self.current_project_id, self.on_ai_sync)

    def on_ai_sync(self, extracted_data):
        # Merge AI extracted data into DB
        project_name = self.title_lbl.cget("text").replace("VersusUp: ", "")
        for item in extracted_data.get("criteria", []):
            name = item.get("name")
            val = item.get("value")
            unit = item.get("unit", "")
            
            if not name or not val: continue
            
            # Find or create criterion
            existing_cs = self.db.get_criteria(self.current_project_id)
            c_found = next((c for c in existing_cs if c[2].lower() == name.lower()), None)
            
            if not c_found:
                cid = self.db.add_criterion(self.current_project_id, name, "number")
                if unit:
                    self.db.update_criterion_settings(cid, 1.0, 1, 0, unit)
            else:
                cid = c_found[0]

            # Since vision model might not know which product it belongs to easily without logic,
            # for now we'll add it as a new criteria suggestion or just note.
            # OPTIMIZATION: Try to map to products if product names were detected.
        
        self.render_grid()
        messagebox.showinfo("AI Sync", "AI suggested data has been processed.")

class AIAnalysisDialog(ctk.CTkToplevel):
    def __init__(self, master, project_id, on_sync):
        super().__init__(master)
        self.title("AI Multi-Image analysis")
        self.geometry("600x600")
        self.project_id = project_id
        self.on_sync = on_sync
        self.ai = AIHandler()
        self.image_paths = []

        self.attributes("-topmost", True)
        
        # UI
        ctk.CTkLabel(self, text="AI Image Analysis (Ollama)", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        
        self.btn_f = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_f.pack(fill="x", padx=40)
        
        self.add_btn = ctk.CTkButton(self.btn_f, text="+ Select Images", command=self.select_images)
        self.add_btn.pack(side="left", expand=True, padx=5)
        
        self.run_btn = ctk.CTkButton(self.btn_f, text="Run Analysis", state="disabled", command=self.run_ai)
        self.run_btn.pack(side="left", expand=True, padx=5)

        self.status_lbl = ctk.CTkLabel(self, text="No images selected", text_color=THEME_TEXT_DIM)
        self.status_lbl.pack(pady=10)

        self.list_frame = ctk.CTkScrollableFrame(self, height=200, fg_color=THEME_CARD)
        self.list_frame.pack(fill="both", expand=True, padx=40, pady=10)

        self.result_text = ctk.CTkTextbox(self, height=150, fg_color="#000")
        self.result_text.pack(fill="x", padx=40, pady=10)

        self.sync_btn = ctk.CTkButton(self, text="Sync to Grid", fg_color=THEME_BTN_SUCCESS, state="disabled", command=self.confirm_sync)
        self.sync_btn.pack(pady=20)

    def select_images(self):
        paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp")])
        if paths:
            self.image_paths = list(paths)
            self.status_lbl.configure(text=f"{len(self.image_paths)} images selected", text_color=THEME_ACCENT)
            self.run_btn.configure(state="normal")
            for wp in self.list_frame.winfo_children(): wp.destroy()
            for p in self.image_paths:
                ctk.CTkLabel(self.list_frame, text=os.path.basename(p), font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)

    def run_ai(self):
        self.run_btn.configure(state="disabled", text="Processing...")
        self.update()
        
        result = self.ai.analyze_images(self.image_paths)
        
        if "error" in result:
            self.result_text.insert("0.0", f"Error: {result['error']}")
            self.run_btn.configure(state="normal", text="Run Analysis")
            return
            
        self.extracted_data = result
        self.result_text.insert("0.0", json.dumps(result, indent=2, ensure_ascii=False))
        self.sync_btn.configure(state="normal")
        self.run_btn.configure(state="normal", text="Run Analysis")

    def confirm_sync(self):
        self.on_sync(self.extracted_data)
        self.destroy()

if __name__ == "__main__":
    app = VersusUpApp()
    app.mainloop()
