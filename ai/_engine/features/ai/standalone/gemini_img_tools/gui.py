"""
Gemini Image Tools - Main GUI Module
Contains the main GeminiImageToolsGUI class.
"""
import sys
import os
import cv2
import numpy as np
from pathlib import Path
import threading
import time
import io
from tkinter import messagebox, filedialog
from utils.i18n import t
import traceback

import customtkinter as ctk
from PIL import Image, ImageGrab
from utils.gui_lib import THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN

# Package imports
from .core import (
    get_gemini_client, 
    imread_unicode, 
    get_unique_path,
    logger,
    GENAI_AVAILABLE
)
if GENAI_AVAILABLE:
    from google.genai import types
else:
    types = None

from .pbr import (
    generate_normal_map,
    generate_roughness_map,
    generate_displacement_map,
    generate_occlusion_map,
    generate_metallic_map,
    make_tileable_synthesis
)
from .history import HistoryManager
from .viewer import ImageViewer
from .prompts import (
    generate_style_prompt,
    generate_pbr_prompt,
    generate_tile_prompt,
    generate_weather_prompt,
    generate_analyze_prompt,
    generate_outpaint_prompt,
    generate_inpaint_prompt
)

# Setup path for external imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(src_dir))

from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER
from utils.image_utils import scan_for_images


