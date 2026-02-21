"""
Mayo CAD conversion tools.
"""
import subprocess
import sys
import os
from pathlib import Path
from tkinter import messagebox
import tkinter as tk
import customtkinter as ctk
import threading

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.append(str(src_dir))

from utils.external_tools import get_mayo_conv, get_mayo_viewer
from utils.i18n import t

try:
    from core.settings import load_settings
    from utils.gui_lib import BaseWindow
    from utils.explorer import get_selection_from_explorer
except Exception as e:
    print(f"Failed to import local modules: {e}")

def _is_headless():
    return os.environ.get("CTX_HEADLESS") == "1" or os.environ.get("CTX_CAPTURE_MODE") == "1"

def open_with_mayo(target_path: str):
    """
    Open the selected file(s) with Mayo.
    """
    try:
        selection = get_selection_from_explorer(target_path)
        if not selection:
            selection = [target_path]
            
        mayo = get_mayo_viewer()
        if not mayo:
            _show_mayo_install_guide()
            return

        # Open first file
        if selection:
            file_to_open = selection[0]
            subprocess.Popen([mayo, str(file_to_open)])
            
    except Exception as e:
        messagebox.showerror(t("common.error"), t("cad_to_obj.failed_to_open_mayo").format(error=e))

def _show_mayo_install_guide():
    """Show Mayo installation guide with download link."""
    if _is_headless():
        return
    msg = (
        f"{t('cad_to_obj.mayo_not_installed')}\n\n"
        f"{t('cad_to_obj.mayo_description')}\n\n"
        f"{t('cad_to_obj.install_steps_header')}\n"
        f"{t('cad_to_obj.install_step1')}\n"
        f"{t('cad_to_obj.install_step2')}\n"
        f"{t('cad_to_obj.install_step3')}\n\n"
        f"{t('cad_to_obj.open_download_page')}"
    )
    
    if messagebox.askyesno(t("cad_to_obj.mayo_required"), msg):
        import webbrowser
        webbrowser.open("https://github.com/fougue/mayo/releases")

class CadConvertGUI(BaseWindow):
    def __init__(self, target_path, demo=False):
        super().__init__(title="ContextUp CAD Converter (Mayo)", width=600, height=400, icon_name="cad_convert_obj")
        self.target_path = target_path
        self.demo_mode = demo or _is_headless()
        self.files_to_convert = []
        
        self.init_files()
        self.create_widgets()
        
    def init_files(self):
        if self.demo_mode:
            # Demo mode
            self.files_to_convert = [Path("demo_model.step"), Path("assembly.stp")]
            return
            
        selection = get_selection_from_explorer(self.target_path)
        if not selection:
            selection = [self.target_path]
            
        cad_exts = {'.step', '.stp', '.iges', '.igs'}
        self.files_to_convert = [Path(p) for p in selection if Path(p).suffix.lower() in cad_exts]
        
        if not self.files_to_convert:
            messagebox.showinfo("Info", "No CAD files selected.")
            self.destroy()
            return

    def create_widgets(self):
        # Header
        header = ctk.CTkLabel(self.main_frame, text=f"{t('cad_to_obj.selected_files')} ({len(self.files_to_convert)})", font=("Segoe UI", 18, "bold"))
        header.pack(pady=20)
        
        # File List
        scroll = ctk.CTkScrollableFrame(self.main_frame, height=150)
        scroll.pack(fill="x", padx=20, pady=10)
        
        for f in self.files_to_convert:
            lbl = ctk.CTkLabel(scroll, text=f.name, anchor="w")
            lbl.pack(fill="x")
            
        # Buttons
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(pady=20, fill="x", padx=20)
        
        self.btn_convert = ctk.CTkButton(btn_frame, text=t("cad_to_obj.convert"), command=self.run_conversion, height=40, font=("Segoe UI", 14, "bold"))
        self.btn_convert.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_open = ctk.CTkButton(btn_frame, text=t("cad_to_obj.open_mayo"), command=self.open_in_mayo, height=40, fg_color="#444", hover_color="#555")
        self.btn_open.pack(side="right", fill="x", expand=True, padx=(10, 0))
        
        # Status
        self.status_label = ctk.CTkLabel(self.main_frame, text=t("common.ready"), text_color="gray")
        self.status_label.pack(side="bottom", pady=10)

    def open_in_mayo(self):
        try:
            mayo = get_mayo_viewer()
            if self.files_to_convert:
                subprocess.Popen([mayo, str(self.files_to_convert[0])])
        except FileNotFoundError:
            messagebox.showerror(t("common.error"), t("cad_to_obj.mayo_not_found"))

    def run_conversion(self):
        self.btn_convert.configure(state="disabled")
        self.status_label.configure(text=t("common.processing"), text_color="yellow")
        
        def _process():
            try:
                mayo = get_mayo_conv()
                success_count = 0
                errors = []
                
                for path in self.files_to_convert:
                    try:
                        if self.demo_mode:
                            import time
                            time.sleep(0.5)
                            success_count += 1
                        else:
                            output_path = path.with_suffix('.obj')
                            cmd = [mayo, "-i", str(path), "-o", str(output_path), "--export-format", "obj"]
                            subprocess.run(cmd, check=True, capture_output=True, text=True)
                            success_count += 1
                    except Exception as e:
                        errors.append(f"{path.name}: {e}")
                
                self.after(0, lambda: self._finish(success_count, errors))
            except FileNotFoundError as e:
                self.after(0, lambda: messagebox.showerror(t("common.error"), str(e)))
                self.after(0, self.destroy)
            
        threading.Thread(target=_process, daemon=True).start()
        
    def _finish(self, success_count, errors):
        self.btn_convert.configure(state="normal")
        if errors:
            msg = f"Converted {success_count}/{len(self.files_to_convert)} files.\nErrors:\n" + "\n".join(errors[:3])
            messagebox.showwarning(t("common.warning"), msg)
            self.status_label.configure(text=t("common.error"), text_color="orange")
        else:
            messagebox.showinfo(t("common.success"), f"Successfully converted {success_count} files.")
            self.status_label.configure(text=t("common.complete"), text_color="green")
            self.after(1000, self.destroy)

def convert_cad(target_path: str):
    app = CadConvertGUI(target_path)
    app.mainloop()

if __name__ == "__main__":
    if "--demo" in sys.argv or _is_headless():
        app = CadConvertGUI(None, demo=True)
        app.mainloop()
    elif len(sys.argv) > 1:
        convert_cad(sys.argv[1])
