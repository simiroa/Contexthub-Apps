import customtkinter as ctk
import os
from pathlib import Path
import threading
import time
from manager.ui.theme import Theme
from utils.comfy_server import is_comfy_running, start_comfy, stop_comfy


class LogsFrame(ctk.CTkFrame):
    def __init__(self, parent, root_dir):
        super().__init__(parent, fg_color="transparent")
        self.root_dir = root_dir
        self.log_dir = root_dir / "logs"
        self.running = False
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Controls
        ctrl = ctk.CTkFrame(self, height=40, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(ctrl, text="Log Viewer", font=ctk.CTkFont(size=16, weight="bold"), text_color=Theme.TEXT_MAIN[1]).pack(side="left", padx=10)
        
        self.btn_refresh = ctk.CTkButton(ctrl, text="Refresh", width=80, fg_color=Theme.GRAY_BTN, hover_color=Theme.GRAY_BTN_HOVER, command=self.load_logs)
        self.btn_refresh.pack(side="right", padx=10)
        
        self.chk_auto = ctk.CTkCheckBox(ctrl, text="Auto Refresh (3s)", command=self.toggle_auto)
        self.chk_auto.pack(side="right", padx=10)
        
        # Tabs
        self.tabview = ctk.CTkTabview(self,
                                      fg_color=Theme.BG_CARD,
                                      segmented_button_selected_color=Theme.PRIMARY,
                                      segmented_button_selected_hover_color=Theme.PRIMARY_HOVER,
                                      segmented_button_unselected_color=Theme.STANDARD,
                                      segmented_button_unselected_hover_color=Theme.STANDARD_HOVER,
                                      border_width=0,
                                      text_color="#E0E0E0")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Create tabs
        self.log_files = {
            "App": "app_*.log",
            "Tray": "debug_*.log",
            "ComfyUI": "comfyui_server.log",
            "Recent": "recent_folders.log"
        }
        
        self.text_widgets = {}
        
        for name, _ in self.log_files.items():
            self.tabview.add(name)  # Create tab first
            tab = self.tabview.tab(name)
            
            # Sub-toolbar for current tab
            tab_toolbar = ctk.CTkFrame(tab, fg_color="transparent", height=30)
            tab_toolbar.pack(fill="x", side="top", pady=(0, 5))
            
            # Export button (all tabs)
            ctk.CTkButton(tab_toolbar, text="Export Log", width=80, height=24, 
                         fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER,
                         command=lambda n=name: self.export_log(n)).pack(side="right", padx=5)
            
            # ComfyUI Management (only for ComfyUI tab)
            if name == "ComfyUI":
                self.btn_comfy_start = ctk.CTkButton(tab_toolbar, text="Start", width=60, height=24,
                                                   fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER,
                                                   command=self._start_comfy_ui)
                self.btn_comfy_start.pack(side="left", padx=2)
                
                self.btn_comfy_restart = ctk.CTkButton(tab_toolbar, text="Restart", width=60, height=24,
                                                     fg_color=Theme.STANDARD, hover_color=Theme.STANDARD_HOVER,
                                                     command=self._restart_comfy_ui)
                self.btn_comfy_restart.pack(side="left", padx=2)
                
                self.btn_comfy_stop = ctk.CTkButton(tab_toolbar, text="Stop", width=60, height=24,
                                                  fg_color=Theme.DANGER, hover_color=Theme.DANGER_HOVER,
                                                  command=self._stop_comfy_ui)
                self.btn_comfy_stop.pack(side="left", padx=2)
                
                self.lbl_comfy_status = ctk.CTkLabel(tab_toolbar, text="---", font=ctk.CTkFont(size=12, weight="bold"))
                self.lbl_comfy_status.pack(side="left", padx=10)

            # Log Text Area
            txt = ctk.CTkTextbox(tab, font=("Consolas", 12), fg_color="#050505", text_color="#d0d0d0")
            txt.pack(fill="both", expand=True)
            txt.configure(state="disabled")
            self.text_widgets[name] = txt
            
        # Initial Load
        self.load_logs()

    def toggle_auto(self):
        if self.chk_auto.get():
            self.running = True
            self._auto_loop()
        else:
            self.running = False

    def _auto_loop(self):
        if self.running:
            self.load_logs()
            self.after(3000, self._auto_loop)

    def load_logs(self):
        for name, pattern in self.log_files.items():
            content = self._read_latest_log(pattern)
            self._update_text(name, content)
        self._update_comfy_status()

    def _update_comfy_status(self):
        if not hasattr(self, "lbl_comfy_status"): return
        running = is_comfy_running()
        if running:
            self.lbl_comfy_status.configure(text="● Online", text_color=Theme.TEXT_SUCCESS)
            self.btn_comfy_start.configure(state="disabled")
        else:
            self.lbl_comfy_status.configure(text="● Offline", text_color=Theme.TEXT_DANGER)
            self.btn_comfy_start.configure(state="normal")

    def _start_comfy_ui(self):
        ok, msg = start_comfy()
        self.load_logs()
        if not ok: tkinter.messagebox.showerror("Error", msg)

    def _stop_comfy_ui(self):
        if not tkinter.messagebox.askyesno("Stop", "Stop ComfyUI Server?"): return
        ok, msg = stop_comfy()
        self.load_logs()
        if not ok: tkinter.messagebox.showerror("Error", msg)

    def _restart_comfy_ui(self):
        if not tkinter.messagebox.askyesno("Restart", "Restart ComfyUI Server?"): return
        stop_comfy()
        time.sleep(1)
        ok, msg = start_comfy()
        self.load_logs()
        if not ok: tkinter.messagebox.showerror("Error", msg)

    def export_log(self, name):
        from tkinter import filedialog
        pattern = self.log_files.get(name)
        if not pattern: return
        
        content = self._read_latest_log(pattern)
        if "No log files found" in content or "Log file not found" in content:
            tkinter.messagebox.showwarning("Empty", "No log content to export.")
            return

        fpath = filedialog.asksaveasfilename(defaultextension=".log", 
                                            initialfile=f"ContextUp_{name}.log",
                                            title=f"Export {name} Log")
        if fpath:
            try:
                Path(fpath).write_text(content, encoding="utf-8")
                tkinter.messagebox.showinfo("Success", f"Log exported to: {fpath}")
            except Exception as e:
                tkinter.messagebox.showerror("Error", f"Failed to export: {e}")

    def _read_latest_log(self, pattern):
        try:
            # Handle direct file (no wildcard) vs pattern
            if "*" not in pattern:
                 f = self.log_dir / pattern
                 if f.exists():
                     latest = f
                 else:
                     return f"Log file not found: {pattern}"
            else:
                # Find latest matching file
                files = list(self.log_dir.glob(pattern))
                if not files:
                    return f"No log files found for pattern: {pattern}"
                
                # Sort by modification time
                latest = max(files, key=lambda f: f.stat().st_mtime)
            
            # Read last 200 lines
            text = latest.read_text(encoding="utf-8", errors="ignore")
            lines = text.splitlines()
            if len(lines) > 200:
                lines = lines[-200:]
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error reading log: {e}"

    def _update_text(self, name, content):
        widget = self.text_widgets[name]
        current_y = widget.yview()[1] # Check if scrolled to bottom
        
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")
        
        # If was largely at bottom, autoscroll
        if current_y > 0.9:
            widget.yview_moveto(1.0)
