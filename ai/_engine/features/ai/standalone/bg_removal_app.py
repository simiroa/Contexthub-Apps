import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
import threading
import sys
import os

# Add dependencies to path
current_dir = Path(__file__).resolve().parent
engine_dir = current_dir.parents[2] # standalone -> ai -> features -> _engine
sys.path.append(str(engine_dir))

from utils.gui_lib import BaseWindow
from utils.image_utils import scan_for_images
from utils.ai_runner import start_ai_script, kill_process_tree
from utils.i18n import t

class BackgroundRemovalGUI(BaseWindow):
    def __init__(self, target_path):
        super().__init__(title="ContextUp Background Removal", width=420, height=750, icon_name="image_remove_bg_ai")
        
        self.target_path = target_path
        self.files, self.scan_count = scan_for_images(target_path)
        self.current_process = None
        
        if not self.files:
            messagebox.showinfo(t("common.info"), f"No image files found.\nScanned {self.scan_count} items.\nPath: {target_path}")
            self.destroy()
            sys.exit(0)
            return

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        self.add_header(f"Removing Background ({len(self.files)} images)")
        
        # Model Selection
        ctk.CTkLabel(self.main_frame, text="Select AI Model:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 5))
        
        self.model_var = ctk.StringVar(value="birefnet")
        
        models = [
            ("rmbg", "RMBG-2.0", "Best Balance (92% accuracy)"),
            ("birefnet", "BiRefNet", "Highest Quality"),
            ("inspyrenet", "InSPyReNet", "Fastest")
        ]
        
        for val, name, desc in models:
            frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            frame.pack(anchor="w", padx=30, pady=2)
            ctk.CTkRadioButton(frame, text=name, variable=self.model_var, value=val).pack(side="left")
            ctk.CTkLabel(frame, text=desc, text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left", padx=10)
            
        # Auth Notice
        auth_box = ctk.CTkFrame(self.main_frame, fg_color="gray30", corner_radius=6)
        auth_box.pack(fill="x", padx=30, pady=(10, 0))
        ctk.CTkLabel(auth_box, text="ℹ️ RMBG-2.0 requires Hugging Face approval & token.", 
                    text_color="#E67E22", font=ctk.CTkFont(size=11)).pack(pady=5)
            
        # Options
        ctk.CTkLabel(self.main_frame, text="Output Options:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        self.transparency_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.main_frame, text="Transparent background (PNG)", variable=self.transparency_var).pack(anchor="w", padx=30, pady=5)
        
        # Post-processing
        ctk.CTkLabel(self.main_frame, text="Post-processing:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(10, 5))
        self.postprocess_var = ctk.StringVar(value="none")
        pp_opts = [("None", "none"), ("Edge Smoothing", "smooth"), ("Edge Sharpening", "sharpen"), ("Matte Feathering", "feather")]
        pp_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        pp_frame.pack(anchor="w", padx=30)
        for label, val in pp_opts:
            ctk.CTkRadioButton(pp_frame, text=label, variable=self.postprocess_var, value=val).pack(anchor="w", pady=2)

        # Progress
        self.progress = ctk.CTkProgressBar(self.main_frame)
        self.progress.pack(fill="x", padx=40, pady=(20, 5))
        self.progress.set(0)
        self.lbl_status = ctk.CTkLabel(self.main_frame, text="Ready", text_color="gray")
        self.lbl_status.pack(pady=(0, 10))
        
        # Buttons
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        self.btn_run = ctk.CTkButton(btn_frame, text="Start Processing", command=self.start_processing, height=45, fg_color="#36719F", hover_color="#2A5980")
        self.btn_run.pack(side="right", padx=5, fill="x", expand=True)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", border_width=1, border_color="gray", height=45, command=self.destroy).pack(side="right", padx=5)

    def start_processing(self):
        self.btn_run.configure(state="disabled", text="Processing...")
        threading.Thread(target=self.run_logic, daemon=True).start()

    def run_logic(self):
        model = self.model_var.get()
        transparency = self.transparency_var.get()
        postprocess = self.postprocess_var.get()
        total = len(self.files)
        success_count = 0
        errors = []
        
        for i, img_path in enumerate(self.files):
            self.lbl_status.configure(text=f"Processing {i+1}/{total}: {img_path.name}")
            self.progress.set(i / total)
            
            try:
                args = ["bg_removal.py", str(img_path), "--model", model]
                if not transparency: args.extend(["--no-transparency"])
                if postprocess != "none": args.extend(["--postprocess", postprocess])
                
                self.current_process = start_ai_script(*args)
                stdout, _ = self.current_process.communicate()
                success = (self.current_process.returncode == 0)
                self.current_process = None
                
                if success: success_count += 1
                else: errors.append(f"{img_path.name}: {stdout[:100]}")
            except Exception as e:
                errors.append(f"{img_path.name}: {str(e)[:100]}")
        
        self.progress.set(1.0)
        if errors:
            self.lbl_status.configure(text="Completed with errors")
            self.btn_run.configure(state="normal", text="Retry / Open Folder", fg_color="#D35400", hover_color="#A04000", command=self.open_output_folder)
            msg = f"Processed {success_count}/{total} images.\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5: msg += "\n..."
            messagebox.showwarning(t("common.warning"), msg)
        else:
            self.lbl_status.configure(text="Processing Completed")
            self.btn_run.configure(state="normal", text="Open Output Folder", command=self.open_output_folder)

    def open_output_folder(self):
        import platform
        path = Path(self.target_path)
        if path.is_file(): path = path.parent
        try:
            if platform.system() == "Windows": os.startfile(path)
            else: subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            messagebox.showerror(t("common.error"), f"Could not open folder: {e}")

    def on_closing(self):
        if self.current_process:
            kill_process_tree(self.current_process)
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    target_path = sys.argv[1]
    ctk.set_appearance_mode("System")
    try:
        app = BackgroundRemovalGUI(target_path)
        app.mainloop()
    except Exception as e:
        messagebox.showerror(t("common.error"), f"Failed to start: {e}")
