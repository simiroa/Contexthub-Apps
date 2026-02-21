"""
Advanced AI Upscaling tools.
Uses Real-ESRGAN and GFPGAN via the embedded Python environment.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import threading
import sys

# Add src to path
# Try getting src from env var first (injected by Host)
src_dir_env = os.environ.get("CTX_ROOT")
if src_dir_env:
    src_dir = Path(src_dir_env) / "src"
else:
    # Fallback for manual run
    current_dir = Path(__file__).parent
    src_dir = current_dir.parent.parent  # features/image -> src (approx)

if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from utils.ai_runner import run_ai_script
from utils.gui_lib import BaseWindow
from utils.image_utils import scan_for_images

class UpscaleGUI(BaseWindow):
    def __init__(self, target_path):
        super().__init__(title="ContextUp AI Upscale", width=450, height=600, icon_name="image_upscale_ai")
        self.target_path = target_path
        self.cancel_flag = False
        
        self.files_to_process, self.scan_count = scan_for_images(target_path)
        
        if not self.files_to_process:
            messagebox.showinfo("Info", f"No image files found.\nScanned {self.scan_count} items.")
            self.destroy()
            return

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)


    def create_widgets(self):
        # 1. Header
        self.add_header(f"Upscale Images ({len(self.files_to_process)})", font_size=20)
        
        # 2. File List
        from utils.gui_lib import FileListFrame
        self.file_scroll = FileListFrame(self.main_frame, self.files_to_process, height=180)
        self.file_scroll.pack(fill="x", padx=20, pady=(0, 10))
        
        # 3. Parameters (2-Column Grid)
        param_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        param_frame.pack(fill="x", padx=20, pady=5)
        param_frame.grid_columnconfigure(0, weight=1)
        param_frame.grid_columnconfigure(1, weight=1)
        
        # Left Column: Scale
        left_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(left_frame, text="Scale Factor:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.scale_var = ctk.IntVar(value=4)
        for val, desc in [(2, "2x (Fast)"), (3, "3x (Balanced)"), (4, "4x (Best)")]:
            ctk.CTkRadioButton(left_frame, text=desc, variable=self.scale_var, value=val).pack(anchor="w", pady=2)
            
        # Right Column: Enhancement
        right_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(right_frame, text="Enhancement:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.face_enhance_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_frame, text="Face Enhancement", variable=self.face_enhance_var).pack(anchor="w", pady=2)
        ctk.CTkLabel(right_frame, text="Restores faces (GFPGAN)", text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=25)

        # 4. Footer
        footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer_frame.pack(fill="x", padx=20, pady=20)
        
        self.progress = ctk.CTkProgressBar(footer_frame, height=10)
        self.progress.pack(fill="x", pady=(0, 15))
        self.progress.set(0)
        
        # Options
        opt_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        opt_row.pack(fill="x", pady=(0, 15))
        
        self.var_delete_org = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_row, text="Delete Original Files", variable=self.var_delete_org, text_color="#E74C3C").pack(side="left")

        # Buttons
        btn_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_row.pack(fill="x")
        
        self.btn_cancel = ctk.CTkButton(btn_row, text="Cancel", height=45, fg_color="transparent", border_width=1, border_color="gray", text_color=("gray10", "gray90"), command=self.cancel_processing)
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_run = ctk.CTkButton(btn_row, text="Start Upscale", height=45, font=ctk.CTkFont(size=14, weight="bold"), command=self.start_upscale)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 0))
        
        self.lbl_status = ctk.CTkLabel(self.main_frame, text="Ready", text_color="gray", font=("", 11))
        self.lbl_status.pack(pady=(0, 5))

    def cancel_processing(self):
        """Cancel ongoing processing or close window."""
        if self.btn_run.cget("state") == "disabled":
            # Processing is running, set cancel flag
            self.cancel_flag = True
            self.lbl_status.configure(text="Cancelling...")
        else:
            # Not processing, just close
            self.destroy()



    def check_memory_risk(self, scale):
        """Check if resolution * scale might cause OOM or freeze."""
        from PIL import Image
        
        high_risk_files = []
        for path in self.files_to_process:
            try:
                with Image.open(path) as img:
                    w, h = img.size
                    pixels = w * h
                    
                    # 4K UHD = 8,294,400 pixels
                    # Risk threshold: Input > 4K OR Output > 8K*8K (~64MP)
                    if pixels > 8_300_000:
                        high_risk_files.append(f"{path.name} ({w}x{h})")
                    elif (pixels * (scale * scale)) > 60_000_000:
                         high_risk_files.append(f"{path.name} (Output > 8K)")
            except:
                pass
                
        if high_risk_files:
            msg = f"Warning: The following files are very large and may crash the Upscaler or freeze your PC:\n\n"
            msg += "\n".join(high_risk_files[:5])
            if len(high_risk_files) > 5: msg += "\n..."
            msg += "\n\nDo you want to continue anyway?"
            
            return messagebox.askyesno("High Memory Usage Warning", msg)
            
        return True



    def start_upscale(self):
        # Check Memory Safety BEFORE threading
        if not self.check_memory_risk(self.scale_var.get()):
            return

        self.cancel_flag = False  # Reset cancel flag for new run
        self.btn_run.configure(state="disabled", text="Processing...")
        threading.Thread(target=self.run_upscale_logic, daemon=True).start()

    def run_upscale_logic(self): # Renamed actual logic
        scale = self.scale_var.get()
        face_enhance = self.face_enhance_var.get()
        
        success_count = 0
        errors = []
        total = len(self.files_to_process)
        
        for i, img_path in enumerate(self.files_to_process):
            # Check cancel flag
            if self.cancel_flag:
                self.after(0, lambda: self.lbl_status.configure(text=f"Cancelled after {success_count} images"))
                break
                
            self.after(0, lambda i=i, total=total, name=img_path.name: 
                         self.lbl_status.configure(text=f"Processing {i+1}/{total}: {name}"))
            self.after(0, lambda v=i/total: self.progress.set(v))
            
            try:
                # Build arguments
                args = [
                    "upscale.py",
                    str(img_path),
                    "--scale", str(scale)
                ]
                
                if face_enhance:
                    args.append("--face-enhance")
                
                # Run AI script
                success, output = run_ai_script(*args)
                
                if success:
                    success_count += 1
                    # Handle Deletion
                    if self.var_delete_org.get() and img_path.exists():
                        try:
                            import os
                            os.remove(img_path)
                        except Exception as e:
                            errors.append(f"Delete failed: {img_path.name}")
                else:
                    errors.append(f"{img_path.name}: {output[:100]}")
                    
            except Exception as e:
                errors.append(f"{img_path.name}: {str(e)[:100]}")
        
        self.after(0, lambda: self.progress.set(1.0))
        self.after(0, lambda: self.lbl_status.configure(text="Done"))
        self.after(0, lambda: self.btn_run.configure(state="normal", text="Start Upscale"))
        
        # Show results
        if errors:
            msg = f"Processed {success_count}/{total} images.\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                msg += "\n..."
            messagebox.showwarning("Completed with Errors", msg)
        else:
            msg = f"Successfully upscaled {success_count} image(s)\n\nScale: {scale}x"
            if face_enhance:
                msg += "\nFace Enhancement: On"
            messagebox.showinfo("Success", msg)
            self.destroy()

    def on_closing(self):
        self.destroy()

def upscale_image(target_path: str, selection=None):
    """
    Upscale image using AI.
    """
    try:
        app = UpscaleGUI(selection or target_path)
        app.mainloop()
            
    except Exception as e:
        messagebox.showerror("Error", f"Upscaling failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        upscale_image(sys.argv[1])
