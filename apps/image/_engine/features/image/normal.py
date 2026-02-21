"""
Normal Map and Simple PBR Tools.
Provides utilities for normal map manipulation and legacy PBR generation.
"""
import sys
from pathlib import Path
from tkinter import messagebox

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/image -> src
sys.path.append(str(src_dir))

from core.logger import setup_logger
from utils.explorer import get_selection_from_explorer
from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_TEXT_MAIN, THEME_TEXT_DIM
import customtkinter as ctk
from PIL import Image

logger = setup_logger("normal_tools")


def flip_normal_green(target_path, selection=None):
    """
    Flip Green channel of normal map (DirectX <-> OpenGL conversion).
    No GUI - instant execution with notification.
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        messagebox.showerror("Error", "Required libraries (Pillow, NumPy) are missing. Please run setup.")
        return
    
    try:
        # Get selection
        if selection is None:
            selection = get_selection_from_explorer(target_path)
        
        if not selection:
            selection = [Path(target_path)]
        
        count = 0
        for path in selection:
            path = Path(path)
            if not path.exists():
                continue
                
            logger.info(f"Flipping green channel: {path}")
            
            img = Image.open(path)
            
            # Ensure RGB/RGBA
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGBA' if 'A' in img.mode else 'RGB')
            
            arr = np.array(img)
            
            # Flip Green channel (index 1)
            arr[:, :, 1] = 255 - arr[:, :, 1]
            
            result = Image.fromarray(arr)
            out_path = path.parent / f"{path.stem}_flipped{path.suffix}"
            result.save(out_path)
            
            logger.info(f"Saved: {out_path}")
            count += 1
        
        messagebox.showinfo("Complete", f"Flipped {count} normal map(s).\nOutput: *_flipped.*")
        
    except Exception as e:
        logger.error(f"Normal flip failed: {e}", exc_info=True)
        messagebox.showerror("Error", f"Failed to flip normal: {e}")


class NormalStrengthGUI(BaseWindow):
    def __init__(self, target_path, selection=None):
        super().__init__(title="ContextUp Normal & Roughness Gen", width=500, height=750, icon_name="simple_pbr")
        self.main_frame.pack_configure(padx=10, pady=10)
        
        # Handle selection
        if selection:
            self.files = selection
        else:
            self.files = get_selection_from_explorer(target_path) or [Path(target_path)]
            
        # Filter existing
        self.files = [Path(p) for p in self.files if Path(p).exists()]
        
        self.create_widgets()
        
    def create_widgets(self):
        # 0. Header
        header = self.add_header("Normal & Roughness Generator", font_size=18)
        header.pack_configure(pady=(5, 15))
        
        # 1. Preview Area (Enlarged)
        self.preview_frame = ctk.CTkFrame(self.main_frame, height=380, fg_color=THEME_BORDER)
        self.preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.preview_frame.pack_propagate(False)
        
        self.lbl_preview = ctk.CTkLabel(self.preview_frame, text="Loading Preview...")
        self.lbl_preview.place(relx=0.5, rely=0.5, anchor="center")
        
        # Load preview image (first file)
        self.preview_img_orig = None
        if self.files:
            try:
                img = Image.open(self.files[0]).convert('RGB')
                aspect = img.height / img.width
                w = 420
                h = int(w * aspect)
                if h > 350:
                    h = 350
                    w = int(h / aspect)
                self.preview_img_orig = img.resize((w, h), Image.Resampling.LANCZOS)
            except Exception as e:
                self.lbl_preview.configure(text=f"Preview Fail: {e}")

        # 2. Preview Mode Selector
        self.tabview = ctk.CTkTabview(self.main_frame, height=50, fg_color=THEME_CARD,
                                      segmented_button_selected_color=THEME_BTN_PRIMARY,
                                      segmented_button_selected_hover_color=THEME_BTN_HOVER,
                                      segmented_button_unselected_color=THEME_DROPDOWN_FG,
                                      segmented_button_unselected_hover_color=THEME_DROPDOWN_BTN,
                                      border_width=1, border_color=THEME_BORDER,
                                      text_color=THEME_TEXT_MAIN)
        self.tabview.pack(fill="x", padx=5, pady=(5, 0))
        self.tabview.add("Original")
        self.tabview.add("Normal")
        self.tabview.add("Roughness")
        self.tabview.set("Normal")
        self.tabview.configure(command=self.update_preview)

        # 3. Dynamic Control Panel
        self.ctrl_panel = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.ctrl_panel.pack(fill="x", padx=10, pady=10)

        # Normal Controls
        self.frame_n_ctrl = ctk.CTkFrame(self.ctrl_panel, fg_color=THEME_CARD)
        ctk.CTkLabel(self.frame_n_ctrl, text="Strength:", font=("", 11, "bold")).pack(side="left", padx=(10, 5))
        self.slider_normal = ctk.CTkSlider(self.frame_n_ctrl, from_=0.1, to=5.0, height=16, command=self.update_preview)
        self.slider_normal.pack(side="left", fill="x", expand=True, padx=5)
        self.slider_normal.set(1.0)
        self.lbl_norm_val = ctk.CTkLabel(self.frame_n_ctrl, text="1.0", width=30, font=("", 10))
        self.lbl_norm_val.pack(side="left")
        self.check_n_flip = ctk.CTkCheckBox(self.frame_n_ctrl, text="Flip G", font=("", 10), width=60, command=self.update_preview)
        self.check_n_flip.pack(side="left", padx=5)

        # Roughness Controls
        self.frame_r_ctrl = ctk.CTkFrame(self.ctrl_panel, fg_color=THEME_CARD)
        ctk.CTkLabel(self.frame_r_ctrl, text="Contrast:", font=("", 11, "bold")).pack(side="left", padx=(10, 5))
        self.slider_rough = ctk.CTkSlider(self.frame_r_ctrl, from_=0.1, to=3.0, height=16, command=self.update_preview)
        self.slider_rough.pack(side="left", fill="x", expand=True, padx=5)
        self.slider_rough.set(1.0)
        self.lbl_rough_val = ctk.CTkLabel(self.frame_r_ctrl, text="1.0", width=30, font=("", 10))
        self.lbl_rough_val.pack(side="left")
        self.check_r_invert = ctk.CTkCheckBox(self.frame_r_ctrl, text="Invert", font=("", 10), width=60, command=self.update_preview)
        self.check_r_invert.pack(side="left", padx=5)

        # 4. Info & Action
        self.lbl_info = ctk.CTkLabel(self.main_frame, text="Preview showing Normal", 
                                     text_color=THEME_TEXT_DIM, font=("", 10))
        self.lbl_info.pack(pady=(0, 5))
        
        self.btn_run = ctk.CTkButton(self.main_frame, text="Save Normal Map(s)", height=35, 
                                     fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER,
                                     font=("", 13, "bold"), command=self.start_gen)
        self.btn_run.pack(fill="x", padx=20, pady=(5, 15))
        
        if self.preview_img_orig:
            self.update_preview()

    def update_preview(self, _=None):
        # Update Labels
        n_str = self.slider_normal.get()
        r_con = self.slider_rough.get()
        self.lbl_norm_val.configure(text=f"{n_str:.1f}")
        self.lbl_rough_val.configure(text=f"{r_con:.1f}")
        
        # Generate Preview
        if self.preview_img_orig:
            current_tab = self.tabview.get()
            self.lbl_info.configure(text=f"Preview showing {current_tab}")
            
            # Contextual UI Focus
            if current_tab == "Original":
                self.frame_n_ctrl.pack_forget()
                self.frame_r_ctrl.pack_forget()
                self.btn_run.configure(text="Select Normal/Roughness to Save", state="disabled")
                display_img = self.preview_img_orig
            elif current_tab == "Normal":
                self.frame_r_ctrl.pack_forget()
                self.frame_n_ctrl.pack(fill="x", pady=5)
                self.btn_run.configure(text="Save Normal Map(s)", state="normal")
                
                params = {'n_str': n_str, 'n_flip': self.check_n_flip.get(), 'r_con': r_con, 'r_invert': self.check_r_invert.get()}
                norm, _ = self.generate_maps(self.preview_img_orig, params)
                display_img = norm
            else: # Roughness
                self.frame_n_ctrl.pack_forget()
                self.frame_r_ctrl.pack(fill="x", pady=5)
                self.btn_run.configure(text="Save Roughness Map(s)", state="normal")
                
                params = {'n_str': n_str, 'n_flip': self.check_n_flip.get(), 'r_con': r_con, 'r_invert': self.check_r_invert.get()}
                _, rough = self.generate_maps(self.preview_img_orig, params)
                display_img = rough
            
            ctk_img = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=display_img.size)
            self.lbl_preview.configure(image=ctk_img, text="")

    def generate_maps(self, img_pil, params):
        """Core logic: Returns (normal_pil, roughness_pil)"""
        import numpy as np
        from PIL import ImageEnhance
        
        n_str = params.get('n_str', 1.0)
        n_flip = params.get('n_flip', False)
        r_con = params.get('r_con', 1.0)
        r_invert = params.get('r_invert', False)

        # Convert to arrays
        if img_pil.mode != 'L':
            gray = img_pil.convert('L')
        else:
            gray = img_pil
            
        # === Roughness ===
        if r_con != 1.0:
            enhancer = ImageEnhance.Contrast(gray)
            img_con = enhancer.enhance(r_con)
        else:
            img_con = gray
            
        arr_r = np.array(img_con, dtype=np.float32) / 255.0
        
        # Invert logic: default depth (1.0 - Gray) or inverted (Gray)
        rough_arr_norm = arr_r if r_invert else (1.0 - arr_r)
        rough_arr = rough_arr_norm * 255
        rough_img = Image.fromarray(rough_arr.astype(np.uint8))
        
        # === Normal ===
        arr_n = np.array(gray, dtype=np.float32) / 255.0
        
        try:
            from scipy.ndimage import sobel
            dx = sobel(arr_n, axis=1)
            dy = sobel(arr_n, axis=0)
        except ImportError:
            dx = np.gradient(arr_n, axis=1)
            dy = np.gradient(arr_n, axis=0)
            
        dx *= n_str
        dy *= n_str
        
        if n_flip:
            dy = -dy # Flip Green (Y-axis)
            
        dz = np.ones_like(arr_n)
        length = np.sqrt(dx*dx + dy*dy + dz*dz)
        np.place(length, length==0, 1)
        
        nx = (dx / length + 1) * 0.5 * 255
        ny = (dy / length + 1) * 0.5 * 255
        nz = (dz / length + 1) * 0.5 * 255
        
        norm_arr = np.stack([nx, ny, nz], axis=-1).astype(np.uint8)
        norm_img = Image.fromarray(norm_arr)
        
        return norm_img, rough_img

    def start_gen(self):
        try:
            import numpy
            from PIL import Image
        except ImportError:
            messagebox.showerror("Error", "Required libraries (Pillow, NumPy) are missing.")
            return

        self.btn_run.configure(state="disabled", text="Saving...")
        import threading
        threading.Thread(target=self.run_process, daemon=True).start()
        
    def run_process(self):
        count = 0
        errors = []
        current_tab = self.tabview.get()
        
        params = {
            'n_str': self.slider_normal.get(),
            'n_flip': self.check_n_flip.get(),
            'r_con': self.slider_rough.get(),
            'r_invert': self.check_r_invert.get()
        }
        
        for path in self.files:
            try:
                img = Image.open(path)
                norm, rough = self.generate_maps(img, params)
                
                if current_tab == "Normal":
                    norm.save(path.parent / f"{path.stem}_normal.png")
                elif current_tab == "Roughness":
                    rough.save(path.parent / f"{path.stem}_roughness.png")
                
                count += 1
            except Exception as e:
                errors.append(f"{path.name}: {e}")
                
        self.main_frame.after(0, lambda: self._finish(count, errors, current_tab))

    def _finish(self, count, errors, tab_name):
        self.btn_run.configure(state="normal", text=f"Save {tab_name} Map(s)")
        if errors:
            messagebox.showwarning("Finished with Errors", "\n".join(errors))
        else:
            messagebox.showinfo("Success", f"Saved {tab_name} maps for {count} files.")
            # Window stays open for continuous work

def generate_simple_normal_roughness(target_path, selection=None):
    """Launch GUI for generation."""
    try:
        from utils.gui_lib import BaseWindow
        import customtkinter as ctk
        
        app = NormalStrengthGUI(target_path, selection)
        app.mainloop()
        
    except Exception as e:
        # Fallback if GUI fails? Or just show error
        messagebox.showerror("Error", f"Failed to launch GUI: {e}")


if __name__ == "__main__":
    # Test entry point
    if len(sys.argv) > 2:
        action = sys.argv[1]
        path = sys.argv[2]

        from utils.batch_runner import collect_batch_context
        batch_id = "normal_flip_green" if action == "flip" else "simple_normal_roughness"
        if collect_batch_context(batch_id, path, timeout=0.2) is None:
            sys.exit(0)
        
        if action == "flip":
            flip_normal_green(path)
        elif action == "simple":
            generate_simple_normal_roughness(path)
    else:
        print("Usage: python normal_tools.py <flip|simple> <path>")
