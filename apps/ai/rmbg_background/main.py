import os
import sys
import subprocess
from pathlib import Path
import runpy

LEGACY_ID = 'rmbg_background'
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
        from utils.gui_lib import BaseWindow, FileListFrame, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_BORDER, ModelManagerFrame
    except ImportError:
        from contexthub.utils.gui_lib import BaseWindow, FileListFrame, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_BORDER, ModelManagerFrame
    
    from utils.i18n import t

    class RMBGWindow(BaseWindow):
        def __init__(self, targets):
            super().__init__(title="rmbg_background.title", width=600, height=520, icon_name="ai_icon")
            self.targets = targets
            self.create_widgets()
            
        def create_widgets(self):
            self.add_header(t("rmbg_background.header"))
            
            ctk.CTkLabel(self.main_frame, text=f"{t('rmbg_background.targets_label')} ({len(self.targets)})", font=("", 14, "bold")).pack(anchor="w", padx=20, pady=(10,5))
            
            path_targets = [Path(t) for t in self.targets]
            self.file_list = FileListFrame(self.main_frame, path_targets, height=120)
            self.file_list.pack(fill="x", padx=20, pady=(0, 20))
            from utils import paths
            model_root = paths.BIREFNET_DIR
            self.model_mgr = ModelManagerFrame(self.main_frame, "BiRefNet", model_root, download_command=self.download_models, check_callback=self._has_birefnet_cache)
            self.model_mgr.pack(fill="x", padx=20, pady=(0, 10))
            
            self.lbl_status = ctk.CTkLabel(self.main_frame, text=t("common.ready"), text_color="gray")
            self.lbl_status.pack(pady=5)
            
            self.progress = ctk.CTkProgressBar(self.main_frame)
            self.progress.pack(fill="x", padx=20, pady=5)
            self.progress.set(0)
            
            btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            btn_frame.pack(fill="x", padx=20, pady=20)
            
            self.btn_cancel = ctk.CTkButton(btn_frame, text=t("common.close"), command=self.destroy, fg_color="transparent", border_width=1, border_color=THEME_BORDER, text_color=("gray10", "gray90"))
            self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))
            
            self.btn_run = ctk.CTkButton(btn_frame, text=t("rmbg_background.start_btn"), command=self.run_process, fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER)
            self.btn_run.pack(side="left", fill="x", expand=True)

        def _has_birefnet_cache(self):
            try:
                from utils import paths
                hub = paths.RESOURCES_DIR / "cache" / "hf" / "hub"
                repo_dir = hub / "models--ZhengPeng7--BiRefNet"
                if repo_dir.exists():
                    blobs = repo_dir / "blobs"
                    return blobs.exists() and any(blobs.iterdir())
                return False
            except Exception:
                return False


        def download_models(self):
            self.model_mgr.lbl_status.configure(text=t("ai_common.downloading"), text_color="#E67E22")
            self.model_mgr.btn_action.configure(state="disabled")

            def _dl():
                try:
                    engine_dir = Path(__file__).resolve().parent.parent / "_engine"
                    dl_script = engine_dir / "setup" / "download_models.py"
                    cmd = [sys.executable, str(dl_script), "--bgrm"]
                    proc = subprocess.run(cmd, capture_output=True, text=True)
                    success = (proc.returncode == 0)
                    if success:
                        self.after(0, lambda: self.model_mgr.check_status())
                    else:
                        self.after(0, lambda: self.model_mgr.lbl_status.configure(text=t("ai_common.download_failed"), text_color="red"))
                except Exception:
                    self.after(0, lambda: self.model_mgr.lbl_status.configure(text=t("ai_common.download_failed"), text_color="red"))

                self.after(0, lambda: self.model_mgr.btn_action.configure(state="normal"))

            threading.Thread(target=_dl, daemon=True).start()

        def run_process(self):
            self.btn_run.configure(state="disabled", text=t("common.processing"))
            self.btn_cancel.configure(state="disabled")
            
            def _thread():
                try:
                    from features.ai import tools
                    
                    total = len(self.targets)
                    for i, target in enumerate(self.targets):
                        self.lbl_status.configure(text=f"Processing {Path(target).name}...")
                        tools.remove_background(target) # Assuming this handles individual file
                        self.progress.set((i+1)/total)
                    
                    self.lbl_status.configure(text=t("common.complete"))
                    messagebox.showinfo(t("common.success"), t("common.complete"))
                    self.after(500, self.destroy)
                    
                except Exception as e:
                    self.lbl_status.configure(text=t("common.error"), text_color="red")
                    print(e)
                    messagebox.showerror(t("common.error"), t("rmbg_background.failed").format(error=e))
                    self.btn_run.configure(state="normal", text=t("rmbg_background.retry"))
                    self.btn_cancel.configure(state="normal")

            threading.Thread(target=_thread, daemon=True).start()

    app = RMBGWindow(targets)
    app.mainloop()


def main():
    targets = _pick_targets()
    if LEGACY_SCOPE not in {"background", "tray_only"} and not targets and not _capture_mode():
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(t("common.warning"), t("rmbg_background.no_target"))
        except Exception:
            pass
        return

    _run_gui_app(targets)


if __name__ == "__main__":
    main()

