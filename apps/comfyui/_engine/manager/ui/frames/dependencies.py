import customtkinter as ctk
import tkinter.messagebox
import threading
import time
import os
import shutil
import webbrowser
from pathlib import Path
from typing import Optional, Dict

from utils import external_tools
import urllib.request
import urllib.error
import json
import ssl

from manager.ui.theme import Theme

class ApiRow(ctk.CTkFrame):
    """Row for API Key / URL with Test button."""
    def __init__(self, parent, api_key, label_text, initial_value, on_test):
        super().__init__(parent, fg_color="transparent")
        self.api_key = api_key
        self.on_test = on_test
        
        self.grid_columnconfigure(1, weight=1)
        
        # Label
        ctk.CTkLabel(self, text=label_text, width=80, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(5, 10))
        
        # Entry
        self.entry = ctk.CTkEntry(self, show="•" if "KEY" in api_key else None)
        self.entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.entry.insert(0, initial_value)
        
        # Test Button
        self.btn_test = ctk.CTkButton(self, text="Test", width=50, fg_color="#34495E", command=self._start_test)
        self.btn_test.grid(row=0, column=2, padx=2)
        
        # Status Label
        self.lbl_status = ctk.CTkLabel(self, text="---", width=60, font=ctk.CTkFont(size=11))
        self.lbl_status.grid(row=0, column=3, padx=(10, 5))

    def _start_test(self):
        val = self.entry.get().strip()
        if not val:
            self.set_status(False, "Empty")
            return
        self.lbl_status.configure(text="Checking...", text_color="gray")
        self.on_test(self.api_key, val, self)

    def set_status(self, success: bool, msg: str = None):
        if success:
            text = msg if msg else "OK"
            color = Theme.TEXT_DIM  # Gray instead of green
        else:
            text = msg if msg else "Error"
            color = Theme.TEXT_DANGER
        self.lbl_status.configure(text=text, text_color=color)

class ToolRow(ctk.CTkFrame):
    """A consistent row for tool path management and status."""
    def __init__(self, parent, tool_key, label_text, initial_value, on_browse, on_detect):
        super().__init__(parent, fg_color="transparent")
        self.tool_key = tool_key
        
        self.grid_columnconfigure(1, weight=1)
        
        # Label
        ctk.CTkLabel(self, text=label_text, width=80, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(5, 10))
        
        # Entry
        self.entry = ctk.CTkEntry(self)
        self.entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.entry.insert(0, initial_value)
        
        # Browse Button
        ctk.CTkButton(self, text="📂", width=30, command=lambda: on_browse(self.entry, tool_key)).grid(row=0, column=2, padx=2)
        
        # Auto-Detect Button
        self.btn_detect = ctk.CTkButton(self, text="🔍", width=30, fg_color="gray40", hover_color="gray30", 
                                        command=lambda: on_detect(self.entry, tool_key))
        self.btn_detect.grid(row=0, column=3, padx=2)
        
        # Status Label
        self.lbl_status = ctk.CTkLabel(self, text="---", width=60, font=ctk.CTkFont(size=11))
        self.lbl_status.grid(row=0, column=4, padx=(10, 5))

    def set_status(self, is_found: bool):
        if is_found:
            self.lbl_status.configure(text="Ready", text_color=Theme.TEXT_DIM)  # Gray instead of green
        else:
            self.lbl_status.configure(text="Missing", text_color=Theme.TEXT_DANGER)

