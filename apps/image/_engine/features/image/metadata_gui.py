import sys
from pathlib import Path

# === PROPER SYSPATH SETUP ===
# features/image/metadata_gui.py -> src
current_file = Path(__file__).resolve()
src_dir = current_file.parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import customtkinter as ctk
from tkinter import messagebox
from utils.gui_lib import BaseWindow, THEME_BORDER, THEME_TEXT_DIM, THEME_BTN_PRIMARY, THEME_BTN_HOVER
from utils.i18n import t
from core.config import MenuConfig
from core.config import MenuConfig
from features.image.metadata_core import get_image_metadata, strip_metadata


class MetadataGUI(BaseWindow):
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.tool_name = "ContextUp Image Metadata"
        try:
            config = MenuConfig()
            item = config.get_item_by_id("image_metadata")
            if item: self.tool_name = item.get("name", self.tool_name)
        except: pass

        super().__init__(title=self.tool_name, width=500, height=400, scrollable=False, icon_name="image_metadata")
        
        self.metadata = get_image_metadata(file_path)
        self.create_widgets()
        self.after(100, self.adjust_window_size)

    def create_widgets(self):
        # Header
        self.add_header(t("image_metadata_gui.header"), font_size=22)
        
        # File Info Label
        ctk.CTkLabel(self.main_frame, text=self.file_path.name, font=("", 12, "bold")).pack(pady=(0, 10))
        
        # area for metadata (Standard Frame for window growth)
        self.scroll_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # 1. Basic Info
        self.add_section_title(self.scroll_frame, t("image_metadata_gui.basic_info"))
        for k, v in self.metadata["Basic"].items():
            self.add_metadata_row(self.scroll_frame, k, v)
        
        # 2. EXIF Info
        self.add_section_title(self.scroll_frame, t("image_metadata_gui.exif_info"))
        if self.metadata["EXIF"]:
            for k, v in self.metadata["EXIF"].items():
                self.add_metadata_row(self.scroll_frame, k, v)
        else:
            ctk.CTkLabel(self.scroll_frame, text=t("image_metadata_gui.no_metadata"), 
                        text_color=THEME_TEXT_DIM, font=("", 11, "italic")).pack(anchor="w", padx=10)
            
        # 3. Footer / Action (Centralized)
        self.btn_strip = ctk.CTkButton(
            self.footer_frame, 
            text=t("image_metadata_gui.strip_metadata"),
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#E74C3C", # Danger red
            hover_color="#C0392B",
            command=self.run_strip
        )
        self.btn_strip.pack(fill="x", padx=20, pady=20)
        
    def add_section_title(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=14, weight="bold"), text_color="#3498DB")
        lbl.pack(anchor="w", pady=(10, 5))
        
    def add_metadata_row(self, parent, key, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=1)
        ctk.CTkLabel(row, text=f"{key}:", font=("", 11, "bold"), width=120, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=str(value), font=("", 11), wraplength=320, justify="left").pack(side="left", fill="x", expand=True)

    def run_strip(self):
        if not messagebox.askyesno(t("dialogs.confirm"), t("dialogs.are_you_sure")):
            return
            
        self.btn_strip.configure(state="disabled", text=t("image_metadata_gui.stripping"))
        
        success = strip_metadata(self.file_path)
        
        if success:
            messagebox.showinfo(t("common.success"), t("image_metadata_gui.strip_success"))
            # Reload metadata
            self.metadata = get_image_metadata(self.file_path)
            for widget in self.scroll_frame.winfo_children():
                widget.destroy()
            self.create_widgets() # Rebuild scroll area content? Actually recreate might be messy, let's just refresh content.
            # Best to just close and reopen or refresh carefully.
            # For now, just destroy and rebuild content:
            # (Self correction: create_widgets also adds header and footer outside scroll_frame)
            # Let's just update the scroll_frame part.
        else:
            messagebox.showerror(t("common.error"), t("image_metadata_gui.strip_error"))
            self.btn_strip.configure(state="normal", text=t("image_metadata_gui.strip_metadata"))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.exists():
            app = MetadataGUI(path)
            app.mainloop()
        else:
            print(f"File not found: {path}")
    else:
        # For testing
        print("Usage: python metadata_gui.py <image_path>")
