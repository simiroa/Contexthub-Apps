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

class PDFSplitGUI(BaseWindow):
    def __init__(self, files_list=None, dev_mode=False):
        super().__init__(title=t("pdf_split.split_title"), width=600, height=450, icon_name="pdf_split")
        self.dev_mode = dev_mode
        
        raw_files = [Path(f) for f in files_list] if files_list else []
        self.files = [f for f in raw_files if f.exists() and f.suffix.lower() == '.pdf']
        self.files = list(dict.fromkeys(self.files)) # Unique files

        if not self.files and not self.dev_mode:
            messagebox.showerror(t("common.error"), t("pdf_split.no_files"))
            self.destroy()
            return
        
        if self.dev_mode:
            if not self.files:
                self.files = [Path("sample_document.pdf")]
            self.after(5000, self.destroy)

        self._is_running = False
        self._mode = 'pdf' # 'pdf' or 'png'
        
        self.create_ui()

    def create_ui(self):
        # Header Section
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(2, 5))
        
        ctk.CTkLabel(header_frame, text="✂️ " + t("pdf_split.split_title"), 
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=THEME_TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(header_frame, text=t("doc_convert.files_count", count=len(self.files)), 
                     font=ctk.CTkFont(size=12), text_color=THEME_TEXT_DIM).pack(side="right", pady=(5, 0))

        # File List
        self.file_list_frame = FileListFrame(self.main_frame, self.files, height=80)
        self.file_list_frame.pack(fill="x", padx=10, pady=1)

        # Settings Card
        settings_card = self.create_card_frame(self.main_frame)
        settings_card.pack(fill="x", padx=10, pady=2)
        
        # Mode Section
        mode_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        mode_row.pack(fill="x", padx=15, pady=2)
        
        ctk.CTkLabel(mode_row, text=t("doc_convert.target_format"), font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        
        self.mode_var = ctk.StringVar(value=t("pdf_split.mode_pdf"))
        self.mode_menu = ctk.CTkOptionMenu(mode_row, variable=self.mode_var, 
                                          values=[t("pdf_split.mode_pdf"), t("pdf_split.mode_png"), t("pdf_split.mode_jpg")],
                                          command=self._on_mode_change, height=32,
                                          fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, 
                                          button_hover_color=THEME_DROPDOWN_HOVER)
        self.mode_menu.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Options Container
        self.options_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        self.options_frame.pack(fill="x", padx=15, pady=0)
        
        # DPI Setting
        self.dpi_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        ctk.CTkLabel(self.dpi_frame, text="DPI:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 5))
        self.dpi_var = ctk.StringVar(value="300")
        self.dpi_menu = ctk.CTkOptionMenu(self.dpi_frame, variable=self.dpi_var,
                                           values=["72", "150", "300", "600"], 
                                           height=24, width=80, font=ctk.CTkFont(size=11))
        self.dpi_menu.pack(side="left")
        
        # Initial Hide
        self.dpi_frame.pack_forget()

        # Progress Section
        self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=5)
        
        self.status_label = ctk.CTkLabel(self.progress_frame, text=t("common.ready"), text_color=THEME_TEXT_DIM, font=ctk.CTkFont(size=11))
        self.status_label.pack(anchor="w")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=8, fg_color=THEME_BORDER, progress_color=THEME_ACCENT)
        self.progress_bar.pack(fill="x", pady=(2, 5))
        self.progress_bar.set(0)
        
        self.detail_label = ctk.CTkLabel(self.progress_frame, text="", text_color=THEME_TEXT_DIM, font=ctk.CTkFont(size=10))
        self.detail_label.pack(anchor="w")

        # Action Buttons in Footer
        self.btn_run = ctk.CTkButton(self.footer_frame, text=t("pdf_split.split_btn"), height=35,
                                     command=self.start_work, fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER)
        self.btn_run.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        self.btn_cancel = ctk.CTkButton(self.footer_frame, text=t("common.cancel"), height=35,
                                        command=self.destroy, fg_color="transparent", border_width=1, border_color=THEME_BORDER)
        self.btn_cancel.pack(side="right")
        
        self.after(100, self.adjust_window_size)

    def _on_mode_change(self, choice):
        if "Image" in choice:
            self.dpi_frame.pack(side="left", pady=0)
        else:
            self.dpi_frame.pack_forget()
        self.after(10, self.adjust_window_size)

    def start_work(self):
        if self._is_running: return
        self._is_running = True
        self.btn_run.configure(state="disabled", text=t("common.processing"))
        self.btn_cancel.configure(text=t("common.stop"), command=self._on_cancel)
        
        threading.Thread(target=self._run_thread, daemon=True).start()

    def _on_cancel(self):
        self._is_running = False
        self.status_label.configure(text=t("common.processing"), text_color="orange")

    def _update_status(self, text, detail="", progress=None):
        def update():
            self.status_label.configure(text=text)
            self.detail_label.configure(text=detail)
            if progress is not None: self.progress_bar.set(progress)
        self.after(0, update)

    def _run_thread(self):
        choice = self.mode_var.get()
        dpi = int(self.dpi_var.get())
        success_count = 0
        errors = []
        
        total = len(self.files)
        
        for idx, path in enumerate(self.files):
            if not self._is_running: break
            
            self._update_status(t("common.processing"), path.name, idx / total)
            
            try:
                output_dir = get_safe_path(path.parent / path.stem)
                output_dir.mkdir(exist_ok=True)
                
                if "PDF" in choice:
                    from pypdf import PdfReader, PdfWriter
                    reader = PdfReader(str(path))
                    for i, page in enumerate(reader.pages):
                        if not self._is_running: break
                        writer = PdfWriter()
                        writer.add_page(page)
                        out_path = get_safe_path(output_dir / f"{path.stem}_page_{i+1:03d}.pdf")
                        with open(out_path, "wb") as f:
                            writer.write(f)
                    success_count += 1
                else: # Images
                    from pdf2image import convert_from_path
                    fmt = "PNG" if "PNG" in choice else "JPEG"
                    ext = ".png" if fmt == "PNG" else ".jpg"
                    images = convert_from_path(str(path), dpi=dpi)
                    for i, image in enumerate(images):
                        if not self._is_running: break
                        out_path = get_safe_path(output_dir / f"{path.stem}_page_{i+1:03d}{ext}")
                        image.save(str(out_path), fmt)
                    success_count += 1
            except Exception as e:
                errors.append(f"{path.name}: {e}")
        
        self.after(0, lambda: self._finish(success_count, errors))

    def _finish(self, count, errors):
        self._is_running = False
        self.btn_run.configure(state="normal", text=t("pdf_split.split_btn"))
        self.btn_cancel.configure(text=t("common.cancel"), command=self.destroy)
        
        if errors:
            msg = t("common.error") + ":\n" + "\n".join(errors[:3])
            self._update_status(t("common.completed_with_errors"), f"{count} {t('common.success')}", 1.0)
            messagebox.showwarning(t("common.warning"), msg)
        else:
            self._update_status(t("common.success_msg"), t("pdf_split.success_fmt", count=count), 1.0)
            messagebox.showinfo(t("common.success"), t("pdf_split.success_fmt", count=count))
            self.destroy()

if __name__ == "__main__":
    setup_theme()
    app = PDFSplitGUI(sys.argv[1:], dev_mode="--dev" in sys.argv)
    app.mainloop()
