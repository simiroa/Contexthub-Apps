import sys
import os
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Add src to path for utils
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from utils.gui_lib import (BaseWindow, FileListFrame, setup_theme, THEME_BG, THEME_CARD, THEME_BORDER, THEME_TEXT_DIM,
                                THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER,
                                THEME_ACCENT, THEME_TEXT_MAIN)
from utils.i18n import t
from utils.files import get_safe_path

class PDFMergeGUI(BaseWindow):
    def __init__(self, files_list=None, dev_mode=False):
        super().__init__(title=t("pdf_merge.title"), width=600, height=400, icon_name="pdf_merge")
        self.dev_mode = dev_mode
        
        raw_files = [Path(f) for f in files_list] if files_list else []
        self.files = [f for f in raw_files if f.exists() and f.suffix.lower() == '.pdf']
        self.files = list(dict.fromkeys(self.files)) # Unique files

        if len(self.files) < 2 and not self.dev_mode:
            messagebox.showinfo(t("common.info"), t("pdf_merge.select_min_2"))
            self.destroy()
            return
        
        if self.dev_mode:
            if not self.files:
                self.files = [Path("sample1.pdf"), Path("sample2.pdf")]
            self.after(5000, self.destroy)

        self._is_running = False
        self.create_ui()

    def create_ui(self):
        # Header Section
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(2, 5))
        
        ctk.CTkLabel(header_frame, text="🔗 " + t("pdf_merge.header"), 
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=THEME_TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(header_frame, text=t("doc_convert.files_count", count=len(self.files)), 
                     font=ctk.CTkFont(size=12), text_color=THEME_TEXT_DIM).pack(side="right", pady=(5, 0))

        # File List
        self.file_list_frame = FileListFrame(self.main_frame, self.files, height=80)
        self.file_list_frame.pack(fill="x", padx=10, pady=1)

        # Progress Section
        self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=10)
        
        self.status_label = ctk.CTkLabel(self.progress_frame, text=t("common.ready"), text_color=THEME_TEXT_DIM, font=ctk.CTkFont(size=11))
        self.status_label.pack(anchor="w")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=8, fg_color=THEME_BORDER, progress_color=THEME_ACCENT)
        self.progress_bar.pack(fill="x", pady=(2, 5))
        self.progress_bar.set(0)
        
        self.detail_label = ctk.CTkLabel(self.progress_frame, text="", text_color=THEME_TEXT_DIM, font=ctk.CTkFont(size=10))
        self.detail_label.pack(anchor="w")

        # Action Buttons in Footer
        self.btn_run = ctk.CTkButton(self.footer_frame, text=t("pdf_merge.merge_btn"), height=35,
                                     command=self.start_merge, fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER)
        self.btn_run.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        self.btn_cancel = ctk.CTkButton(self.footer_frame, text=t("common.cancel"), height=35,
                                        command=self.destroy, fg_color="transparent", border_width=1, border_color=THEME_BORDER)
        self.btn_cancel.pack(side="right")
        
        self.after(100, self.adjust_window_size)

    def start_merge(self):
        if self._is_running: return
        self._is_running = True
        self.btn_run.configure(state="disabled", text=t("common.processing"))
        
        threading.Thread(target=self._run_thread, daemon=True).start()

    def _update_status(self, text, detail="", progress=None):
        def update():
            self.status_label.configure(text=text)
            self.detail_label.configure(text=detail)
            if progress is not None: self.progress_bar.set(progress)
        self.after(0, update)

    def _run_thread(self):
        try:
            from pypdf import PdfWriter
            self._update_status(t("common.processing"), t("common.initializing"), 0.1)
            
            merger = PdfWriter()
            total = len(self.files)
            
            for idx, pdf in enumerate(self.files):
                self._update_status(t("common.processing"), pdf.name, (idx + 1) / total * 0.8)
                merger.append(str(pdf))
            
            dest = get_safe_path(self.files[0].parent / "merged.pdf")
            self._update_status(t("common.processing"), t("common.completed"), 0.9)
            merger.write(str(dest))
            merger.close()
            
            self._update_status(t("common.success"), "", 1.0)
            self.after(0, lambda: self._finish(dest))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(t("common.error"), f"Merge failed: {e}"))
            self.after(0, self.destroy)

    def _finish(self, dest):
        messagebox.showinfo(t("common.success"), t("pdf_merge.success_fmt", count=len(self.files), dest=dest.name))
        self.destroy()

if __name__ == "__main__":
    setup_theme()
    app = PDFMergeGUI(sys.argv[1:], dev_mode="--dev" in sys.argv)
    app.mainloop()
