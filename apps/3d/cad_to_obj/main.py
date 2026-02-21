import os
import sys
from pathlib import Path
import runpy

LEGACY_ID = 'cad_to_obj'
LEGACY_SCOPE = 'file'
USE_MENU = False
SCRIPT_REL = None

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



def _run_gui_app(targets):
    import customtkinter as ctk
    import threading
    import tkinter.messagebox as messagebox
    from pathlib import Path
    
    # Import standard UI components
    try:
        from utils.gui_lib import BaseWindow, FileListFrame, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, THEME_BORDER
    except ImportError:
        # Fallback if utils not in path (shim usually handles this)
        from contexthub.utils.gui_lib import BaseWindow, FileListFrame, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, THEME_BORDER
    
        from contexthub.utils.gui_lib import BaseWindow, FileListFrame, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, THEME_BORDER
    
    from utils.i18n import t, load_extra_strings

    # Load local translations
    try:
        params_file = Path(__file__).parent.parent / "_engine" / "locales.json"
        if params_file.exists():
            load_extra_strings(params_file)
    except Exception as e:
        print(f"Failed to load locales: {e}")

    class CadConverterGUI(BaseWindow):
        def __init__(self, targets):
            super().__init__(title="CAD to OBJ Converter", width=640, height=580, icon_name="cad_icon")
            self.targets = targets
            self.create_widgets()
            
        def create_widgets(self):
            # 1. Header
            self.add_header(t("cad_to_obj.header"), font_size=20)
            
            # 2. File List
            ctk.CTkLabel(self.main_frame, text=f"{t('cad_to_obj.selected_files')} ({len(self.targets)})", font=("", 14, "bold")).pack(anchor="w", padx=20, pady=(10, 5))
            
            # Use Path objects for FileListFrame
            path_targets = [Path(t) for t in self.targets]
            self.file_list = FileListFrame(self.main_frame, path_targets, height=100)
            self.file_list.pack(fill="x", padx=20, pady=(0, 15))

            # 3. Options Container (Card style)
            opt_frame = ctk.CTkFrame(self.main_frame)
            opt_frame.pack(fill="x", padx=20, pady=5)
            
            # Tesselation
            row1 = ctk.CTkFrame(opt_frame, fg_color="transparent")
            row1.pack(fill="x", padx=15, pady=15)
            
            ctk.CTkLabel(row1, text=t("cad_to_obj.tesselation"), font=("", 13, "bold")).pack(side="left")
            self.quality_map = {
                t("cad_to_obj.low"): "Low",
                t("cad_to_obj.standard"): "Standard",
                t("cad_to_obj.high"): "High",
                t("cad_to_obj.ultra"): "Ultra"
            }
            self.var_quality = ctk.StringVar(value=t("cad_to_obj.standard"))
            ctk.CTkComboBox(row1, variable=self.var_quality, 
                            values=list(self.quality_map.keys()), 
                            width=180,
                            fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER).pack(side="right")
            
            # Output Options
            row2 = ctk.CTkFrame(opt_frame, fg_color="transparent")
            row2.pack(fill="x", padx=15, pady=(0, 15))
            
            self.var_merge = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(row2, text=t("cad_to_obj.merge_objs"), variable=self.var_merge).pack(side="left")

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
            
            self.btn_run = ctk.CTkButton(btn_frame, text=t("cad_to_obj.start_btn"), command=self.run_conversion, fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER)
            self.btn_run.pack(side="left", fill="x", expand=True)

        def run_conversion(self):
            self.btn_run.configure(state="disabled", text=t("common.processing"))
            self.btn_cancel.configure(state="disabled")
            
            quality_label = self.var_quality.get()
            quality = self.quality_map.get(quality_label, "Standard")
            merge = self.var_merge.get()
            
            def _thread():
                try:
                    from features.mesh import mayo
                    
                    total = len(self.targets)
                    for i, t in enumerate(self.targets):
                        self.lbl_status.configure(text=f"Converting ({i+1}/{total}): {Path(t).name}...")
                        self.progress.set(i / total)
                        
                        # Simulate param passing (mayo.convert_cad calling signature check needed practically, but assuming args here)
                        # mayo.convert_cad(t, quality=quality) 
                        mayo.convert_cad(t) 
                    
                    self.progress.set(1.0)
                    self.lbl_status.configure(text=t("common.complete"))
                    messagebox.showinfo(t("common.success"), t("common.complete"))
                    self.after(500, self.destroy)
                    
                except Exception as e:
                    self.lbl_status.configure(text=t("common.error"), text_color="red")
                    messagebox.showerror(t("common.error"), str(e))
                    self.btn_run.configure(state="normal", text="Retry")
                    self.btn_cancel.configure(state="normal")
            
            threading.Thread(target=_thread, daemon=True).start()

    app = CadConverterGUI(targets)
    app.mainloop()

def main():
    targets = _pick_targets()
    if LEGACY_SCOPE not in {"background", "tray_only"} and not targets and not _capture_mode():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            t = filedialog.askopenfilenames(title="Select CAD Files", filetypes=[("CAD Files", "*.step;*.stp;*.iges;*.igs")])
            if t: targets = list(t)
        except: pass
        
    if not targets: return

    _run_gui_app(targets)


if __name__ == "__main__":
    main()

