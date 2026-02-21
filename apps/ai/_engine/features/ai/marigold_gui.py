import customtkinter as ctk
import os

from tkinter import messagebox
from pathlib import Path
import sys
import threading
from PIL import Image

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/ai -> src
sys.path.append(str(src_dir))

from utils.gui_lib import BaseWindow, FileListFrame, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_BTN_DANGER, THEME_BTN_DANGER_HOVER, THEME_ACCENT, THEME_DROPDOWN_BTN, THEME_DROPDOWN_FG, THEME_DROPDOWN_HOVER, ModelManagerFrame
from utils.ai_runner import run_ai_script, start_ai_script, kill_process_tree
from utils.config_persistence import load_gui_state, save_gui_state
from utils.i18n import t

class CTkToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        label = ctk.CTkLabel(self.tooltip_window, text=self.text, corner_radius=5, padx=10, pady=5, font=("Arial", 11))  # Use theme default
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class MarigoldGUI(BaseWindow):
    def __init__(self, target_path):
        super().__init__(title=t("marigold_gui.title"), width=420, height=920, icon_name="ai_pbr")
        
        if target_path is None:
            self.target_path = None
            self.files = []
            self.input_width, self.input_height = 0, 0
        else:
            self.target_path = Path(target_path)
            if not self.target_path.exists():
                messagebox.showerror(t("common.error"), t("marigold_gui.file_not_found"))
                self.destroy()
                return
            self.files = [self.target_path]
            # Get input image size
            try:
                with Image.open(self.target_path) as img:
                    self.input_width, self.input_height = img.size
            except:
                self.input_width, self.input_height = 0, 0
        
        self.current_process = None
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.var_albedo = ctk.BooleanVar(value=False)
        self.var_roughness = ctk.BooleanVar(value=False)
        self.var_metallicity = ctk.BooleanVar(value=False)
        self.var_depth = ctk.BooleanVar(value=False)
        self.var_normal = ctk.BooleanVar(value=True)
        self.var_orm = ctk.BooleanVar(value=False)
        
        # Options
        self.var_flip_y = ctk.BooleanVar(value=False)
        self.var_invert_roughness = ctk.BooleanVar(value=False)
        self.var_output_res = ctk.StringVar(value="768")
        
        # Load State
        self.gui_state = load_gui_state("marigold", {
            "steps": 10, "ensemble": 1, "res": "768", "fp16": True,
            "flip_y": False, "invert": False, "orm": False
        })
        
        self.var_processing_res = ctk.IntVar(value=768)
        self.var_steps = ctk.IntVar(value=self.gui_state.get("steps", 10))
        self.var_ensemble = ctk.IntVar(value=self.gui_state.get("ensemble", 1))
        self.var_fp16 = ctk.BooleanVar(value=self.gui_state.get("fp16", True))
        
        self.var_flip_y.set(self.gui_state.get("flip_y", False))
        self.var_orm.set(self.gui_state.get("orm", False))
        self.var_invert_roughness.set(self.gui_state.get("invert", False))
        self.var_output_res.set(self.gui_state.get("res", "768"))
        
        # Preview State
        self.preview_images = []
        self.preview_index = 0
        
        self.cancel_flag = False
        self.ai_thread = None
        
        self.create_widgets()
        
        # Initial Preview
        try:
            with Image.open(self.target_path) as img:
                self.add_preview_image("Input", img)
        except: pass

    def _has_marigold_cache(self):
        try:
            from utils import paths
            hub = paths.RESOURCES_DIR / "cache" / "hf" / "hub"
            repos = [
                "models--prs-eth--marigold-depth-v1-1",
                "models--prs-eth--marigold-normals-v1-1",
                "models--prs-eth--marigold-iid-appearance-v1-1",
            ]
            for repo in repos:
                repo_dir = hub / repo
                if repo_dir.exists():
                    snapshots = repo_dir / "snapshots"
                    if snapshots.exists() and any(snapshots.rglob("*.*")):
                        return True
            return False
        except Exception:
            return False


    def create_widgets(self):
        # 0. Title & Header
        title_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(title_frame, text=t("marigold_gui.pbr_material_generator"), font=("Arial", 18, "bold")).pack(side="left")

        # Model Manager (Integrated)
        from utils import paths
        model_root = paths.MARIGOLD_DIR
        
        self.model_mgr = ModelManagerFrame(title_frame, "Marigold", model_root, download_command=self.download_models, check_callback=self._has_marigold_cache)
        self.model_mgr.pack(side="right")
        
        # Remove old check button if present (we replaced it)
        
        # 1. Preview Carousel (New)
        self.prev_container = ctk.CTkFrame(self.main_frame, height=240, corner_radius=10)  # Use theme default
        self.prev_container.pack(fill="x", padx=10, pady=5)
        self.prev_container.pack_propagate(False)
        
        # Top Bar: Label + Arrows
        p_top = ctk.CTkFrame(self.prev_container, fg_color="transparent", height=30)
        p_top.pack(fill="x", padx=10, pady=5)
        
        self.btn_prev = ctk.CTkButton(p_top, text="◀", width=30, height=24, command=self.prev_preview, state="disabled", 
                                       fg_color="transparent", border_width=1, border_color=THEME_BORDER)
        self.btn_prev.pack(side="left")
        
        self.lbl_preview_title = ctk.CTkLabel(p_top, text=t("marigold_gui.preview"), font=("Arial", 12, "bold"))
        self.lbl_preview_title.pack(side="left", fill="x", expand=True)
        
        self.btn_next = ctk.CTkButton(p_top, text="▶", width=30, height=24, command=self.next_preview, state="disabled",
                                       fg_color="transparent", border_width=1, border_color=THEME_BORDER)
        self.btn_next.pack(side="right")

        # Image Area
        self.lbl_preview_img = ctk.CTkLabel(self.prev_container, text=t("marigold_gui.no_preview"), text_color="gray")
        self.lbl_preview_img.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Main Content
        content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        
        # === SECTION 1: Material Maps ===
        mat_frame = ctk.CTkFrame(content, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        mat_frame.pack(fill="x", pady=(2, 3))
        
        mat_header = ctk.CTkFrame(mat_frame, fg_color="transparent")
        mat_header.pack(fill="x", padx=10, pady=(6, 2))
        ctk.CTkLabel(mat_header, text=t("marigold_gui.material_maps"), font=("Arial", 11, "bold")).pack(side="left")
        ctk.CTkLabel(mat_header, text=t("marigold_gui.auto_albedo"), font=("Arial", 9), text_color="gray").pack(side="left", padx=5)
        
        mat_inner = ctk.CTkFrame(mat_frame, fg_color="transparent")
        mat_inner.pack(fill="x", padx=10, pady=(0, 6))
        
        ctk.CTkCheckBox(mat_inner, text=t("marigold_gui.albedo"), variable=self.var_albedo, width=80).pack(side="left", padx=(0, 8))
        ctk.CTkCheckBox(mat_inner, text=t("marigold_gui.roughness"), variable=self.var_roughness, width=95).pack(side="left", padx=8)
        ctk.CTkCheckBox(mat_inner, text=t("marigold_gui.metallic"), variable=self.var_metallicity, width=80).pack(side="left", padx=8)
        
        # === SECTION 2: Geometry Maps ===
        geo_frame = ctk.CTkFrame(content, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        geo_frame.pack(fill="x", pady=3)
        
        geo_header = ctk.CTkFrame(geo_frame, fg_color="transparent")
        geo_header.pack(fill="x", padx=10, pady=(6, 2))
        ctk.CTkLabel(geo_header, text=t("marigold_gui.geometry_maps"), font=("Arial", 11, "bold")).pack(side="left")
        ctk.CTkLabel(geo_header, text=t("marigold_gui.direct"), font=("Arial", 9), text_color="gray").pack(side="left", padx=5)
        
        geo_inner = ctk.CTkFrame(geo_frame, fg_color="transparent")
        geo_inner.pack(fill="x", padx=10, pady=(0, 6))
        
        ctk.CTkCheckBox(geo_inner, text=t("marigold_gui.depth"), variable=self.var_depth, width=70).pack(side="left", padx=(0, 8))
        ctk.CTkCheckBox(geo_inner, text=t("marigold_gui.normal"), variable=self.var_normal, width=80).pack(side="left", padx=8)
        
        # === SECTION 3: Quality Settings ===
        qual_frame = ctk.CTkFrame(content, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        qual_frame.pack(fill="x", pady=2)
        
        # Presets
        h_frame = ctk.CTkFrame(qual_frame, fg_color="transparent")
        h_frame.pack(anchor="center", pady=(6, 4))
        
        ctk.CTkLabel(h_frame, text=t("marigold_gui.quality_label"), font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        def create_preset_btn(name, mode, tip):
            btn = ctk.CTkButton(h_frame, text=name, width=55, height=20, fg_color=THEME_DROPDOWN_BTN, font=("Arial", 10), command=lambda: self.set_preset(mode))
            btn.pack(side="left", padx=2)
            CTkToolTip(btn, tip)
            
        create_preset_btn(t("marigold_gui.preset_speed"), "speed", "10 Steps, 512px")
        create_preset_btn(t("marigold_gui.preset_balanced"), "balanced", "20 Steps, 768px")
        create_preset_btn(t("marigold_gui.preset_quality"), "quality", "50 Steps, Native")

        # Sliders
        slider_frame = ctk.CTkFrame(qual_frame, fg_color=THEME_CARD)
        slider_frame.pack(fill="x", padx=10, pady=4)
        
        # Steps
        s_row = ctk.CTkFrame(slider_frame, fg_color="transparent")
        s_row.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(s_row, text=t("marigold_gui.steps_label"), width=45, anchor="w", font=("Arial", 10)).pack(side="left")
        ctk.CTkSlider(s_row, from_=1, to=50, number_of_steps=49, variable=self.var_steps, height=12).pack(side="left", fill="x", expand=True, padx=5)
        lbl_s_val = ctk.CTkLabel(s_row, text="10", width=25, font=("Arial", 10))
        lbl_s_val.pack(side="right")
        self.var_steps.trace("w", lambda *a: lbl_s_val.configure(text=str(int(self.var_steps.get()))))

        # Passes
        e_row = ctk.CTkFrame(slider_frame, fg_color="transparent")
        e_row.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(e_row, text=t("marigold_gui.passes_label"), width=45, anchor="w", font=("Arial", 10)).pack(side="left")
        ctk.CTkSlider(e_row, from_=1, to=10, number_of_steps=9, variable=self.var_ensemble, height=12).pack(side="left", fill="x", expand=True, padx=5)
        lbl_e_val = ctk.CTkLabel(e_row, text="1", width=25, font=("Arial", 10))
        lbl_e_val.pack(side="right")
        self.var_ensemble.trace("w", lambda *a: lbl_e_val.configure(text=str(int(self.var_ensemble.get()))))

        # === SECTION 4: Export Options ===
        export_frame = ctk.CTkFrame(content, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        export_frame.pack(fill="x", pady=(2, 2))
        
        ctk.CTkLabel(export_frame, text=t("marigold_gui.export_options"), font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(6, 4))
        
        export_inner = ctk.CTkFrame(export_frame, fg_color="transparent")
        export_inner.pack(fill="x", padx=10, pady=(0, 6))
        
        # Row 1: Output Size + FP16 + Flip + ORM
        row1 = ctk.CTkFrame(export_inner, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        
        ctk.CTkLabel(row1, text=t("marigold_gui.output_size"), font=("Arial", 10)).pack(side="left")
        cm_res = ctk.CTkComboBox(row1, variable=self.var_output_res, values=["512", "768", "1024", "2048", "Native"], width=70, height=22)
        cm_res.pack(side="left", padx=5)
        CTkToolTip(cm_res, t("marigold_gui.output_size_tip"))
        
        # Sync with processing res
        def on_res_change(*args):
            val = self.var_output_res.get()
            if val == "Native":
                self.var_processing_res.set(0)
            else:
                try:
                    self.var_processing_res.set(int(val))
                except:
                    self.var_processing_res.set(768)
        self.var_output_res.trace("w", on_res_change)
        
        ctk.CTkCheckBox(row1, text=t("marigold_gui.fp16"), variable=self.var_fp16, checkbox_width=16, checkbox_height=16, font=("Arial", 10)).pack(side="left", padx=5)
        ctk.CTkCheckBox(row1, text=t("marigold_gui.flip_y"), variable=self.var_flip_y, checkbox_width=16, checkbox_height=16, font=("Arial", 10)).pack(side="left", padx=5)
        
        row2 = ctk.CTkFrame(export_inner, fg_color="transparent")
        row2.pack(fill="x", pady=2)
        
        ctk.CTkCheckBox(row2, text=t("marigold_gui.orm_pack"), variable=self.var_orm, width=90, font=("Arial", 10)).pack(side="left")
        ctk.CTkCheckBox(row2, text=t("marigold_gui.invert_rough"), variable=self.var_invert_roughness, width=105, font=("Arial", 10)).pack(side="left", padx=10)

        # === Bottom: Buttons & Status ===
        footer = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=15, pady=(5, 15))
        
        # Progress Bar
        self.progress = ctk.CTkProgressBar(footer, height=8)
        self.progress.pack(fill="x", pady=(0, 5))
        self.progress.set(0)

        self.lbl_status = ctk.CTkLabel(footer, text=t("common.ready"), text_color="gray", height=16, font=("Arial", 11))
        self.lbl_status.pack(pady=(0, 5))
        
        btn_row = ctk.CTkFrame(footer, fg_color="transparent")
        btn_row.pack(fill="x")
        
        self.btn_run = ctk.CTkButton(btn_row, text=t("marigold_gui.generate_pbr"), height=40, 
                                     font=("Arial", 13, "bold"), 
                                     fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER,
                                     command=self.start_generation)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_cancel = ctk.CTkButton(btn_row, text=t("common.cancel"), height=40, width=70, 
                                        fg_color="transparent", border_width=1, border_color=THEME_BORDER,
                                        command=self.cancel_or_close)
        self.btn_cancel.pack(side="right")

    # --- Model Check Logic ---
    def check_models(self):
        """Run a dummy script to verify/download models."""
        self.lbl_status.configure(text=t("marigold_gui.verifying_models"), text_color=THEME_ACCENT)
        self.btn_run.configure(state="disabled")
        threading.Thread(target=self._run_model_check, daemon=True).start()
        
    def _run_model_check(self):
        try:
            # Use run_ai_script_streaming if we want real-time feedback,
            # but run_ai_script also returns output. For the "Checking..." feedback, 
            # we can't easily get real-time lines with run_ai_script (it waits).
            # But the AI environment is tricky. Let's use run_ai_script and just wait.
            
            # OR better: use run_ai_script_streaming logic manually or simpler:
            # Just call run_ai_script. It will block this thread (which is fine, it's a daemon thread).
            
            self.main_frame.after(0, lambda: self.lbl_status.configure(text=t("ai_common.verifying_models")))
            
            success, output = run_ai_script("check_marigold_deps.py")
            
            if success:
                self.main_frame.after(0, lambda: messagebox.showinfo(t("marigold_gui.models_title"), t("marigold_gui.models_ready")))
                self.main_frame.after(0, lambda: self.lbl_status.configure(text=t("marigold_gui.models_ready"), text_color="gray"))
            else:
                self.main_frame.after(0, lambda: messagebox.showerror(t("common.error"), f"{t('marigold_gui.model_check_failed')}:\n{output}"))
                self.main_frame.after(0, lambda: self.lbl_status.configure(text=t("marigold_gui.model_check_failed"), text_color="red"))
                 
        except Exception as e:
            print(e)
            self.main_frame.after(0, lambda: self.lbl_status.configure(text=t("common.error"), text_color="red"))
        
        self.main_frame.after(0, lambda: self.btn_run.configure(state="normal"))


    # --- Preview Logic ---
    def add_preview_image(self, label, pil_img):
        # Resize for preview
        try:
            ratio = pil_img.height / pil_img.width
            target_h = 240
            target_w = int(target_h / ratio)
            
            # Limit width to fit container (approx 380px for 420px window)
            if target_w > 380:
                target_w = 380
                target_h = int(target_w * ratio)
            
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
            
            self.preview_images.append({"label": label, "image": ctk_img})
            
            # Switch to new image
            self.preview_index = len(self.preview_images) - 1
            self.update_preview_display()
        except Exception as e:
            print(f"Preview Error: {e}")

    def update_preview_display(self):
        if not self.preview_images:
            self.lbl_preview_title.configure(text=t("marigold_gui.no_preview"))
            self.lbl_preview_img.configure(image=None, text=t("marigold_gui.no_preview"))
            self.btn_prev.configure(state="disabled")
            self.btn_next.configure(state="disabled")
            return
            
        data = self.preview_images[self.preview_index]
        self.lbl_preview_title.configure(text=f"{data['label']} ({self.preview_index+1}/{len(self.preview_images)})")
        self.lbl_preview_img.configure(image=data['image'], text="")
        
        self.btn_prev.configure(state="normal" if len(self.preview_images) > 1 else "disabled")
        self.btn_next.configure(state="normal" if len(self.preview_images) > 1 else "disabled")

    def prev_preview(self):
        self.preview_index = (self.preview_index - 1) % len(self.preview_images)
        self.update_preview_display()

    def next_preview(self):
        self.preview_index = (self.preview_index + 1) % len(self.preview_images)
        self.update_preview_display()

    def set_preset(self, mode):
        if mode == "speed":
            self.var_steps.set(10)
            self.var_ensemble.set(1)
            self.var_output_res.set("512")
        elif mode == "balanced":
            self.var_steps.set(20)
            self.var_ensemble.set(3)
            self.var_output_res.set("768")
        elif mode == "quality":
            self.var_steps.set(50)
            self.var_ensemble.set(5)
            self.var_output_res.set("Native")
            
    def cancel_or_close(self):
        """Cancel processing if running, otherwise close window."""
        if self.btn_run.cget("state") == "disabled":
            self.cancel_flag = True
            self.lbl_status.configure(text=t("common.processing"))
            if self.current_process:
                try:
                    kill_process_tree(self.current_process)
                except Exception:
                    pass
                self.current_process = None
        else:
            self.destroy()

    def start_generation(self):
        has_geometry = self.var_depth.get() or self.var_normal.get()
        has_material = self.var_albedo.get() or self.var_roughness.get() or self.var_metallicity.get() or self.var_orm.get()
        
        if not has_geometry and not has_material:
            messagebox.showwarning(t("common.warning"), t("marigold_gui.select_map_warning"))
            return
        
        # Auto-enable Albedo if material maps are selected
        if has_material and not self.var_albedo.get():
            self.var_albedo.set(True)
        
        # CRITICAL: Reset cancel flag before each run
        self.cancel_flag = False
            
        self.btn_run.configure(state="disabled", text=t("common.processing"))
        self.btn_cancel.configure(fg_color=THEME_BTN_DANGER, hover_color=THEME_BTN_DANGER_HOVER, text_color="white")
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        
        self.ai_thread = threading.Thread(target=self.run_process, daemon=True)
        self.ai_thread.start()
        
    def run_process(self):
        try:
            # Check cancel before starting
            if self.cancel_flag:
                self.main_frame.after(0, self.finish_cancelled)
                return
                
            self.update_status(t("ai_common.initializing"))
            
            args = [str(self.target_path)]
            
            if self.var_depth.get(): args.append("--depth")
            if self.var_normal.get(): args.append("--normal")
            if self.var_albedo.get(): args.append("--albedo")
            if self.var_roughness.get(): args.append("--roughness")
            if self.var_metallicity.get(): args.append("--metallicity")
            if self.var_orm.get(): args.append("--orm")
            
            if self.var_flip_y.get(): args.append("--flip_y")
            if self.var_invert_roughness.get(): args.append("--invert_roughness")
            
            args.extend(["--res", str(self.var_processing_res.get())])
            args.extend(["--ensemble", str(int(self.var_ensemble.get()))])
            args.extend(["--steps", str(int(self.var_steps.get()))])
            args.extend(["--model_version", "v1-1"])  # Hardcoded to latest
            
            if self.var_fp16.get():
                args.append("--fp16")
            
            # Check cancel before AI call
            if self.cancel_flag:
                self.main_frame.after(0, self.finish_cancelled)
                return
        
            # We use the new start_ai_script to track the process
            self.current_process = start_ai_script("marigold_inference.py", *args)
            stdout, stderr = self.current_process.communicate()
            success = (self.current_process.returncode == 0)
            output = stdout if success else (stderr if stderr else stdout)
            self.current_process = None
            
            # Check cancel after AI call
            if self.cancel_flag:
                self.main_frame.after(0, self.finish_cancelled)
                return
            
            if success:
                self.main_frame.after(0, lambda: self.finish_success(output))
            else:
                self.main_frame.after(0, lambda: self.finish_error(output))
                
        except Exception as e:
            if not self.cancel_flag:
                self.main_frame.after(0, lambda: self.finish_error(str(e)))

    def update_status(self, text):
        self.lbl_status.configure(text=text)

    def clean_error_message(self, text):
        """Remove tqdm bars and other noise from error message."""
        if not text: return ""
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            # Filter tqdm progress bars (e.g., "100%|#####|")
            if '%' in line and '|' in line and (']' in line or 'it/s' in line):
                continue
            # Filter warnings
            if "UserWarning" in line and "torch" in line:
                continue
            clean_lines.append(line)
        return '\n'.join(clean_lines).strip()


    def finish_cancelled(self):
        """Handle cancelled state."""
        self.progress.stop()
        self.progress.set(0)
        self.lbl_status.configure(text=t("common.cancelled"))
        self.btn_run.configure(state="normal", text=t("marigold_gui.generate_pbr"))
        self.btn_cancel.configure(fg_color="transparent", hover_color="gray25", text_color="gray")
        messagebox.showinfo(t("common.cancelled"), t("common.cancelled"))

    def finish_success(self, output):
        self.progress.stop()
        self.progress.set(1)
        self.lbl_status.configure(text=t("common.complete"))
        self.btn_run.configure(state="normal", text=t("marigold_gui.generate_pbr"))
        self.btn_cancel.configure(fg_color="transparent", hover_color="gray25", text_color="gray")
        self.save_settings() # Save on success
        
        # Load generated images into Preview
        base = self.target_path.stem
        parent = self.target_path.parent
        
        generated_map = {
            "Albedo": f"{base}_albedo.png",
            "Roughness": f"{base}_roughness.png",
            "Metallic": f"{base}_metallicity.png",
            "Depth": f"{base}_depth.png",
            "Normal": f"{base}_normal.png",
            "ORM": f"{base}_orm.png"
        }
        
        found_any = False
        self.preview_images = [] # Reset preview
        
        # Always keep input
        try:
             with Image.open(self.target_path) as img:
                self.add_preview_image("Input", img)
        except: pass
        
        for label, fname in generated_map.items():
            fpath = parent / fname
            if fpath.exists():
                try:
                    with Image.open(fpath) as img:
                        self.add_preview_image(label, img.copy()) # Copy to memory
                    found_any = True
                except: pass
        
        if found_any:
            # message box optional, or just status update
            self.lbl_status.configure(text=t("common.complete"))
        else:
            # Fallback if nothing found (maybe stored elsewhere?)
            if messagebox.askyesno(t("common.success"), f"{t('marigold_gui.maps_generated')}\n\n{t('marigold_gui.open_folder_prompt')}"):
                try:
                    os.startfile(parent)
                except Exception as e:
                    messagebox.showerror(t("common.error"), t("marigold_gui.open_folder_failed").format(error=e))
        
    def finish_error(self, error_msg):
        self.progress.stop()
        self.progress.set(0)
        self.lbl_status.configure(text=t("common.error"))
        self.btn_run.configure(state="normal", text=t("marigold_gui.generate_pbr"))
        self.btn_cancel.configure(fg_color="transparent", hover_color="gray25", text_color="gray")
        
        clean_msg = self.clean_error_message(error_msg)
        if not clean_msg: clean_msg = t("ai_common.unknown_error")
        
        messagebox.showerror(t("common.error"), f"{t('marigold_gui.generation_failed')}\n{clean_msg}")

    def save_settings(self):
        try:
            state = {
                "steps": self.var_steps.get(),
                "ensemble": self.var_ensemble.get(),
                "res": self.var_output_res.get(),
                "fp16": self.var_fp16.get(),
                "flip_y": self.var_flip_y.get(),
                "invert": self.var_invert_roughness.get(),
                "orm": self.var_orm.get(),
                # Map toggles are per-image, but quality settings are worth remembering
            }
            save_gui_state("marigold", state)
        except: pass

    # --- Model Handling ---
    
    def download_models(self):
        """Standardized download trigger."""
        self.check_models()
        # After check (which might trigger download in legacy logic), update UI
        self.after(1000, lambda: self.model_mgr.check_status())

    def on_closing(self):
        """Clean up process and close."""
        if self.current_process:
            kill_process_tree(self.current_process)
        self.destroy()

def run_marigold_gui(target_path):
    app = MarigoldGUI(target_path)
    app.mainloop()

if __name__ == "__main__":
    if "--demo" in sys.argv or "--test-screenshot" in sys.argv:
        run_marigold_gui(None)
    elif len(sys.argv) > 1:
        from utils.batch_runner import collect_batch_context
        
        batch_files = collect_batch_context("marigold_pbr", sys.argv[1], timeout=0.3)
        
        if batch_files is None:
            sys.exit(0)
        
        run_marigold_gui(str(batch_files[0]))
    else:
        # Default or debug
        pass