class DependenciesFrame(ctk.CTkFrame):
    def __init__(self, parent, settings_manager, package_manager, config_manager=None, translator=None, root_dir=None):
        super().__init__(parent, fg_color="transparent")
        self.settings = settings_manager
        self.package_manager = package_manager
        self.config_manager = config_manager
        self.tr = translator if translator else lambda k: k
        self.root_dir = Path(root_dir) if root_dir else None
        
        self.tool_rows: Dict[str, ToolRow] = {}
        self.api_entries = {}
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Scrollable area
        
        # --- Navigation/Header (Row 0) ---
        self._create_section_headers()
        
        # --- Scrollable Content Area (Row 1) ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        self._create_connectivity_content()
        self._create_deps_content()
        
        # Flags
        self._deps_loaded = False

    def _create_section_headers(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 5))
        
        ctk.CTkLabel(header_frame, text=self.tr("manager.dashboard.connectivity.title"), font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        
        # Tools Control
        ctk.CTkButton(header_frame, text=self.tr("common.refresh"), width=80, command=self.refresh_all).pack(side="right", padx=5)

    def _create_connectivity_content(self):
        self.conn_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.conn_frame.pack(fill="x", pady=(0, 20))
        self.conn_frame.grid_columnconfigure(0, weight=1)
        
        tools_map = [
            ("PYTHON_PATH", self.tr("manager.dashboard.connectivity.python")),
            ("FFMPEG_PATH", self.tr("manager.dashboard.connectivity.ffmpeg")),
            ("BLENDER_PATH", self.tr("manager.dashboard.connectivity.blender")),
            ("COMFYUI_PATH", "ComfyUI"), # No key for ComfyUI yet?
            ("MAYO_PATH", self.tr("manager.dashboard.connectivity.mayo"))
        ]
        
        for i, (key, name) in enumerate(tools_map):
            initial_val = self.settings.get(key, "")
            row = ToolRow(self.conn_frame, key, name, initial_val, self._on_browse, self._on_detect)
            row.pack(fill="x", pady=2)
            self.tool_rows[key] = row
            
        # APIs Section inside connectivity
        sep = ctk.CTkFrame(self.conn_frame, height=1, fg_color="gray30")
        sep.pack(fill="x", pady=15)
        
        api_container = ctk.CTkFrame(self.conn_frame, fg_color="transparent")
        api_container.pack(fill="x")
        api_container.grid_columnconfigure(0, weight=1)
        
        apis = [
            ("GEMINI_API_KEY", self.tr("manager.dashboard.connectivity.gemini_api")),
            ("OLLAMA_URL", self.tr("manager.dashboard.connectivity.ollama_url"))
        ]
        
        for i, (key, name) in enumerate(apis):
            default = "http://localhost:11434" if "OLLAMA" in key else ""
            val = self.settings.get(key, default)
            
            row = ApiRow(api_container, key, name, val, self._test_api_connection)
            row.pack(fill="x", pady=2)
            self.api_entries[key] = row.entry # Keep ref for saving

    def _test_api_connection(self, key, value, row_instance):
        """Threaded connection check."""
        def run_check():
            success = False
            msg = "Fail"
            try:
                if "GEMINI" in key:
                    success, msg = self._check_gemini(value)
                elif "OLLAMA" in key:
                    success, msg = self._check_ollama(value)
                else:
                    msg = "Unknown"
            except Exception as e:
                msg = "Ex"
                print(e)
            
            # Update UI on main thread
            self.after(0, lambda: row_instance.set_status(success, msg))
            
        threading.Thread(target=run_check, daemon=True).start()

    def _check_gemini(self, api_key):
        if not api_key: return False, "Empty"
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read())
                    if "models" in data:
                        return True, "Active"
            return False, "Invalid"
        except urllib.error.HTTPError as e:
             return False, f"HTTP {e.code}"
        except Exception:
            return False, "Error"

    def _check_ollama(self, url):
        if not url: return False, "Empty"
        # Normalize URL
        if not url.startswith("http"): url = "http://" + url
        try:
            # Try /api/tags (list models)
            target = f"{url.rstrip('/')}/api/tags"
            with urllib.request.urlopen(target, timeout=2) as response:
                if response.status == 200:
                    return True, "Online"
            return False, "Unreachable"
        except Exception:
            return False, "Down"

    def _create_deps_content(self):
        # Header for Deps
        deps_header = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        deps_header.pack(fill="x", pady=(10, 5))
        ctk.CTkLabel(deps_header, text="📦 " + self.tr("manager.frames.dependencies.title"), font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        btn_box = ctk.CTkFrame(deps_header, fg_color="transparent")
        btn_box.pack(side="right")
        
        ctk.CTkButton(btn_box, text=self.tr("manager.frames.dependencies.check_sys"), width=120, font=ctk.CTkFont(size=11), fg_color="#8E44AD", command=self.update_system_libs).pack(side="left", padx=2)
        ctk.CTkButton(btn_box, text=self.tr("manager.frames.dependencies.install_ai"), width=120, font=ctk.CTkFont(size=11), fg_color="#D35400", hover_color="#E74C3C", command=self.install_ai_heavy_batch).pack(side="left", padx=2)
        
        self.deps_list_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.deps_list_frame.pack(fill="x", pady=5)
        
        self._show_loading_placeholder()

    def _on_browse(self, entry, key):
        from tkinter import filedialog
        path = filedialog.askopenfilename()
        
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)
            self.refresh_tool_status(key)

    def _on_detect(self, entry, key):
        """Auto-detect tool path using external_tools logic."""
        try:
            detected = None
            if key == "PYTHON_PATH":
                # Check tools/python/python.exe
                p = self.root_dir / "tools" / "python" / "python.exe" if self.root_dir else Path("tools/python/python.exe")
                if p.exists(): detected = str(p)
            elif key == "FFMPEG_PATH":
                detected = external_tools.get_ffmpeg()
            elif key == "BLENDER_PATH":
                detected = external_tools.get_blender()
            elif key == "COMFYUI_PATH":
                detected = external_tools.get_comfyui()
            elif key == "MAYO_PATH":
                try: detected = external_tools.get_mayo_viewer()
                except: pass
            
            if detected and detected != "ffmpeg": # Ignore generic 'ffmpeg' fallback if we want absolute path
                entry.delete(0, "end")
                entry.insert(0, detected)
                self.refresh_tool_status(key)
            else:
                tkinter.messagebox.showinfo("Not Found", f"Could not auto-detect {key}. Please browse manually.")
        except Exception as e:
            tkinter.messagebox.showerror("Error", f"Detection failed: {e}")

    def refresh_all(self):
        """Refresh both tool paths and python dependencies."""
        self.refresh_tool_statuses()
        self.refresh_deps()

    def refresh_tool_statuses(self):
        for key in self.tool_rows:
            self.refresh_tool_status(key)

    def refresh_tool_status(self, key):
        row = self.tool_rows.get(key)
        if not row: return
        
        path = row.entry.get().strip()
        if not path:
            row.set_status(False)
            return
            
        is_valid = False
        try:
            is_valid = os.path.exists(path)
        except: pass
        
        row.set_status(is_valid)

    def save(self):
        """Save all settings to manager's settings."""
        for key, row in self.tool_rows.items():
            self.settings[key] = row.entry.get().strip()
        for key, entry in self.api_entries.items():
            self.settings[key] = entry.get().strip()

    def on_visible(self):
        if not self._deps_loaded:
            self._deps_loaded = True
            self.refresh_all()

    def _show_loading_placeholder(self):
        for w in self.deps_list_frame.winfo_children(): w.destroy()
        ctk.CTkLabel(self.deps_list_frame, text="Scanning dependencies...", text_color="gray").pack(pady=10)

    def refresh_deps(self):
        threading.Thread(target=self._scan_deps, daemon=True).start()

    def _scan_deps(self):
        self.installed_packages = self.package_manager.get_installed_packages()
        
        self.pkg_ai_heavy = [
            ("torch", "PyTorch (AI Core)"),
            ("rembg", "Rembg (BG Removal)"),
            ("faster-whisper", "Faster Whisper"),
            ("transformers", "Transformers"),
        ]
        
        common_libs = [
            ("customtkinter", "CustomTkinter"),
            ("pystray", "Pystray"),
            ("Pillow", "Pillow"),
            ("google-generativeai", "Gemini API"),
            ("numpy", "NumPy"),
        ] + self.pkg_ai_heavy
        
        self.after(0, lambda: [w.destroy() for w in self.deps_list_frame.winfo_children()])
        for pkg, label in common_libs:
            ver = self.installed_packages.get(pkg.lower(), None)
            self.after(0, lambda p=pkg, l=label, v=ver: self._add_dep_row(p, l, v))

    def _add_dep_row(self, pkg, label, version):
        row = ctk.CTkFrame(self.deps_list_frame, fg_color="transparent")
        row.pack(fill="x", pady=1)
        
        ctk.CTkLabel(row, text=label, width=150, anchor="w").pack(side="left", padx=10)
        
        status_text = f"v{version}" if version else "Missing"
        status_color = Theme.TEXT_DIM if version else Theme.TEXT_DANGER  # Gray instead of green
        ctk.CTkLabel(row, text=status_text, text_color=status_color, width=100).pack(side="left")
        
        if not version:
            ctk.CTkButton(row, text="Install", width=60, height=22, font=ctk.CTkFont(size=10),
                          command=lambda: self.install_pkg(pkg)).pack(side="right", padx=10)

    def install_ai_heavy_batch(self):
        if not tkinter.messagebox.askyesno("Install AI Engine", "Install heavy AI dependencies? (approx 4GB)"): return
        pkgs = [p[0] for p in self.pkg_ai_heavy] + ["torchvision", "torchaudio"]
        meta = {
            "torch": {'pip_name': "torch", 'install_args': ["--index-url", "https://download.pytorch.org/whl/cu121"]},
            "torchvision": {'pip_name': "torchvision", 'install_args': ["--index-url", "https://download.pytorch.org/whl/cu121"]},
            "torchaudio": {'pip_name': "torchaudio", 'install_args': ["--index-url", "https://download.pytorch.org/whl/cu121"]},
        }
        self.package_manager.install_packages(pkgs, meta, lambda c, f: None, lambda s: self.after(0, lambda: self.refresh_all()))

    def install_pkg(self, pkg):
        if not tkinter.messagebox.askyesno("Confirm", f"Install {pkg}?"): return
        meta = {pkg: {'pip_name': pkg, 'install_args': []}}
        self.package_manager.install_packages([pkg], meta, lambda c, f: None, lambda s: self.after(0, lambda: self.refresh_all()))

    def update_system_libs(self):
        if not tkinter.messagebox.askyesno("System Update", "Install all requirements?"): return
        self.package_manager.update_system_libs(lambda s, m: self.after(0, lambda: tkinter.messagebox.showinfo("Result", m)))
