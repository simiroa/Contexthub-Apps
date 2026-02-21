"""
Texture Tools: Power of 2 Resizing and Utilities.
"""
import sys
import os
import math
from pathlib import Path
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox
import threading

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/image -> src
sys.path.append(str(src_dir))

from utils.gui_lib import BaseWindow, PremiumScrollableFrame
from utils.explorer import get_selection_from_explorer

def get_nearest_pot(n, upscale=True):
    """Returns the nearest power of 2. If upscale is True, rounds up, else rounds down."""
    if n <= 0: return 1
    
    # Log base 2
    log_val = math.log2(n)
    
    if upscale:
        # Round up to next power of 2
        # If already POT, stay same? Or go up? Usually stay same.
        # But user might want to force up. Let's stick to nearest logic requested.
        # "Upscale" usually means >= current.
        pot = math.ceil(log_val)
    else:
        # Downscale
        pot = math.floor(log_val)
        
    return 2 ** int(pot)

class TextureToolsGUI(BaseWindow):
    def __init__(self, target_path=None):
        super().__init__(title="ContextUp Texture Tools", width=500, height=400, icon_name="image_texture_tools")
        
        self.target_path = target_path
        self.selection = []
        
        if target_path:
            try:
                self.selection = get_selection_from_explorer(target_path)
                # Filter for images
                self.selection = [p for p in self.selection if p.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tga', '.bmp', '.webp']]
            except Exception as e:
                print(f"Selection error: {e}")
                
        if not self.selection:
            messagebox.showerror("Error", "No valid images selected.")
            self.destroy()
            return

        self.create_widgets()
        self.update_preview()

    def create_widgets(self):
        # Header
        ctk.CTkLabel(self.main_frame, text="Resize to Power of 2", font=("", 18, "bold")).pack(pady=15)
        
        # File Info
        self.lbl_files = ctk.CTkLabel(self.main_frame, text=f"Selected: {len(self.selection)} files")
        self.lbl_files.pack(pady=5)
        
        # Settings
        settings_frame = ctk.CTkFrame(self.main_frame)
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        # Upscale/Downscale
        self.var_upscale = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(settings_frame, text="Upscale (Round Up)", variable=self.var_upscale, command=self.update_preview).pack(anchor="w", padx=20, pady=10)
        
        # Alpha
        self.var_alpha = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(settings_frame, text="Preserve Alpha Channel", variable=self.var_alpha).pack(anchor="w", padx=20, pady=10)
        
        # Preview Area
        self.preview_frame = PremiumScrollableFrame(self.main_frame, height=150)
        self.preview_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Actions
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(btn_frame, text="Process All", command=self.run_process, fg_color="green").pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, fg_color="transparent", border_width=1, text_color="gray").pack(side="right", padx=5)

    def update_preview(self):
        # Clear
        for widget in self.preview_frame.winfo_children(): widget.destroy()
        
        upscale = self.var_upscale.get()
        
        for path in self.selection[:10]: # Limit preview
            try:
                with Image.open(path) as img:
                    w, h = img.size
                    target_w = get_nearest_pot(w, upscale)
                    target_h = get_nearest_pot(h, upscale)
                    
                    row = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
                    row.pack(fill="x", pady=2)
                    
                    ctk.CTkLabel(row, text=path.name, width=150, anchor="w").pack(side="left")
                    ctk.CTkLabel(row, text=f"{w}x{h}  ➜  {target_w}x{target_h}", font=("Consolas", 12)).pack(side="left", padx=10)
            except Exception:
                pass
                
        if len(self.selection) > 10:
            ctk.CTkLabel(self.preview_frame, text=f"...and {len(self.selection)-10} more").pack(pady=5)

    def run_process(self):
        upscale = self.var_upscale.get()
        preserve_alpha = self.var_alpha.get()
        
        def _process():
            count = 0
            for path in self.selection:
                try:
                    with Image.open(path) as img:
                        w, h = img.size
                        target_w = get_nearest_pot(w, upscale)
                        target_h = get_nearest_pot(h, upscale)
                        
                        if w == target_w and h == target_h:
                            continue # Skip if already POT
                            
                        # Resize
                        resample = Image.Resampling.LANCZOS
                        resized = img.resize((target_w, target_h), resample)
                        
                        # Save (Overwrite or New? Let's overwrite as implied by "Resize", but maybe backup?)
                        # User request didn't specify, but usually tools like this modify or save copy.
                        # Let's save as copy to be safe: _pot.png
                        # Actually user said "Resize to Power of 2", implying modification.
                        # But safety first. Let's overwrite but keep original? No, that's messy.
                        # Let's save with suffix for now.
                        
                        save_path = path.parent / f"{path.stem}_pot{path.suffix}"
                        
                        if not preserve_alpha and resized.mode == 'RGBA':
                             resized = resized.convert('RGB')
                             
                        resized.save(save_path)
                        count += 1
                        
                except Exception as e:
                    print(f"Failed to process {path}: {e}")
            
            self.after(0, lambda: messagebox.showinfo("Complete", f"Processed {count} images."))
            self.after(0, self.destroy)
            
        threading.Thread(target=_process, daemon=True).start()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        anchor = sys.argv[1]
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("image_texture_tool", anchor, timeout=0.2) is None:
            sys.exit(0)

        app = TextureToolsGUI(sys.argv[1])
        app.mainloop()
