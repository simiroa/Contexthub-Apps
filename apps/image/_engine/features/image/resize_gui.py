import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
from PIL import Image
import sys
import threading
import math
import shutil
import os

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/image -> src
sys.path.append(str(src_dir))

from utils.explorer import get_selection_from_explorer
from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_BTN_DANGER, THEME_BTN_DANGER_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from utils.image_utils import scan_for_images
from utils.files import get_safe_path
from utils.ai_runner import run_ai_script
from utils.i18n import t

def _is_headless():
    return os.environ.get("CTX_HEADLESS") == "1" or os.environ.get("CTX_CAPTURE_MODE") == "1"

class ImageResizeGUI(BaseWindow):
    def __init__(self, files_list):
        super().__init__(title="ContextUp Image Resize (POT)", width=650, height=600, scrollable=False, icon_name="image_resize_pot")
        
        # Accept list of files directly
        if isinstance(files_list, (list, tuple)) and len(files_list) > 0:
            self.files, self.candidates_count = scan_for_images(files_list)
        else:
            self.files, self.candidates_count = scan_for_images(files_list)
        
        if not self.files:
            if _is_headless():
                self.files = [Path("demo_image.png")]
                self.candidates_count = len(self.files)
            else:
                messagebox.showerror(t("common.error"), t("image_resize_gui.no_valid_images"))
                self.destroy()
                return

        self.current_img_size = (0, 0)
        try:
            with Image.open(self.files[0]) as img:
                self.current_img_size = img.size
        except:
            pass
        
        self.cancel_flag = False

        self.create_widgets()
        self.update_recommendation()
        self.after(100, self.adjust_window_size)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)


    def create_widgets(self):
        # 1. Header
        header_text = t("image_resize_gui.title").split("(")[0].strip()
        self.add_header(f"{header_text} ({len(self.files)})", font_size=20)
        
        # 2. File List (Slightly reduced height)
        from utils.gui_lib import FileListFrame
        self.file_scroll = FileListFrame(self.main_frame, self.files, height=150)
        self.file_scroll.pack(fill="x", padx=20, pady=(0, 10))

        # 3. Parameters (2-Column Grid)
        param_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        param_frame.pack(fill="x", padx=20, pady=5)
        param_frame.grid_columnconfigure(0, weight=1)
        param_frame.grid_columnconfigure(1, weight=1)
        
        # Left Column: Target Settings
        left_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(left_frame, text=t("image_resize_gui.target_resolution"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        
        # Cleaner UI: Single OptionMenu instead of messy buttons
        self.size_var = ctk.StringVar(value="1024")
        
        # Grid for cleaner look
        res_grid = ctk.CTkFrame(left_frame, fg_color="transparent")
        res_grid.pack(fill="x", pady=(0, 5))
        
        presets = ["512", "1024", "2048", "4096", "8192"]
        self.opt_size = ctk.CTkOptionMenu(res_grid, variable=self.size_var, values=presets, 
                                          command=self.update_recommendation, width=140)
        self.opt_size.pack(side="left")
                          
        self.var_square = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(left_frame, text=t("image_resize_gui.force_square"), variable=self.var_square).pack(anchor="w", pady=(10, 0))

        # Right Column: Method Settings
        right_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(right_frame, text=t("image_resize_gui.resize_method"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        
        self.mode_var = ctk.StringVar(value="Standard")
        self.rad_std = ctk.CTkRadioButton(right_frame, text=t("image_resize_gui.standard_lanczos"), variable=self.mode_var, value="Standard", command=self.update_recommendation)
        self.rad_std.pack(anchor="w", pady=2)
        
        self.rad_ai = ctk.CTkRadioButton(right_frame, text=t("image_resize_gui.ai_upscale"), variable=self.mode_var, value="AI", command=self.update_recommendation)
        self.rad_ai.pack(anchor="w", pady=2)
        
        # Info Label (Spanning or at bottom)
        self.lbl_info = ctk.CTkLabel(param_frame, text="Info...", text_color="gray", justify="left", anchor="w")
        self.lbl_info.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # 4. Footer (Centralized)
        self.progress = ctk.CTkProgressBar(self.footer_frame, height=10)
        self.progress.pack(fill="x", pady=(0, 15))
        self.progress.set(0)
        
        # Options
        opt_row = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        opt_row.pack(fill="x", pady=(0, 15))
        
        self.var_new_folder = ctk.BooleanVar(value=False)
        self.var_delete_org = ctk.BooleanVar(value=False)
        
        ctk.CTkCheckBox(opt_row, text=t("image_convert_gui.save_to_folder"), variable=self.var_new_folder).pack(side="left", padx=(0, 20))
        ctk.CTkCheckBox(opt_row, text=t("image_convert_gui.delete_original"), variable=self.var_delete_org, 
                       text_color=THEME_BTN_DANGER_HOVER).pack(side="left")
        
        # Buttons
        btn_row = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        btn_row.pack(fill="x")
        
        self.btn_cancel = ctk.CTkButton(btn_row, text=t("common.cancel"), height=45, fg_color="transparent", 
                                        border_width=1, border_color=THEME_BORDER, text_color=("gray10", "gray90"), command=self.cancel_or_close)
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_resize = ctk.CTkButton(btn_row, text=t("image_resize_gui.start_resize"), height=45, 
                                       font=ctk.CTkFont(size=14, weight="bold"), 
                                       fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER,
                                       command=self.start_resize)
        self.btn_resize.pack(side="left", fill="x", expand=True, padx=(0, 0))
        
        self.lbl_status = ctk.CTkLabel(self.footer_frame, text=t("common.ready"), text_color="gray", font=("", 11))
        self.lbl_status.pack(pady=(5, 0))

    def _set_size(self, value):
        """Set size from preset button."""
        self.size_var.set(value)
        self.update_recommendation()

    def update_recommendation(self, *args):
        try:
            target = int(self.size_var.get())
        except:
            target = 1024
            
        current = max(self.current_img_size) if self.current_img_size[0] > 0 else 1024
        
        ratio = target / current
        mode = self.mode_var.get()
        
        msg = f"Current: ~{current}px -> Target: {target}px\n"
        
        if ratio > 1.5:
            msg += f"Upscale: {ratio:.1f}x\n"
            if mode != "AI":
                msg += "Recommended: Use AI Upscale for better quality."
                self.lbl_info.configure(text_color="#ffcc00") # Warning Yellow
            else:
                msg += "AI Upscale selected."
                self.lbl_info.configure(text_color="#66cc66") # Good Green
        elif ratio < 0.8:
            msg += f"Downscale: {ratio:.1f}x"
            self.lbl_info.configure(text_color="gray")
        else:
            msg += "Size change is minor."
            self.lbl_info.configure(text_color="gray")
            
        self.lbl_info.configure(text=msg)

    def cancel_or_close(self):
        """Cancel processing if running, otherwise close window."""
        if self.btn_resize.cget("state") == "disabled":
            self.cancel_flag = True
            self.lbl_status.configure(text="Cancelling...")
        else:
            self.destroy()

    def start_resize(self):
        if not self.files:
            return
        
        # CRITICAL: Reset cancel flag before each run
        self.cancel_flag = False
        
        self.btn_resize.configure(state="disabled", text="Processing...")
        self.btn_cancel.configure(fg_color=THEME_BTN_DANGER, hover_color=THEME_BTN_DANGER_HOVER, text_color="white")
        self.lbl_status.configure(text="Starting...")
        threading.Thread(target=self.run_logic, daemon=True).start()

    def get_nearest_pot(self, val):
        return 2**round(math.log2(val))

    def run_logic(self):
        try:
            target_size = int(self.size_var.get())
        except:
            target_size = 1024
            
        mode = self.mode_var.get()
        force_square = self.var_square.get()
        
        total = len(self.files)
        success = 0
        errors = []
        
        for i, path in enumerate(self.files):
            # Check cancel flag before each file
            if self.cancel_flag:
                break
                
            self.after(0, lambda p=path.name: self.lbl_status.configure(text=f"Processing: {p}"))
            self.after(0, lambda v=(i) / total: self.progress.set(v))
            try:
                # Output setup
                save_new_folder = self.var_new_folder.get()
                delete_original = self.var_delete_org.get()
                
                out_dir = path.parent
                if save_new_folder:
                    out_dir = path.parent / "Resized"
                    out_dir.mkdir(exist_ok=True)
                
                if mode == "AI":
                    # Determine scale factor needed
                    with Image.open(path) as img:
                        w, h = img.size
                        longest = max(w, h)
                        scale_needed = target_size / longest
                        
                        if scale_needed <= 1.0:
                            scale = 1
                        elif scale_needed <= 2.5:
                            scale = 2
                        else:
                            scale = 4
                    
                    if scale > 1:
                        # Use external realesrgan-ncnn-vulkan tool
                        import tempfile
                        import subprocess
                        from manager.mgr_core.packages import PackageManager
                        
                        pkg_mgr = PackageManager()
                        esrgan_exe = pkg_mgr.get_tool_path("realesrgan-ncnn-vulkan")
                        
                        if not esrgan_exe or not esrgan_exe.exists():
                            raise Exception("Real-ESRGAN tool not found. Please install via Manager -> Preferences.")
                        
                        with tempfile.TemporaryDirectory() as temp_dir_str:
                            temp_dir = Path(temp_dir_str)
                            
                            # Real-ESRGAN outputs PNG by default
                            temp_output_file = temp_dir / f"{path.stem}.png"
                            
                            # Build command for realesrgan-ncnn-vulkan
                            cmd = [
                                str(esrgan_exe),
                                "-i", str(path),
                                "-o", str(temp_output_file),
                                "-s", str(scale),
                                "-n", "realesrgan-x4plus"
                            ]
                            
                            result = subprocess.run(cmd, capture_output=True, text=True)
                            if result.returncode != 0:
                                raise Exception(f"AI Failed: {result.stderr}")
                            
                            if not temp_output_file.exists():
                                raise Exception(f"AI output missing")
                            
                            # Move to actual destination with suffix
                            suffix = f"_ai{scale}x"
                            new_name = f"{path.stem}{suffix}.png"
                            dest_path = get_safe_path(out_dir / new_name)
                            
                            shutil.move(str(temp_output_file), str(dest_path))
                    else:
                        # Fallback copy
                        suffix = "_ai1x"
                        new_name = f"{path.stem}{suffix}{path.suffix}"
                        dest_path = get_safe_path(out_dir / new_name)
                        shutil.copy(path, dest_path)
                
                else:
                    # Standard Resize
                    with Image.open(path) as img:
                        if img.mode != "RGB": img = img.convert("RGB")
                        w, h = img.size
                        
                        if force_square:
                            # 1. Resize to fit within target_size box
                            ratio = min(target_size/w, target_size/h)
                            new_w = int(w * ratio)
                            new_h = int(h * ratio)
                            
                            # Standard Resize first
                            res = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                            
                            # 2. Create padded square canvas
                            new_img = Image.new("RGB", (target_size, target_size), (0, 0, 0))
                            
                            # 3. Paste centered
                            offset_x = (target_size - new_w) // 2
                            offset_y = (target_size - new_h) // 2
                            new_img.paste(res, (offset_x, offset_y))
                            
                            res = new_img # Replace result
                            
                        else:
                            ratio = w / h
                            if w >= h:
                                nw = target_size
                                nh = self.get_nearest_pot(nw / ratio)
                            else:
                                nh = target_size
                                nw = self.get_nearest_pot(nh * ratio)
                            
                            res = img.resize((nw, nh), Image.Resampling.LANCZOS)
                        
                        # Suffix: _{target_size}px
                        suffix = f"_{target_size}px"
                        new_name = f"{path.stem}{suffix}{path.suffix}"
                        save_path = get_safe_path(out_dir / new_name)
                        
                        res.save(save_path)
                
                success += 1
                
                # Handle Deletion
                if delete_original and path.exists():
                    try:
                        import os
                        os.remove(path)
                    except Exception as e:
                        errors.append(f"Delete failed: {path.name} ({e})")
                        
            except Exception as e:
                errors.append(f"{path.name}: {e}")
                print(e)
        
        self.after(0, lambda: self.progress.set(1.0))
        self.after(0, lambda: self.btn_resize.configure(state="normal", text="Start Resize"))
        self.after(0, lambda: self.btn_cancel.configure(fg_color="transparent", hover_color="gray25", text_color="gray"))
        
        if self.cancel_flag:
            self.after(0, lambda: self.lbl_status.configure(text="Cancelled"))
            self.after(0, lambda: messagebox.showinfo("Cancelled", "Processing was cancelled."))
        else:
            self.after(0, lambda: self.lbl_status.configure(text="Complete"))
            
            msg = f"Processed {success}/{total} images."
            if errors:
                final_msg = msg + f"\nErrors: {len(errors)}\n\n" + "\n".join(errors[:5])
                if len(errors) > 5: final_msg += "\n..."
                self.after(0, lambda m=final_msg: messagebox.showwarning("Completed with Errors", m))
            else:
                self.after(0, lambda m=msg: messagebox.showinfo("Success", m))
                self.after(0, self.destroy)

    def on_closing(self):
        self.destroy()

def resize_gui_entry(files_list):
    app = ImageResizeGUI(files_list)
    app.mainloop()


def get_all_selected_files(anchor_path: str) -> list[Path]:
    """Get all selected files via Explorer COM - INSTANT."""
    try:
        selected = get_selection_from_explorer(anchor_path)
        if selected and len(selected) > 0:
            return selected
    except:
        pass
    return [Path(anchor_path)]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        anchor = sys.argv[1]
        
        # STEP 1: Get ALL selected files instantly via Explorer COM
        all_files = get_all_selected_files(anchor)
        
        # STEP 2: Mutex - ensure only one GUI window opens
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("resize_power_of_2", anchor, timeout=0.2) is None:
            sys.exit(0)
        
        # STEP 3: Launch GUI with complete file list
        resize_gui_entry(all_files)
