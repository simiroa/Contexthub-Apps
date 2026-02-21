import os
import sys
from pathlib import Path

# Add src to path for absolute imports
try:
    current_dir = Path(__file__).resolve().parent
    src_dir = current_dir.parent.parent  # features/prompt_master -> src
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
except: pass

import customtkinter as ctk
from tkinter import messagebox
import requests
import threading

from features.prompt_master.mixins import PresetMixin, TagLibraryMixin, TranslationMixin, ImageMixin
from features.prompt_master.tooltip import Tooltip
from features.prompt_master.constants import PRESETS_DIR
from utils.gui_lib import setup_theme, THEME_BG, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER
from utils.i18n import t

class PromptMasterApp(PresetMixin, TagLibraryMixin, TranslationMixin, ImageMixin, ctk.CTk):
    """
    Main Application Class for Prompt Master.
    
    Combines various mixins to provide a comprehensive prompt engineering tool:
    - PresetMixin: Handles loading and displaying prompt templates.
    - TagLibraryMixin: Manages custom tags and user context.
    - TranslationMixin: Provides Korean-to-English translation for inputs.
    - ImageMixin: Handles image display, pasting, and saving.
    """
    def __init__(self):
        super().__init__()
        setup_theme()  # Apply theme from settings.json

        self.title(t("prompt_master.header"))
        
        # Enforce minimum size and default size
        self.minsize(1200, 800)
        
        # Force update before setting geometry to ensure it applies
        self.update_idletasks()
        self.geometry("1450x900")

        # Data
        self.engines = []
        self.current_engine = None
        self.current_engine_color = ("#1F6AA5", "#144870")
        self.presets = []
        self.current_preset_data = None
        self.input_widgets = {}
        self.option_widgets = {}
        self.custom_input_widget = None
        self.tags = self.load_tags()
        self.selected_tags = []
        self.engine_tabs = {}  # Store tab buttons

        # Main container (Deep Black Background)
        main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=THEME_BG)
        main_container.pack(fill="both", expand=True)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_columnconfigure(2, weight=0, minsize=450) # Result Card Width

        # Top bar for engine tabs
        self.top_bar = ctk.CTkFrame(main_container, height=50, corner_radius=0, fg_color=THEME_BG, border_width=1, border_color=THEME_BORDER)
        self.top_bar.grid(row=0, column=0, columnspan=3, sticky="ew")
        
        # Logo on left
        logo = ctk.CTkLabel(self.top_bar, text=t("prompt_master.header"), font=ctk.CTkFont(size=18, weight="bold"))
        logo.pack(side="left", padx=20, pady=10)
        
        # Engine tabs in center
        self.tabs_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.tabs_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Left Panel: Preset Manager (COMPACT) - Integrated with Background
        self.left_frame = ctk.CTkFrame(main_container, width=100, corner_radius=0, fg_color=THEME_BG, border_width=1, border_color=THEME_BORDER)
        self.left_frame.grid(row=1, column=0, sticky="nsew")
        self.left_frame.grid_rowconfigure(0, weight=0) # Search & Tools
        self.left_frame.grid_rowconfigure(1, weight=1) # List (Expand)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Search & Tools Container
        self.search_container = ctk.CTkFrame(self.left_frame, fg_color="transparent", height=30)
        self.search_container.grid(row=0, column=0, padx=5, pady=(10, 5), sticky="ew")
        self.search_container.grid_columnconfigure(0, weight=1) # Search takes available space
        
        # Search Box
        self.preset_search = ctk.CTkEntry(
            self.search_container, 
            placeholder_text=t("prompt_master.placeholder_search"),
            height=24,
            font=ctk.CTkFont(size=12),
            border_width=1,
            border_color=THEME_BORDER,
            fg_color=THEME_BG
        )
        self.preset_search.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        self.preset_search.bind("<KeyRelease>", self.filter_presets)
        Tooltip(self.preset_search, t("prompt_master.tooltip_search"))

        # Buttons (Icon Only)
        self.open_folder_btn = ctk.CTkButton(
            self.search_container, 
            text="📁", 
            command=self.open_presets_folder,
            height=24,
            width=24,
            fg_color="transparent",
            border_width=1,
            border_color=THEME_BORDER,
            hover_color="#1a1a1a",
            border_spacing=0
        )
        self.open_folder_btn.grid(row=0, column=1, padx=(2, 0))
        Tooltip(self.open_folder_btn, t("prompt_master.tooltip_folder"))

        self.guide_btn = ctk.CTkButton(
            self.search_container, 
            text="📝", 
            command=self.show_add_guide,
            height=24,
            width=24,
            fg_color="transparent",
            border_width=1,
            border_color=THEME_BORDER,
            hover_color="#1a1a1a",
            border_spacing=0
        )
        self.guide_btn.grid(row=0, column=2, padx=(2, 0))
        Tooltip(self.guide_btn, t("prompt_master.tooltip_guide"))

        # Compact preset scrollable frame
        self.preset_scroll = ctk.CTkScrollableFrame(
            self.left_frame, 
            scrollbar_fg_color="transparent",
            scrollbar_button_color="#222",
            scrollbar_button_hover_color="#333"
        )
        self.preset_scroll.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")
        self.preset_scroll.grid_columnconfigure(0, weight=1) # Ensure buttons fill width

        # Center Panel: Split into Builder (top) + Tag Library (bottom)
        self.center_frame = ctk.CTkFrame(main_container, corner_radius=0, fg_color=THEME_BG)
        self.center_frame.grid(row=1, column=1, sticky="nsew")
        self.center_frame.grid_rowconfigure(0, weight=0, minsize=600)  # Builder: Fixed Height (600px)
        self.center_frame.grid_rowconfigure(1, weight=1)  # Tag Library: Variable (Fills remaining)
        self.center_frame.grid_columnconfigure(0, weight=1)

        # Custom Template section (Builder) - Slightly Brighter Card
        self.builder_frame = ctk.CTkFrame(self.center_frame, corner_radius=10, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        # Reduced padding for more compact look
        self.builder_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        
        # Inputs get priority (weight 3) and minsize to ensure width
        # Image gets weight 1 to shrink/grow, but inputs are "secured"
        self.builder_frame.grid_columnconfigure(0, weight=3, minsize=450)
        self.builder_frame.grid_columnconfigure(1, weight=1) 
        self.builder_frame.grid_rowconfigure(2, weight=1) # Row 2 (Inputs) is the scrollable content

        # Title (Row 0, Spans Full Width)
        self.builder_title = ctk.CTkLabel(
            self.builder_frame, 
            text=t("prompt_master.custom_template"), 
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w"
        )
        self.builder_title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(20, 5), pady=(15, 5))

        # Fixed Template Frame (Row 1, Spans Full Width) - Uses space above image
        self.fixed_template_frame = ctk.CTkFrame(self.builder_frame, fg_color="transparent")
        self.fixed_template_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(10, 5), pady=(0, 10))
        self.fixed_template_frame.grid_columnconfigure(0, weight=1)

        # Left: Input Scroll (Row 2, Col 0)
        self.input_scroll = ctk.CTkScrollableFrame(
            self.builder_frame, 
            fg_color="transparent",
            scrollbar_fg_color="transparent",
            scrollbar_button_color="#222",
            scrollbar_button_hover_color="#333"
        )
        self.input_scroll.grid(row=2, column=0, sticky="nsew", padx=(10, 5), pady=(0, 10))

        # Right: Image Panel (Row 2, Col 1) - Alongside Inputs
        self.image_panel = ctk.CTkFrame(self.builder_frame, fg_color="transparent", corner_radius=0)
        self.image_panel.grid(row=2, column=1, sticky="nsew", padx=(5, 10), pady=(0, 10))
        self.image_panel.grid_rowconfigure(0, weight=1)
        self.image_panel.grid_columnconfigure(0, weight=1)
        
        # Placeholder text for image panel
        self.image_placeholder = ctk.CTkLabel(self.image_panel, text="No Image", text_color="gray")
        self.image_placeholder.grid(row=0, column=0)

        # Tag Library section (bottom section) - Slightly Brighter Card
        self.tag_library_frame = ctk.CTkFrame(self.center_frame, corner_radius=10, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        self.tag_library_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.tag_library_frame.grid_rowconfigure(2, weight=1)  # Scrollable area (now row 2)
        self.tag_library_frame.grid_columnconfigure(0, weight=1)
        
        # Tag Library Header
        tag_header = ctk.CTkLabel(
            self.tag_library_frame,
            text=t("prompt_master.tag_library"),
            font=ctk.CTkFont(size=14, weight="bold")
        )
        tag_header.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        # Custom Prompt (User Context) - Persistent
        self.custom_input = ctk.CTkTextbox(self.tag_library_frame, height=50, fg_color=THEME_BG, border_width=1, border_color=THEME_BORDER)
        self.custom_input.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.custom_input.bind("<KeyRelease>", self.update_output)
        
        # Tag Library Content (populated by TagLibraryMixin)
        # Use regular Frame instead of ScrollableFrame to avoid nested scrollbars
        self.tag_library_scroll = ctk.CTkFrame(self.tag_library_frame, fg_color="transparent")
        self.tag_library_scroll.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # Output Panel (Right)
        self.right_frame = ctk.CTkFrame(main_container, corner_radius=0, fg_color="transparent")
        self.right_frame.grid(row=1, column=2, sticky="nsew", padx=(0, 20), pady=20)
        self.right_frame.grid_rowconfigure(0, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        # Output Display Container - Slightly Brighter Card
        self.output_container = ctk.CTkFrame(self.right_frame, corner_radius=10, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        self.output_container.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        # Output Text Widget (Centered inside container)
        self.output_text = ctk.CTkTextbox(
            self.output_container, 
            wrap="word",
            font=("", 20, "bold"),
            fg_color="transparent", # Transparent to blend with container
            height=300 
        )
        self.output_text.place(relx=0.5, rely=0.45, anchor="center", relwidth=0.9, relheight=0.8)
        
        self.output_text._textbox.configure(spacing1=5, spacing2=2, spacing3=5)
        self.output_text.tag_config("center", justify="center")

        # Action Buttons Overlay (Inside the black box, bottom right)
        self.action_overlay = ctk.CTkFrame(self.output_container, fg_color="transparent")
        self.action_overlay.place(relx=0.95, rely=0.95, anchor="se")

        # Optimize (Magic Wand)
        self.optimize_btn = ctk.CTkButton(
            self.action_overlay, 
            text="✨", 
            command=self.optimize_prompt, 
            width=35,
            height=35,
            corner_radius=8,
            anchor="center",
            fg_color=THEME_BTN_PRIMARY,
            hover_color=THEME_BTN_HOVER,
            font=ctk.CTkFont(size=16), # Adjusted size
            border_spacing=0 # Remove internal padding for perfect centering
        )
        self.optimize_btn.pack(side="right", padx=5)
        Tooltip(self.optimize_btn, t("prompt_master.tooltip_optimize"))
        
        # Copy (Clipboard)
        self.copy_btn = ctk.CTkButton(
            self.action_overlay, 
            text="📋", 
            command=self.copy_to_clipboard, 
            width=35,
            height=35,
            corner_radius=8,
            anchor="center",
            font=ctk.CTkFont(size=16),
            border_spacing=0
        )
        self.copy_btn.pack(side="right", padx=5)
        Tooltip(self.copy_btn, t("prompt_master.tooltip_copy"))

        # Clear (Trash)
        self.clear_btn = ctk.CTkButton(
            self.action_overlay, 
            text="🗑️", 
            command=self.clear_fields, 
            width=35,
            height=35,
            corner_radius=8,
            anchor="center",
            font=ctk.CTkFont(size=16),
            border_spacing=0
        )
        self.clear_btn.pack(side="right", padx=5)
        Tooltip(self.clear_btn, t("prompt_master.tooltip_clear"))

        # Initialization
        self.load_engines()
        self.build_tag_library_ui()

    def build_ui(self):
        """Build preset UI - Unified Grid Layout"""
        # Clear inputs
        for widget in self.input_scroll.winfo_children():
            widget.destroy()
        
        # Clear Fixed Template Frame
        for widget in self.fixed_template_frame.winfo_children():
            widget.destroy()
        
        # Configure Grid Columns for input_scroll
        # Col 0: Label (Auto width, right aligned)
        # Col 1: Input (Expands)
        # Col 2: Button (Fixed width)
        self.input_scroll.grid_columnconfigure(0, weight=0) 
        self.input_scroll.grid_columnconfigure(1, weight=1)
        self.input_scroll.grid_columnconfigure(2, weight=0)

        # Update Image Panel
        self.display_example_image()
        
        self.input_widgets = {}
        self.option_widgets = {}

        if not self.current_preset_data:
            # Update title if no preset
            self.builder_title.configure(text=t("prompt_master.select_preset"))
            return

        # Update Title
        title = self.current_preset_data.get("name", "Untitled")
        self.builder_title.configure(text=title)
        
        row = 0
        
        # Description
        desc = self.current_preset_data.get("description", "")
        if desc:
            ctk.CTkLabel(
                self.fixed_template_frame, 
                text=desc, 
                text_color="gray",
                font=ctk.CTkFont(size=11),
                wraplength=400,
                justify="left"
            ).grid(row=row, column=0, sticky="w", padx=10, pady=(0, 5))
            row += 1

        # Raw Prompt Template Display (Rich Text)
        template_text = self.current_preset_data.get("template", "")
        if template_text:
            # Container for the textbox
            template_frame = ctk.CTkFrame(self.fixed_template_frame, fg_color="transparent")
            template_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 5))
            template_frame.grid_columnconfigure(0, weight=1)

            # Read-only Textbox for rich text
            self.template_display = ctk.CTkTextbox(
                template_frame,
                height=120,
                fg_color="transparent",
                text_color="gray60",
                font=ctk.CTkFont(size=14),
                wrap="word",
                activate_scrollbars=True
            )
            self.template_display.grid(row=0, column=0, sticky="ew")
            
            # Parse and insert text with highlighting
            import re
            parts = re.split(r'(\{.*?\})', template_text)
            
            bold_font = ctk.CTkFont(size=14, weight="bold")
            self.template_display._textbox.tag_config("highlight", foreground="white", font=bold_font)
            self.template_display._textbox.tag_config("dim", foreground="gray60")
            
            for part in parts:
                if part.startswith("{") and part.endswith("}"):
                    self.template_display.insert("end", part, "highlight")
                else:
                    self.template_display.insert("end", part, "dim")
            
            self.template_display.configure(state="disabled") # Make read-only
            row += 1

        # Inputs - Unified Grid
        inputs = self.current_preset_data.get("inputs", [])
        if inputs:
            for inp in inputs:
                self.create_input_with_translate(self.input_scroll, inp, row)
                row += 1

        # Options - Unified Grid
        options = self.current_preset_data.get("options", [])
        if options:
            for opt in options:
                # Label (Right aligned)
                label = ctk.CTkLabel(self.input_scroll, text=f"{opt.get('label', opt['id'])}:", anchor="e")
                label.grid(row=row, column=0, sticky="e", padx=(10, 10), pady=2)
                
                # Combobox (Expands)
                combo = ctk.CTkComboBox(
                    self.input_scroll, 
                    values=opt.get("choices", []), 
                    command=self.update_output,
                    fg_color=THEME_BG,
                    border_color=THEME_BORDER,
                    button_color="#1a1a1a",
                    button_hover_color="#222"
                )
                combo.set(opt.get("default", ""))
                combo.grid(row=row, column=1, sticky="ew", pady=2)
                
                # Empty placeholder for button column to maintain grid structure if needed
                # or just leave it empty.
                
                self.option_widgets[opt["id"]] = combo
                row += 1


    def update_output(self, event=None):
        if not self.current_preset_data:
            return

        template = self.current_preset_data.get("template", "")
        
        for key, widget in self.input_widgets.items():
            val = widget.get()
            template = template.replace(f"{{{key}}}", val)
            
        for key, widget in self.option_widgets.items():
            val = widget.get()
            template = template.replace(f"{{{key}}}", val)
        
        custom_text = self.custom_input.get("0.0", "end").strip()
        if custom_text:
            template = f"{template}, {custom_text}"
            
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", template, "center")

    def copy_to_clipboard(self):
        self.clipboard_clear()
        self.clipboard_append(self.output_text.get("0.0", "end").strip())
        messagebox.showinfo(t("common.success"), t("prompt_master.copy_success"))

    def clear_fields(self):
        if messagebox.askyesno("Clear All", "Are you sure you want to clear all fields?\nThis will reset all inputs and options."):
            for widget in self.input_widgets.values():
                widget.delete(0, "end")
            # Custom Prompt is now persistent (User Context), so we don't clear it
            # self.custom_input.delete("0.0", "end")
            
            self.update_output()

    def optimize_prompt(self):
        prompt = self.output_text.get("0.0", "end").strip()
        if not prompt:
            return

        self.optimize_btn.configure(state="disabled", text=t("prompt_master.status_optimizing"))
        
        def run_optimization():
            try:
                response = requests.post('http://localhost:11434/api/generate', json={
                    "model": "llama3",
                    "prompt": f"Optimize this prompt:\n\n{prompt}",
                    "stream": False
                })
                if response.status_code == 200:
                    result = response.json().get("response", "")
                    self.output_text.delete("0.0", "end")
                    self.output_text.insert("0.0", result.strip(), "center")
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                self.optimize_btn.configure(state="normal", text="Optimize")

        threading.Thread(target=run_optimization, daemon=True).start()

def open_prompt_master(target_path=None):
    """Entry point"""
    app = PromptMasterApp()
    app.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        open_prompt_master(sys.argv[1])
    else:
        open_prompt_master()
