
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import sys
import os
import shutil
import time
import random
import io
from pathlib import Path
from PIL import Image

# ...

    def _build_settings(self, parent):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=20)
        
        # Res
        PremiumLabel(f, text="Resolution", style="small").pack(anchor="w")
        self.combo_res = ctk.CTkComboBox(f, values=["1024x1024", "896x1152", "1152x896"], fg_color=Colors.BG_MAIN, border_color=Colors.BORDER_LIGHT)
        self.combo_res.pack(fill="x", pady=(2, 10))
        
        # Steps/CFG compact
        r2 = ctk.CTkFrame(f, fg_color="transparent")
        r2.pack(fill="x")
        
        col1 = ctk.CTkFrame(r2, fg_color="transparent")
        col1.pack(side="left", fill="x", expand=True, padx=(0,5))
        PremiumLabel(col1, text="Steps: 4", style="small").pack(anchor="w")
        self.lbl_steps = col1.winfo_children()[0] # Fix: winfo_children
        self.slider_steps = ctk.CTkSlider(col1, from_=1, to=10, number_of_steps=9, height=16, bg_color=Colors.BG_CARD)
        self.slider_steps.set(4)
        self.slider_steps.pack(fill="x")
        
        col2 = ctk.CTkFrame(r2, fg_color="transparent")
        col2.pack(side="right", fill="x", expand=True, padx=(5,0))
        PremiumLabel(col2, text="CFG: 1.0", style="small").pack(anchor="w")
        self.slider_cfg = ctk.CTkSlider(col2, from_=1.0, to=5.0, number_of_steps=40, height=16)
        self.slider_cfg.set(1.0)
        self.slider_cfg.pack(fill="x")

        # Seed
        PremiumLabel(f, text="Seed", style="small").pack(anchor="w", pady=(10,0))
        self.entry_seed = ctk.CTkEntry(f, placeholder_text="Random", fg_color=Colors.BG_MAIN, border_color=Colors.BORDER_LIGHT)
        self.entry_seed.pack(fill="x")

    def add_prompt_box(self):
        frame = ctk.CTkFrame(self.prompt_scroll, fg_color=Colors.BG_MAIN, corner_radius=8, border_width=1, border_color=Colors.BORDER_LIGHT)
        frame.pack(fill="x", pady=5)
        
        txt = ctk.CTkTextbox(frame, height=60, font=Fonts.BODY, fg_color="transparent")
        txt.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Delete btn
        if len(self.prompts) > 0:
            ctk.CTkButton(frame, text="×", width=30, fg_color="transparent", hover_color=Colors.ACCENT_ERROR, text_color=Colors.TEXT_TERTIARY,
                         command=lambda f=frame, t=txt: self.remove_prompt_box(f, t)).pack(side="right", padx=2)
            
        self.prompts.append(txt)
        self.prompt_frames.append(frame)

    def remove_prompt_box(self, frame, txt_widget):
        if txt_widget in self.prompts: self.prompts.remove(txt_widget)
        if frame in self.prompt_frames: self.prompt_frames.remove(frame)
        frame.destroy()

    def start_generation(self):
        if self.is_processing: return
        texts = [p.get("1.0", "end").strip() for p in self.prompts if p.get("1.0", "end").strip()]
        if not texts: return
        
        full_prompt = ", ".join(texts)
        width, height = map(int, self.combo_res.get().split()[0].split("x"))
        steps = int(self.slider_steps.get())
        cfg = self.slider_cfg.get()
        seed_val = self.entry_seed.get().strip()
        seed = int(seed_val) if seed_val.isdigit() else random.randint(0, 2**32-1)
        
        self.is_processing = True
        self.btn_generate.configure(state="disabled", text="Igniting...")
        self.status_badge.set_status("Processing...", "active")
        
        threading.Thread(target=self._run_workflow, args=(full_prompt, width, height, steps, cfg, seed), daemon=True).start()

    def _run_workflow(self, prompt, width, height, steps, cfg, seed):
        try:
            wf_path = workflow_utils.get_workflow_path("z_image_turbo")
            workflow = workflow_utils.load_workflow(wf_path)
            
            # Use workflow_utils helpers or direct manipulation if known
            # Simple direct update as per previous file logic
            # Node IDs: 45 (Text), 41 (EmptySD3), 44 (KSampler)
            
            # We need to perform same JSON updates as original file
            # ... (Converting API format logic if needed, but comfyui_client usually accepts API format directly)
            
            if "nodes" in workflow:
                # Naive conversion or just implement the conversion logic again
                 workflow = self._convert_to_api(workflow)

            workflow["45"]["inputs"]["text"] = prompt
            workflow["44"]["inputs"]["seed"] = seed
            workflow["44"]["inputs"]["steps"] = steps
            workflow["44"]["inputs"]["cfg"] = cfg
            workflow["41"]["inputs"]["width"] = width
            workflow["41"]["inputs"]["height"] = height
            
            outputs = self.client.generate_image(workflow)
            
            images = []
            if outputs:
                for nid, result in outputs.items():
                    # ComfyUIManager returns {node_id: [bytes]} usually
                    for img_bytes in result:
                         images.append(Image.open(io.BytesIO(img_bytes)))
            
            self.after(0, lambda: self._on_success(images))

        except Exception as e:
            self.after(0, lambda: self.status_badge.set_status(f"Error: {e}", "error"))
            self.is_processing = False
            self.after(0, lambda: self.btn_generate.configure(state="normal", text="Ignite Turbo"))

    def _convert_to_api(self, data):
        # Simplified copy of original logic
        api = {}
        links = {}
        for l in data.get("links", []): links[l[0]] = (str(l[1]), l[2])
        for node in data.get("nodes", []):
            inputs = {}
            for inp in node.get("inputs",[]):
                if inp.get("link") and inp["link"] in links: inputs[inp["name"]] = list(links[inp["link"]])
            vals = node.get("widgets_values", [])
            # ... (Assume robust conversion in workflow_utils eventually, for now quick mapping)
            if vals:
                ct = node["type"]
                if ct == "CLIPTextEncode": inputs["text"] = vals[0]
                elif ct == "EmptySD3LatentImage": inputs["width"], inputs["height"] = vals[0], vals[1]
                elif ct == "KSampler": inputs["seed"], inputs["steps"], inputs["cfg"] = vals[0], vals[2], vals[3]
            api[str(node["id"])] = {"class_type": node["type"], "inputs": inputs}
        return api

    def _on_success(self, images):
        self.is_processing = False
        self.btn_generate.configure(state="normal", text="Ignite Turbo")
        self.status_badge.set_status("Complete", "success")
        
        if images:
            self._show_image(images[-1])
            # Save logic omitted for brevity, essentially just save to disk
            
    def _show_image(self, img):
        w = self.right_panel.winfo_width()
        h = self.right_panel.winfo_height() - 80
        display = img.copy()
        display.thumbnail((w,h))
        ctk_img = ctk.CTkImage(display, size=display.size)
        self.preview_label.configure(image=ctk_img, text="")
        self.current_image = img

    def open_output_folder(self):
        # ...
        pass
    
    def save_current_image(self):
        # ...
        pass

if __name__ == "__main__":
    app = ZImageTurboGUI()
    app.mainloop()
