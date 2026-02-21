import os
import sys
from pathlib import Path
import runpy

LEGACY_ID = 'mesh_convert'
LEGACY_SCOPE = 'file'
USE_MENU = False
SCRIPT_REL = "features/mesh/blender.py"

ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = Path(__file__).resolve().parent
LEGACY_ROOT = APP_ROOT.parent / "_engine"
os.chdir(LEGACY_ROOT)
sys.path.insert(0, str(LEGACY_ROOT))
if not os.environ.get("CTX_APP_ROOT"):
    os.environ["CTX_APP_ROOT"] = str(APP_ROOT)


def _capture_mode():
    return os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1"

def _pick_targets():
    if LEGACY_SCOPE in {"background", "tray_only"}:
        return []

    if _capture_mode():
        try:
            from utils.headless_inputs import get_headless_targets
            return get_headless_targets(LEGACY_ID, LEGACY_SCOPE, LEGACY_ROOT)
        except Exception:
            return []

    args = [a for a in sys.argv[1:] if a]
    if args:
        return args

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()

        if LEGACY_SCOPE in {"items"}:
            paths = filedialog.askopenfilenames(title=LEGACY_ID)
            return list(paths)
        if LEGACY_SCOPE in {"directory"}:
            path = filedialog.askdirectory(title=LEGACY_ID)
            return [path] if path else []
        path = filedialog.askopenfilename(title=LEGACY_ID)
        return [path] if path else []
    except Exception:
        return []


def _run_script(script_rel, targets):
    script_path = LEGACY_ROOT / script_rel
    if not script_path.exists():
        raise FileNotFoundError("Missing script: " + str(script_path))
    argv = [str(script_path)] + targets
    old_argv = sys.argv
    try:
        sys.argv = argv
        runpy.run_path(str(script_path), run_name="__main__")
    finally:
        sys.argv = old_argv


def _run_menu(targets):
    from core import menu as legacy_menu
    handler = legacy_menu.build_handler_map().get(LEGACY_ID)
    if handler is None:
        raise RuntimeError("Missing legacy handler: " + LEGACY_ID)

    target = targets[0] if targets else str(LEGACY_ROOT)
    selection = targets if len(targets) > 1 else None
    try:
        if selection:
            handler(target, selection)
        else:
            handler(target)
    except TypeError:
        handler(target)


def main():
    targets = _pick_targets()
    if LEGACY_SCOPE not in {"background", "tray_only"} and not targets and not _capture_mode():
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("ContextHub", "No target selected.")
        except Exception:
            pass
        return



