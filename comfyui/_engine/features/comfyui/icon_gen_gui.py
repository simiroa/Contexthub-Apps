
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import sys
import io
import random
import time
from pathlib import Path
from PIL import Image

# Add src to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from features.comfyui.premium import PremiumComfyWindow, Colors, Fonts, GlassFrame, PremiumLabel, ActionButton, PremiumScrollableFrame
try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

import json
from datetime import datetime

class IconGenGUI(PremiumComfyWindow):
    def __init__(self):
        super().__init__(title="AI Icon Generator", width=1050, height=750)
        
        # Internal State
        self.is_processing = False
        self.generated_image = None
        self.history = [] 
        self.templates = self._load_templates()
        self.view_mode = "Single"
        
        self.setup_content()

    def _load_templates(self):
        try:
            path = Path(src_dir).parent / "userdata" / "icon_templates.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load templates: {e}")
        return {}

    def _save_templates(self):
        try:
            path = Path(src_dir).parent / "userdata" / "icon_templates.json"
            path.parent.mkdir(exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.templates, f, indent=4)
        except Exception as e:
            print(f"Failed to save templates: {e}")

    def setup_content(self):
        # Split Layout: Left Control Panel (Fixed Width), Right Viewport (Flexible)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=0) # Left
        self.content_area.grid_columnconfigure(1, weight=1) # Right
        
        # --- Left Panel ---
        self.left_panel = GlassFrame(self.content_area, width=380)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(24, 12), pady=(0, 24))
        self.left_panel.grid_propagate(False)
        
        self._build_controls()
        
        # --- Right Panel ---
        self.right_panel = GlassFrame(self.content_area)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 24), pady=(0, 24))
        
        self._build_viewport()

    def _build_controls(self):
        # Padding
        pad_x = 20
        
        # 1. Mode/Tabs
        self.tab = ctk.CTkTabview(self.left_panel, height=250, segmented_button_fg_color=Colors.BG_MAIN, segmented_button_selected_color=Colors.ACCENT_SECONDARY)
        self.tab.pack(fill="x", padx=pad_x, pady=10)
        self.tab.add("Design")
        self.tab.add("Batch")
        
        # Design Tab
        t_design = self.tab.tab("Design")
        
        PremiumLabel(t_design, text="Prompt", style="small").pack(anchor="w", pady=(5,0))
        self.txt_prompt = ctk.CTkTextbox(t_design, height=100, font=Fonts.BODY, fg_color=Colors.BG_MAIN)
        self.txt_prompt.pack(fill="x", pady=(5, 10))
        
        # Templates
        tmpl_frame = ctk.CTkFrame(t_design, fg_color="transparent")
        tmpl_frame.pack(fill="x")
        
        self.combo_tmpl = ctk.CTkComboBox(tmpl_frame, values=["Load Template..."] + list(self.templates.keys()), 
                                        command=self._on_template_select, width=160)
        self.combo_tmpl.pack(side="left", fill="x", expand=True, padx=(0,5))
        
        ActionButton(tmpl_frame, text="Save", width=60, height=32, variant="secondary", command=self._save_current_as_template).pack(side="right")
        
        # Batch Tab
        t_batch = self.tab.tab("Batch")
        
        # Batch Styles (Prefix/Suffix)
        style_frame = ctk.CTkFrame(t_batch, fg_color="transparent")
        style_frame.pack(fill="x", pady=(5, 5))
        
        PremiumLabel(style_frame, text="Global Prefix", style="small").grid(row=0, column=0, sticky="w", padx=2)
        self.entry_prefix = ctk.CTkEntry(style_frame, placeholder_text="e.g. icon of", fg_color=Colors.BG_MAIN, border_color=Colors.BORDER_LIGHT)
        self.entry_prefix.grid(row=1, column=0, sticky="ew", padx=2, pady=(0, 5))
        
        PremiumLabel(style_frame, text="Global Suffix", style="small").grid(row=0, column=1, sticky="w", padx=2)
        self.entry_suffix = ctk.CTkEntry(style_frame, placeholder_text="e.g. minimal, 3d render", fg_color=Colors.BG_MAIN, border_color=Colors.BORDER_LIGHT)
        self.entry_suffix.grid(row=1, column=1, sticky="ew", padx=2, pady=(0, 5))
        
        style_frame.grid_columnconfigure(0, weight=1)
        style_frame.grid_columnconfigure(1, weight=1)

        PremiumLabel(t_batch, text="One subject per line", style="small").pack(anchor="w")
        self.txt_batch = ctk.CTkTextbox(t_batch, height=140, fg_color=Colors.BG_MAIN)
        self.txt_batch.pack(fill="both", expand=True, pady=5)

        # 2. Options
        opt_group = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        opt_group.pack(fill="x", padx=pad_x, pady=10)
        
        # Seed
        row1 = ctk.CTkFrame(opt_group, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        PremiumLabel(row1, text="Seed", style="body").pack(side="left")
        
        self.entry_seed = ctk.CTkEntry(row1, width=120, placeholder_text="Random", fg_color=Colors.BG_MAIN, border_color=Colors.BORDER_LIGHT)
        self.entry_seed.pack(side="right")
        ctk.CTkButton(row1, text="🎲", width=30, fg_color=Colors.BG_CARD_HOVER, command=lambda: self.entry_seed.delete(0, 'end')).pack(side="right", padx=5)

        # RemBG
        self.var_rembg = ctk.BooleanVar(value=REMBG_AVAILABLE)
        self.chk_rembg = ctk.CTkSwitch(opt_group, text="Remove Background", variable=self.var_rembg, 
                                     progress_color=Colors.ACCENT_PURPLE,
                                     state="normal" if REMBG_AVAILABLE else "disabled")
        self.chk_rembg.pack(anchor="w", pady=10)
        
        # 3. Action
        self.btn_generate = ActionButton(self.left_panel, text="Generate Icon", variant="primary", command=self.start_generation)
        self.btn_generate.pack(side="bottom", fill="x", padx=pad_x, pady=30)

    def _build_viewport(self):
        self.right_panel.grid_rowconfigure(0, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)
        
        # Main Preview Area
        self.preview_container = ctk.CTkFrame(self.right_panel, fg_color="transparent") # Transparent to show parent
        self.preview_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        self.preview_label = ctk.CTkLabel(self.preview_container, text="Ready to create.", text_color=Colors.TEXT_TERTIARY, font=Fonts.HEADER)
        self.preview_label.pack(expand=True, fill="both")
        
        # Gallery / Actions Strip
        self.strip = ctk.CTkFrame(self.right_panel, height=80, fg_color=Colors.BG_MAIN, corner_radius=0)
        self.strip.grid(row=1, column=0, sticky="ew")
        
        # Action Buttons (Left)
        act_frame = ctk.CTkFrame(self.strip, fg_color="transparent")
        act_frame.pack(side="left", padx=10, fill="y")
        
        self.btn_save_ico = ActionButton(act_frame, text="ICO", width=60, height=36, variant="secondary", state="disabled", command=lambda: self.save("ico"))
        self.btn_save_ico.pack(side="left", padx=2)
        
        self.btn_save_png = ActionButton(act_frame, text="PNG", width=60, height=36, variant="secondary", state="disabled", command=lambda: self.save("png"))
        self.btn_save_png.pack(side="left", padx=2)
        
        # Scrollable Gallery (Right)
        self.gallery_frame = PremiumScrollableFrame(self.strip, orientation="horizontal", height=60, fg_color="transparent")
        self.gallery_frame.pack(side="right", fill="x", expand=True, padx=5, pady=5)

    # --- Logic ---

    def _on_template_select(self, value):
        if value in self.templates:
            self.txt_prompt.delete("1.0", "end")
            self.txt_prompt.insert("end", self.templates[value])

    def _save_current_as_template(self):
        prompt = self.txt_prompt.get("1.0", "end").strip()
        if not prompt: return
        dialog = ctk.CTkInputDialog(text="Template Name:", title="Save Template")
        name = dialog.get_input()
        if name:
            self.templates[name] = prompt
            self._save_templates()
            self.combo_tmpl.configure(values=["Load Template..."] + list(self.templates.keys()))

    def start_generation(self):
        if self.is_processing: return
        
        mode = self.tab.get()
        prompts = []
        if mode == "Design":
            p = self.txt_prompt.get("1.0", "end").strip()
            if p: prompts.append(p)
        else:
            raw = self.txt_batch.get("1.0", "end").strip()
            if raw: 
                # Apply Prefix/Suffix
                prefix = self.entry_prefix.get().strip()
                suffix = self.entry_suffix.get().strip()
                
                lines = [line.strip() for line in raw.split('\n') if line.strip()]
                for line in lines:
                    final = line
                    if prefix: final = f"{prefix} {final}"
                    if suffix: final = f"{final}, {suffix}"
                    prompts.append(final)
            
        if not prompts:
            messagebox.showwarning("Warning", "Prompt is empty.")
            return

        seed_raw = self.entry_seed.get().strip()
        base_seed = int(seed_raw) if seed_raw.isdigit() else None

        self.is_processing = True
        self.btn_generate.configure(state="disabled", text="Processing...")
        self.preview_label.configure(text="Generating...", image=None)
        
        threading.Thread(target=self._run_batch, args=(prompts, base_seed), daemon=True).start()

    def _run_batch(self, prompts, base_seed):
        for i, prompt in enumerate(prompts):
            if not self.winfo_exists(): break
            
            # Update status badge if available
            self.after(0, lambda: self.status_badge.set_status(f"Generating {i+1}/{len(prompts)}", "active"))
            
            seed = base_seed + i if base_seed is not None else random.randint(1, 2**32-1)
            
            try:
                self._run_single_generation_sync(prompt, seed)
            except Exception as e:
                print(f"Error: {e}")
                
        self.after(0, self._on_batch_complete)
        
    def _create_workflow_json(self, prompt, seed):
        # Same workflow logic as before
        return {
            "3": { "class_type": "KSampler", "inputs": { "seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler_ancestral", "scheduler": "simple", "denoise": 1, "model": ["10", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0] } },
            "5": { "class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1} },
            "6": { "class_type": "CLIPTextEncode", "inputs": { "text": f"{prompt}, 3d render, soft glassmorphism, neon glow, black background, minimal, 8k, best quality", "clip": ["12", 0] } },
            "7": { "class_type": "CLIPTextEncode", "inputs": { "text": "text, watermark, low quality, cropped, photo", "clip": ["12", 0] } },
            "8": { "class_type": "VAEDecode", "inputs": { "samples": ["3", 0], "vae": ["11", 0] } },
            "9": { "class_type": "SaveImage", "inputs": { "filename_prefix": "icon_gen", "images": ["8", 0] } },
            "10": { "class_type": "UNETLoader", "inputs": { "unet_name": "z-image-turbo-fp8-e5m2.safetensors", "weight_dtype": "default" } },
            "11": { "class_type": "VAELoader", "inputs": { "vae_name": "ae.safetensors" } },
            "12": { "class_type": "CLIPLoader", "inputs": { "clip_name": "qwen_3_4b.safetensors", "type": "stable_diffusion" } }
        }

    def _run_single_generation_sync(self, prompt, seed):
        workflow = self._create_workflow_json(prompt, seed)
        outputs = self.client.generate_image(workflow, output_node_id=9)
        
        if outputs:
            img_data = outputs[0] # assuming bytes
            img = Image.open(io.BytesIO(img_data))
            
            if self.var_rembg.get() and REMBG_AVAILABLE:
                try:
                    img = remove(img)
                    bbox = img.getbbox()
                    if bbox: img = img.crop(bbox)
                except: pass
            
            # Add padding/resize
            new_img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            img.thumbnail((256, 256), Image.Resampling.LANCZOS)
            x = (256 - img.width) // 2
            y = (256 - img.height) // 2
            new_img.paste(img, (x, y), img)
            
            self.generated_image = new_img
            # Store prompt for filename generation
            self.current_prompt = prompt
            self.history.append({"image": new_img, "prompt": prompt, "seed": seed})
            
            self.after(0, lambda: self._add_to_gallery(new_img))
            self.after(0, self._show_result)

    def _on_batch_complete(self):
        self.is_processing = False
        self.btn_generate.configure(state="normal", text="Generate Icon")
        self.status_badge.set_status("Ready", "success")

    def _show_result(self, image=None):
        if not image: image = self.generated_image
        if not image: return
        
        self.generated_image = image 
        # Update current prompt from history if this image is from history
        # (This usually requires passing prompt too, but for now we rely on batch linear or last)
        
        self.btn_save_ico.configure(state="normal")
        self.btn_save_png.configure(state="normal")
        
        # Display logic (resize to fit preview container)
        w = self.preview_container.winfo_width()
        h = self.preview_container.winfo_height()
        if w < 100: w = 400
        if h < 100: h = 400
        
        # Keep aspect ratio
        display_img = image.copy()
        display_img.thumbnail((w-40, h-40), Image.Resampling.LANCZOS)
        
        ctk_img = ctk.CTkImage(display_img, size=display_img.size)
        self.preview_label.configure(image=ctk_img, text="")

    def _add_to_gallery(self, img):
        thumb = img.copy()
        thumb.thumbnail((60, 60))
        ctk_thumb = ctk.CTkImage(thumb, size=(60, 60))
        
        btn = ctk.CTkButton(self.gallery_frame, image=ctk_thumb, text="", width=70, height=70,
                           fg_color="transparent", border_width=1, border_color=Colors.BORDER_LIGHT,
                           command=lambda i=img: self._show_result(i))
        btn.pack(side="left", padx=5)

    def _get_smart_filename(self, ext):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Get prompt from last generation or history
            # For simplicity, use first few words of current_prompt
            if hasattr(self, 'current_prompt'):
                safe_prompt = "".join([c if c.isalnum() else "_" for c in self.current_prompt])
                safe_prompt = safe_prompt[:20]
                return f"icon_{safe_prompt}_{timestamp}{ext}"
        except: pass
        return f"icon_{int(time.time())}{ext}"

    def save(self, fmt):
        if not self.generated_image: return
        ext = ".ico" if fmt == "ico" else ".png"
        default_name = self._get_smart_filename(ext)
        
        path = filedialog.asksaveasfilename(defaultextension=ext, initialfile=default_name)
        if path:
            if fmt == "ico":
                self.generated_image.save(path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
            else:
                self.generated_image.save(path)

if __name__ == "__main__":
    app = IconGenGUI()
    app.mainloop()