class GeminiImageToolsGUI(BaseWindow):
    """Main GUI for Gemini Image Tools."""
    
    def __init__(self, target_path=None, start_tab="Style"):
        super().__init__(title="Gemini Image Tools (Gemini 2.5)", width=1200, height=900, icon_name="ai_gemini_vision")
        
        self.target_path = target_path
        self.start_tab = start_tab
        self.selection = []
        self.last_api_request = 0
        self.api_delay = 2.0
        self.processed_img = None
        
        if target_path:
            self.selection, scan_count = scan_for_images(target_path)
            if not self.selection:
                messagebox.showerror(t("common.error"), f"No valid image found.\nScanned {scan_count} items.")
                self.destroy()
                return
                
        if not self.selection:
            messagebox.showerror(t("common.error"), "No image selected.")
            self.destroy()
            return
            
        self.current_image_path = self.selection[0]
        
        try:
            self.original_img = imread_unicode(str(self.current_image_path))
            if self.original_img is None:
                raise ValueError("Image loaded as None")
            self.cv_img = self.original_img.copy()
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            self.cv_img = None
            
        if self.cv_img is None:
            messagebox.showerror(t("common.error"), "Failed to load image.\n(Check file path or format)")
            self.destroy()
            return

        self.create_widgets()
        
        # History Init
        cache_dir = current_dir / ".cache"
        self.history = HistoryManager(cache_dir)
        self.history.add(self.cv_img)
        
        self.update()
        self.viewer.load_image(self.cv_img)
        self.update_info_header()
        self.update_prompt_from_ui()
        
        # Clipboard Bind
        self.bind("<Control-v>", self.paste_from_clipboard)

    def create_widgets(self):
        """Create all GUI widgets."""
        # Main Layout: Grid
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Content Frame
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        
        self.content_frame.grid_columnconfigure(0, weight=0)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Left Panel
        self.left_panel = ctk.CTkFrame(self.content_frame, width=350, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        self.left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 5), pady=0)
        
        # Right Panel
        self.right_panel = ctk.CTkFrame(self.content_frame, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        
        # Info Header
        self.info_frame = ctk.CTkFrame(self.right_panel, height=30, fg_color="transparent")
        self.info_frame.pack(side="top", fill="x", padx=10, pady=(5, 0))
        
        self.lbl_info = ctk.CTkLabel(self.info_frame, text="", text_color="gray", font=("Arial", 12, "bold"))
        self.lbl_info.pack(side="top", anchor="center")
        
        # Image Viewer
        self.viewer = ImageViewer(self.right_panel)
        self.viewer.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        
        # Navigation Bar
        self._create_navigation_bar()
        
        # Global Image Type Selector
        ctk.CTkLabel(self.left_panel, text="Image Type:", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5), padx=10, anchor="w")
        self.image_type = ctk.StringVar(value="Select Type")
        ctk.CTkComboBox(self.left_panel, variable=self.image_type, 
                        values=["Select Type", "UV Texture", "Tileable Texture", "Photo", "Sketch"], 
                        command=self.update_prompt_from_ui).pack(fill="x", padx=10, pady=(0, 10))
        
        # Tabs
        self.tab_view = ctk.CTkTabview(self.left_panel, command=self.on_tab_change,
                                        fg_color=THEME_CARD,
                                        segmented_button_selected_color=THEME_BTN_PRIMARY,
                                        segmented_button_selected_hover_color=THEME_BTN_HOVER,
                                        segmented_button_unselected_color=THEME_DROPDOWN_FG,
                                        segmented_button_unselected_hover_color=THEME_DROPDOWN_BTN,
                                        border_width=1, border_color=THEME_BORDER,
                                        text_color="#E0E0E0")
        self.tab_view.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_style = self.tab_view.add("Style")
        self.tab_tile = self.tab_view.add("Tileable")
        self.tab_weather = self.tab_view.add("Weathering")
        self.tab_analyze = self.tab_view.add("Analysis")
        self.tab_outpaint = self.tab_view.add("Outpaint")
        self.tab_inpaint = self.tab_view.add("Inpaint")
        
        self._setup_style_tab()
        self._setup_tile_tab()
        self._setup_weather_tab()
        self._setup_analyze_tab()
        self._setup_outpaint_tab()
        self._setup_inpaint_tab()
        
        if self.start_tab:
            try:
                self.tab_view.set(self.start_tab)
            except ValueError:
                pass
        
        # Bottom Bar
        self._create_bottom_bar()

    def _create_navigation_bar(self):
        """Create the navigation bar at the bottom of the right panel."""
        self.nav_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=30)
        self.nav_frame.pack(side="bottom", fill="x", pady=(0, 5))
        
        self.nav_container = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        self.nav_container.pack(side="top", anchor="center")
        
        self.btn_open = ctk.CTkButton(self.nav_container, text="📂", width=30, height=24, 
                                       command=self.open_file_dialog, fg_color="transparent", 
                                       text_color="gray", hover_color="#333333")
        self.btn_open.pack(side="left", padx=5)
        
        self.btn_prev_arrow = ctk.CTkButton(self.nav_container, text="<", width=30, height=24, 
                                            command=self.do_undo, state="disabled")
        self.btn_prev_arrow.pack(side="left", padx=5)
        
        self.lbl_counter = ctk.CTkLabel(self.nav_container, text="1 / 1", font=("Arial", 12), text_color="gray")
        self.lbl_counter.pack(side="left", padx=10)
        
        self.btn_next_arrow = ctk.CTkButton(self.nav_container, text=">", width=30, height=24, 
                                            command=self.do_redo, state="disabled")
        self.btn_next_arrow.pack(side="left", padx=5)
        
        self.btn_clear = ctk.CTkButton(self.nav_container, text="🗑️", width=30, height=24, 
                                       command=self.close_image, fg_color="transparent", 
                                       text_color="gray", hover_color="#333333")
        self.btn_clear.pack(side="left", padx=5)

    def _create_bottom_bar(self):
        """Create the bottom bar with prompt area and action buttons."""
        self.bottom_bar = ctk.CTkFrame(self.main_frame, height=150)
        self.bottom_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        # Prompt Area
        prompt_frame = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        prompt_frame.pack(fill="x", padx=10, pady=(5, 0))
        
        ctk.CTkLabel(prompt_frame, text="AI Prompt:").pack(side="left", anchor="w")
        ctk.CTkButton(prompt_frame, text="[JSON]", width=50, height=20, fg_color="transparent", 
                      border_width=1, text_color="gray", command=self.show_prompt_json).pack(side="left", padx=10)
        
        self.prompt_entry = ctk.CTkTextbox(self.bottom_bar, height=50)
        self.prompt_entry.pack(fill="x", padx=10, pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(btn_frame, text="Generate (Gemini 2.5)", command=self.run_ai_request, 
                      fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER, width=150).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Reset to Original", command=self.reset_image, 
                      fg_color="gray", width=120).pack(side="left", padx=5)
        
        self.status_label = ctk.CTkLabel(btn_frame, text="Ready", text_color="gray", font=("Arial", 12))
        self.status_label.pack(side="left", padx=15)
        
        ctk.CTkButton(btn_frame, text="Save As...", command=self.save_result, 
                      fg_color="green", width=100).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Copy", command=self.copy_to_clipboard, 
                      fg_color="#E67E22", width=80).pack(side="right", padx=5)

    # --- Tab Setup Methods ---
    
    def _setup_style_tab(self):
        ctk.CTkLabel(self.tab_style, text="AI Style Transfer", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        self.style_mode = ctk.StringVar(value="Realistic")
        ctk.CTkComboBox(self.tab_style, variable=self.style_mode, 
                        values=["Realistic", "Stylized", "Cartoon", "Cyberpunk", "Sketch", "Oil Painting"], 
                        command=self.update_prompt_from_ui).pack(pady=10)
        
        ctk.CTkLabel(self.tab_style, text="Style Strength:").pack(pady=(20, 5))
        self.slider_style_strength = ctk.CTkSlider(self.tab_style, from_=0.0, to=1.0, number_of_steps=20, 
                                                   command=self.update_prompt_from_ui)
        self.slider_style_strength.set(0.7)
        self.slider_style_strength.pack(fill="x", padx=10)

    def _setup_tile_tab(self):
        ctk.CTkLabel(self.tab_tile, text="Make Tileable (AI)", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        ctk.CTkLabel(self.tab_tile, text="Texture Scale Factor:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        self.slider_tile_scale = ctk.CTkSlider(self.tab_tile, from_=0.5, to=2.0, number_of_steps=30, 
                                               command=self.update_prompt_from_ui)
        self.slider_tile_scale.set(1.0)
        self.slider_tile_scale.pack(fill="x", padx=10, pady=5)
        
        scale_frame = ctk.CTkFrame(self.tab_tile, fg_color="transparent")
        scale_frame.pack(fill="x", padx=10)
        ctk.CTkLabel(scale_frame, text="0.5x (Zoom Out)", font=("", 10)).pack(side="left")
        ctk.CTkLabel(scale_frame, text="2.0x (Zoom In)", font=("", 10)).pack(side="right")
        
        ctk.CTkLabel(self.tab_tile, text="Description / Context (Optional):", anchor="w").pack(fill="x", padx=10, pady=(20, 0))
        self.entry_tile_desc = ctk.CTkEntry(self.tab_tile, placeholder_text="e.g. Concrete wall, Fabric pattern...")
        self.entry_tile_desc.pack(fill="x", padx=10, pady=5)
        self.entry_tile_desc.bind("<KeyRelease>", self.update_prompt_from_ui)
        
        self.btn_check_tile = ctk.CTkButton(self.tab_tile, text="🔍 Check Tiling (Offset 50%)", 
                                            command=self.toggle_tiling_check, fg_color="transparent", 
                                            border_width=1, text_color="gray")
        self.btn_check_tile.pack(pady=15)

    def _setup_weather_tab(self):
        ctk.CTkLabel(self.tab_weather, text="AI Weathering", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        self.weather_mode = ctk.StringVar(value="Rust")
        ctk.CTkComboBox(self.tab_weather, variable=self.weather_mode, 
                        values=["Rust", "Dirt", "Moss", "Scratches", "Old Paper", "Worn Edges"], 
                        command=self.update_prompt_from_ui).pack(pady=10)
        
        ctk.CTkLabel(self.tab_weather, text="Intensity:").pack(pady=5)
        self.slider_weather = ctk.CTkSlider(self.tab_weather, from_=0.0, to=1.0, number_of_steps=20, 
                                            command=self.update_prompt_from_ui)
        self.slider_weather.set(0.5)
        self.slider_weather.pack(fill="x", padx=10)

    def _setup_analyze_tab(self):
        ctk.CTkLabel(self.tab_analyze, text="Gemini Vision Analysis", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        ctk.CTkLabel(self.tab_analyze, text="Output Format:").pack(pady=(5, 0))
        self.analyze_style = ctk.StringVar(value="General Analysis")
        ctk.CTkComboBox(self.tab_analyze, variable=self.analyze_style, 
                        values=["General Analysis", "Midjourney Prompt", "Flux Prompt", "ComfyUI Prompt"],
                        command=self.update_prompt_from_ui).pack(pady=5)

        self.txt_analysis = ctk.CTkTextbox(self.tab_analyze, height=200)
        self.txt_analysis.pack(fill="x", padx=5, pady=5)
        
        btn_frame = ctk.CTkFrame(self.tab_analyze, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(btn_frame, text="Analyze Texture", command=self.run_analysis).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="Copy to Clipboard", command=self.copy_analysis_to_clipboard, 
                      fg_color="gray").pack(side="right", expand=True, padx=5)

    def _setup_outpaint_tab(self):
        ctk.CTkLabel(self.tab_outpaint, text="AI Outpainting", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        ctk.CTkLabel(self.tab_outpaint, text="Expand Direction:").pack(pady=5)
        self.outpaint_dir = ctk.StringVar(value="All Sides")
        ctk.CTkComboBox(self.tab_outpaint, variable=self.outpaint_dir, 
                        values=["All Sides", "Horizontal", "Vertical"], 
                        command=self.update_prompt_from_ui).pack(pady=5)
        
        ctk.CTkLabel(self.tab_outpaint, text="Expansion Scale:").pack(pady=(20, 5))
        self.slider_outpaint = ctk.CTkSlider(self.tab_outpaint, from_=1.1, to=2.0, number_of_steps=18, 
                                             command=self.update_prompt_from_ui)
        self.slider_outpaint.set(1.5)
        self.slider_outpaint.pack(fill="x", padx=10)

    def _setup_inpaint_tab(self):
        ctk.CTkLabel(self.tab_inpaint, text="Object Removal / Replace", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        ctk.CTkLabel(self.tab_inpaint, text="Target Object (to remove/change):").pack(pady=(10, 0), anchor="w", padx=10)
        self.entry_inpaint_target = ctk.CTkEntry(self.tab_inpaint)
        self.entry_inpaint_target.pack(fill="x", padx=10, pady=5)
        self.entry_inpaint_target.bind("<KeyRelease>", self.update_prompt_from_ui)
        
        ctk.CTkLabel(self.tab_inpaint, text="Replacement (leave empty to remove):").pack(pady=(10, 0), anchor="w", padx=10)
        self.entry_inpaint_replace = ctk.CTkEntry(self.tab_inpaint)
        self.entry_inpaint_replace.pack(fill="x", padx=10, pady=5)
        self.entry_inpaint_replace.bind("<KeyRelease>", self.update_prompt_from_ui)

    # --- Event Handlers ---
    
    def on_tab_change(self):
        self.update_prompt_from_ui()

    def update_prompt_from_ui(self, event=None):
        """Update the prompt based on current tab and settings."""
        tab = self.tab_view.get()
        img_type = self.image_type.get()
        
        if tab == "Style":
            prompt = generate_style_prompt(img_type, self.style_mode.get(), self.slider_style_strength.get())
        elif tab == "Tileable":
            prompt = generate_tile_prompt(img_type, self.slider_tile_scale.get(), self.entry_tile_desc.get().strip())
        elif tab == "Weathering":
            prompt = generate_weather_prompt(img_type, self.weather_mode.get(), self.slider_weather.get())
        elif tab == "Analysis":
            prompt = generate_analyze_prompt(img_type, self.analyze_style.get())
        elif tab == "Outpaint":
            prompt = generate_outpaint_prompt(img_type, self.outpaint_dir.get(), self.slider_outpaint.get())
        elif tab == "Inpaint":
            prompt = generate_inpaint_prompt(img_type, self.entry_inpaint_target.get(), self.entry_inpaint_replace.get())
        else:
            prompt = ""
        
        self.prompt_entry.delete("1.0", "end")
        self.prompt_entry.insert("1.0", prompt)

    def toggle_tiling_check(self):
        """Toggle tiling check view."""
        if self.cv_img is None:
            return
        
        if not hasattr(self, 'is_tiling_check'):
            self.is_tiling_check = False
        
        if self.is_tiling_check:
            self.viewer.load_image(self.cv_img)
            self.is_tiling_check = False
            self.btn_check_tile.configure(text="🔍 Check Tiling (Offset 50%)", fg_color="transparent", text_color="gray")
        else:
            h, w = self.cv_img.shape[:2]
            img_roll = np.roll(self.cv_img, w // 2, axis=1)
            img_roll = np.roll(img_roll, h // 2, axis=0)
            cv2.line(img_roll, (w//2, 0), (w//2, h), (0, 255, 0), 1)
            cv2.line(img_roll, (0, h//2), (w, h//2), (0, 255, 0), 1)
            self.viewer.load_image(img_roll)
            self.is_tiling_check = True
            self.btn_check_tile.configure(text="🔙 Restore View", fg_color="#2b2b2b", text_color="white")

    def check_rate_limit(self):
        """Check if we need to wait before making another API request."""
        now = time.time()
        if now - self.last_api_request < self.api_delay:
            wait_time = self.api_delay - (now - self.last_api_request)
            self.status_label.configure(text=f"Wait {wait_time:.1f}s...", text_color="orange")
            return False
        self.last_api_request = now
        self.status_label.configure(text="Processing...", text_color="yellow")
        return True

    def reset_image(self):
        """Reset to original image."""
        self.cv_img = self.original_img.copy()
        self.viewer.load_image(self.cv_img)
        self.history.add(self.cv_img)
        self.update_history_buttons()
        self.status_label.configure(text="Reset to Original", text_color="green")
        
    def update_info_header(self):
        """Update the info header with current image details."""
        if self.cv_img is None:
            return
        h, w = self.cv_img.shape[:2]
        filename = self.current_image_path.name
        folder = self.current_image_path.parent.name
        self.lbl_info.configure(text=f"File: {filename} | Folder: {folder} | Res: {w}x{h}")
        
    def do_undo(self):
        """Undo last change."""
        img = self.history.undo()
        if img is not None:
            self.cv_img = img
            self.viewer.load_image(self.cv_img)
            self.update_history_buttons()
            self.update_info_header()
            
    def do_redo(self):
        """Redo last undone change."""
        img = self.history.redo()
        if img is not None:
            self.cv_img = img
            self.viewer.load_image(self.cv_img)
            self.update_history_buttons()
            self.update_info_header()
            
    def update_history_buttons(self):
        """Update undo/redo button states."""
        can_undo = self.history.can_undo()
        can_redo = self.history.can_redo()
        
        self.btn_prev_arrow.configure(state="normal" if can_undo else "disabled")
        self.btn_next_arrow.configure(state="normal" if can_redo else "disabled")
        
        current = self.history.current_index + 1
        total = len(self.history.history)
        self.lbl_counter.configure(text=f"{current} / {total}")

    # --- AI Request Handling ---
    
    def run_ai_request(self):
        """Run AI generation request."""
        if not self.check_rate_limit():
            return
        
        prompt = self.prompt_entry.get("1.0", "end").strip()
        if not prompt:
            self.status_label.configure(text="Error: No Prompt", text_color="red")
            return
            
        client, api_error = get_gemini_client()
        if not client:
            messagebox.showerror(t("common.error"), api_error or "Gemini API Key not configured.")
            self.status_label.configure(text="API Key Required", text_color="red")
            return

        def _process():
            try:
                current_tab = self.tab_view.get()
                model_name = "gemini-2.5-flash" if current_tab == "Analysis" else "gemini-2.5-flash-preview-05-20"
                
                self.after(0, lambda: self.status_label.configure(text=f"Sending to {model_name}...", text_color="yellow"))

                is_success, buffer = cv2.imencode(".png", self.cv_img)
                if not is_success:
                    raise ValueError("Failed to encode image")
                img_bytes = buffer.tobytes()

                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        prompt,
                        types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                    ]
                )
                
                text_output = ""
                image_found = False
                new_cv_img = None
                
                if response.parts:
                    for part in response.parts:
                        if part.text:
                            text_output += part.text + "\n"
                        elif part.inline_data:
                            image_data = part.inline_data.data
                            image = Image.open(io.BytesIO(image_data))
                            new_cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                            image_found = True
                
                self.after(0, lambda: self._handle_ai_response(text_output, new_cv_img, image_found))

            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._handle_ai_error(err_msg))
        
        threading.Thread(target=_process, daemon=True).start()

    def _handle_ai_response(self, text_output, new_cv_img, image_found):
        """Handle successful AI response."""
        if image_found and new_cv_img is not None:
            self.cv_img = new_cv_img
            self.viewer.load_image(self.cv_img)
            self.processed_img = self.cv_img
            
            self.history.add(self.cv_img)
            self.update_history_buttons()
            self.update_info_header()
            
            # Auto-save
            try:
                timestamp = int(time.time())
                save_name = f"{self.current_image_path.stem}_gen_{timestamp}.png"
                save_path = self.current_image_path.parent / save_name
                cv2.imwrite(str(save_path), self.cv_img)
                self.status_label.configure(text=f"Saved: {save_name}", text_color="green")
            except Exception as e:
                self.status_label.configure(text="Generated (Auto-save failed)", text_color="orange")
        
        if text_output:
            if self.tab_view.get() == "Analysis":
                self.txt_analysis.delete("1.0", "end")
                self.txt_analysis.insert("1.0", text_output)
                if not image_found:
                    self.status_label.configure(text="Analysis Complete", text_color="green")
            elif not image_found:
                messagebox.showinfo(t("common.info"), f"Model returned text:\n\n{text_output}")
                self.status_label.configure(text="Text Response Received", text_color="green")

    def _handle_ai_error(self, err_msg):
        """Handle AI API error."""
        if "429" in err_msg or "Quota" in err_msg or "ResourceExhausted" in err_msg:
            self.status_label.configure(text="Error: Quota Exceeded", text_color="red")
            messagebox.showerror(t("common.error"), "Gemini API Quota Exceeded.\nPlease wait a minute or check your plan.")
        else:
            self.status_label.configure(text="Error: API Failed", text_color="red")
            messagebox.showerror(t("common.error"), f"An error occurred:\n{err_msg[:200]}...")

    def run_analysis(self):
        """Run analysis on the current image."""
        self.tab_view.set("Analysis")
        self.update_prompt_from_ui()
        self.run_ai_request()

    # --- File Operations ---
    
    def save_result(self):
        """Save the current image."""
        if not hasattr(self, 'processed_img') or self.processed_img is None:
            self.processed_img = self.cv_img
             
        initial_name = f"{self.current_image_path.stem}_edited.png"
        path = filedialog.asksaveasfilename(defaultextension=".png", initialfile=initial_name)
        if path:
            save_path = Path(path)
            if save_path.exists():
                save_path = get_unique_path(save_path)
            cv2.imwrite(str(save_path), self.processed_img)
            messagebox.showinfo(t("common.success"), f"Saved to {save_path.name}")

    def copy_to_clipboard(self):
        """Copy current image to clipboard."""
        if self.cv_img is None:
            return
        
        try:
            import tempfile
            import subprocess
            
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                
            cv2.imwrite(str(tmp_path), self.cv_img)
            
            cmd = f"Set-Clipboard -Path '{str(tmp_path)}'"
            subprocess.run(["powershell", "-Command", cmd], check=True)
            
            self.status_label.configure(text="Copied to Clipboard", text_color="green")
            
        except Exception as e:
            self.status_label.configure(text="Clipboard Error", text_color="red")

    def copy_analysis_to_clipboard(self):
        """Copy analysis text to clipboard."""
        text = self.txt_analysis.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status_label.configure(text="Copied to Clipboard", text_color="green")
            messagebox.showinfo(t("common.success"), "Analysis text copied to clipboard.")

    def show_prompt_json(self):
        """Show the current prompt in JSON format."""
        import json
        prompt = self.prompt_entry.get("1.0", "end").strip()
        
        data = {
            "system_instruction": "You are a texture generation expert...",
            "user_prompt": prompt,
            "model": "gemini-2.5-flash-preview-05-20" if self.tab_view.get() != "Analysis" else "gemini-2.5-flash"
        }
        
        json_str = json.dumps(data, indent=2)
        
        top = ctk.CTkToplevel(self)
        top.title("Prompt Inspection")
        top.geometry("500x400")
        
        txt = ctk.CTkTextbox(top, font=("Consolas", 12))
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", json_str)

    def close_image(self):
        """Close current image."""
        self.cv_img = None
        self.original_img = None
        self.viewer.image = None
        self.viewer.canvas.delete("all")
        self.lbl_info.configure(text="No Image Loaded")
        self.lbl_counter.configure(text="- / -")
        self.status_label.configure(text="Image Closed", text_color="gray")
        self.history = HistoryManager(current_dir / ".cache")
        self.update_history_buttons()

    def paste_from_clipboard(self, event=None):
        """Paste image from clipboard."""
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                self.load_new_image_from_cv(cv_img, "Clipboard_Image")
            elif isinstance(img, list):
                self.load_new_image(img[0])
        except Exception as e:
            pass

    def open_file_dialog(self):
        """Open file dialog to load a new image."""
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tga")])
        if path:
            self.load_new_image(path)

    def load_new_image(self, path):
        """Load a new image from file path."""
        try:
            cv_img = imread_unicode(str(path))
            if cv_img is None:
                messagebox.showerror(t("common.error"), "Failed to load image.\nFormat not supported or file corrupted.")
                return
                
            self.current_image_path = Path(path)
            self.load_new_image_from_cv(cv_img, self.current_image_path.name)
            
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(t("common.error"), f"Failed to load image: {e}")

    def load_new_image_from_cv(self, cv_img, name="Image"):
        """Load a new image from CV2 array."""
        self.cv_img = cv_img
        self.original_img = cv_img.copy()
        
        self.history = HistoryManager(current_dir / ".cache")
        self.history.add(self.cv_img)
        
        self.viewer.load_image(self.cv_img)
        self.update_history_buttons()
        
        h, w = self.cv_img.shape[:2]
        folder = self.current_image_path.parent.name if hasattr(self, 'current_image_path') else "Clipboard"
        self.lbl_info.configure(text=f"File: {name} | Folder: {folder} | Res: {w}x{h}")
        self.status_label.configure(text="Image Loaded", text_color="green")

    def apply_offset(self):
        """Apply tileable offset."""
        res = make_tileable_synthesis(self.cv_img)
        self.viewer.load_image(res)
        self.processed_img = res
        self.status_label.configure(text="Applied Offset", text_color="green")


def run_gui(target_path=None, start_tab="Style"):
    """Entry point for running the Gemini Image Tools GUI."""
    app = GeminiImageToolsGUI(target_path=target_path, start_tab=start_tab)
    app.mainloop()


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    run_gui(target)