def _run_gui_app(targets):
    import customtkinter as ctk
    import threading
    import tkinter.messagebox as messagebox
    from pathlib import Path
    import runpy
    import sys
    
    # Import standard UI components
    try:
        from utils.gui_lib import BaseWindow, FileListFrame, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, THEME_BORDER
    except ImportError:
        from contexthub.utils.gui_lib import BaseWindow, FileListFrame, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, THEME_BORDER
    
        from contexthub.utils.gui_lib import BaseWindow, FileListFrame
    
    from utils.i18n import t, load_extra_strings

    # Load local translations
    try:
        params_file = Path(__file__).parent.parent / "_engine" / "locales.json"
        if params_file.exists():
            load_extra_strings(params_file)
    except Exception as e:
        print(f"Failed to load locales: {e}")

    class MeshConverterGUI(BaseWindow):
        def __init__(self, targets):
            super().__init__(title=t("mesh_convert.title"), width=640, height=580, icon_name="mesh_icon")
            self.targets = targets
            self.create_widgets()
            
        def create_widgets(self):
            # 1. Header
            self.add_header(t("mesh_convert.header"), font_size=20)
            
            # 2. File List
            ctk.CTkLabel(self.main_frame, text=f"{t('mesh_convert.source_files')} ({len(self.targets)})", font=("", 14, "bold")).pack(anchor="w", padx=20, pady=(10, 5))
            
            path_targets = [Path(t) for t in self.targets]
            self.file_list = FileListFrame(self.main_frame, path_targets, height=100)
            self.file_list.pack(fill="x", padx=20, pady=(0, 15))

            # 3. Options
            opt_frame = ctk.CTkFrame(self.main_frame)
            opt_frame.pack(fill="x", padx=20, pady=5)
            
            # Row 1: Format
            row1 = ctk.CTkFrame(opt_frame, fg_color="transparent")
            row1.pack(fill="x", padx=15, pady=15)
            
            ctk.CTkLabel(row1, text=t("mesh_convert.target_format"), font=("", 13, "bold")).pack(side="left")
            self.var_format = ctk.StringVar(value="GLB")
            formats = ["GLB", "GLTF", "OBJ", "FBX", "STL", "ABC", "PLY", "DAE"]
            ctk.CTkComboBox(row1, variable=self.var_format, values=formats, width=150,
                            fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER).pack(side="right")
            
            # Row 2: Draco
            row2 = ctk.CTkFrame(opt_frame, fg_color="transparent")
            row2.pack(fill="x", padx=15, pady=(0, 15))
            
            self.var_draco = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(row2, text=t("mesh_convert.use_draco"), variable=self.var_draco).pack(side="left")
            
            # 4. Progress & Status
            self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            self.progress_frame.pack(fill="x", padx=20, pady=(20, 0))
            
            self.lbl_status = ctk.CTkLabel(self.progress_frame, text=t("common.ready"), text_color="gray")
            self.lbl_status.pack(anchor="w")
            
            self.progress = ctk.CTkProgressBar(self.progress_frame)
            self.progress.pack(fill="x", pady=5)
            self.progress.set(0)

            # 5. Buttons
            btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            btn_frame.pack(fill="x", padx=20, pady=20)
            
            self.btn_cancel = ctk.CTkButton(btn_frame, text=t("common.cancel"), command=self.destroy, fg_color="transparent", border_width=1, border_color=THEME_BORDER, text_color=("gray10", "gray90"))
            self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))
            
            self.btn_run = ctk.CTkButton(btn_frame, text=t("mesh_convert.start_btn"), command=self.run_conversion, fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER)
            self.btn_run.pack(side="left", fill="x", expand=True)

        def run_conversion(self):
            self.btn_run.configure(state="disabled", text=t("common.processing"))
            self.btn_cancel.configure(state="disabled")
            
            target_fmt = self.var_format.get().lower()
            script_path = LEGACY_ROOT / SCRIPT_REL
            
            def _thread():
                try:
                    # Construct args: ["convert", file1, file2, ..., "--format", target_fmt]
                    emulated_argv = [str(script_path), "convert"] + self.targets + ["--format", target_fmt]
                    
                    if self.var_draco.get():
                         emulated_argv.append("--draco")

                    # Monkey patch sys.argv
                    original_argv = sys.argv
                    sys.argv = emulated_argv
                    
                    self.lbl_status.configure(text=f"Running Blender Script...")
                    self.progress.set(0.5) # Indeterminate since single script run processes all
                    
                    runpy.run_path(str(script_path), run_name="__main__")
                    
                    sys.argv = original_argv
                        
                    self.progress.set(1.0)
                    self.lbl_status.configure(text=t("common.complete"))
                    messagebox.showinfo(t("common.success"), t("common.complete"))
                    self.after(500, self.destroy)
                    
                except Exception as e:
                    import sys
                    sys.argv = original_argv # Restore just in case
                    self.lbl_status.configure(text=t("common.error"), text_color="red")
                    print(e)
                    messagebox.showerror(t("common.error"), f"Conversion failed: {e}")
                    self.btn_run.configure(state="normal", text="Retry")
                    self.btn_cancel.configure(state="normal")

            threading.Thread(target=_thread, daemon=True).start()

    app = MeshConverterGUI(targets)
    app.mainloop()

def main():
    targets = _pick_targets()
    if LEGACY_SCOPE not in {"background", "tray_only"} and not targets and not _capture_mode():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            t = filedialog.askopenfilenames(title="Select Mesh Files", filetypes=[("Mesh Files", "*.obj;*.fbx;*.glb;*.gltf;*.stl")])
            if t: targets = list(t)
        except: pass
    
    if not targets: return

    _run_gui_app(targets)


if __name__ == "__main__":
    main()

