import os
import json
import subprocess
import customtkinter as ctk
from tkinter import messagebox
from ..constants import PRESETS_DIR, ENGINE_COLORS
from utils.gui_lib import THEME_BG, THEME_CARD, THEME_BORDER, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER

class PresetMixin:
    def load_engines(self):
        """Load engines and create tabs"""
        self.engines = []
        if os.path.exists(PRESETS_DIR):
            for item in os.listdir(PRESETS_DIR):
                if os.path.isdir(os.path.join(PRESETS_DIR, item)):
                    self.engines.append(item)
        
        if self.engines:
            # Create engine tabs
            for engine in self.engines:
                color = ENGINE_COLORS.get(engine, ("#1F6AA5", "#144870"))
                
                tab_btn = ctk.CTkButton(
                    self.tabs_frame,
                    text=engine,
                    command=lambda e=engine: self.on_engine_change(e),
                    width=100,
                    height=35,
                    fg_color="transparent",
                    border_width=1,
                    border_color=THEME_BORDER
                )
                tab_btn.pack(side="left", padx=2)
                self.engine_tabs[engine] = tab_btn
            
            # Select first engine
            self.on_engine_change(self.engines[0])

    def on_engine_change(self, choice):
        """Engine tab clicked"""
        self.current_engine = choice
        
        # Update tab colors
        if choice in ENGINE_COLORS:
            self.current_engine_color = ENGINE_COLORS[choice]
        else:
            self.current_engine_color = ("#1F6AA5", "#144870")
        
        # Update all tabs (deselect others, highlight selected)
        for engine, tab_btn in self.engine_tabs.items():
            if engine == choice:
                tab_btn.configure(
                    fg_color=self.current_engine_color[0],
                    border_color=self.current_engine_color[0],
                    text_color="white"
                )
            else:
                tab_btn.configure(
                    fg_color="transparent",
                    border_color=THEME_BORDER,
                    text_color="#666"
                )
        
        # Load presets
        self.load_presets(choice)

    def load_presets(self, engine):
        """Load presets for selected engine and cache data"""
        for widget in self.preset_scroll.winfo_children():
            widget.destroy()

        engine_path = os.path.join(PRESETS_DIR, engine)
        if not os.path.exists(engine_path):
            print(f"[PromptMaster] Engine path not found: {engine_path}")
            return

        self.preset_cache = [] # Cache for search: {filename, name, tags, template}
        first_preset_file = None
        
        # 1. Read all presets first to populate cache
        files = sorted(os.listdir(engine_path))
        print(f"[PromptMaster] Found {len(files)} files in {engine_path}")
        
        for filename in files:
            if filename.endswith(".json") and filename != "list.json":
                try:
                    filepath = os.path.join(engine_path, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    self.preset_cache.append({
                        "filename": filename,
                        "name": data.get("name", filename[:-5]),
                        "tags": data.get("tags", []), 
                        "template": data.get("template", "").lower()
                    })
                    
                    if first_preset_file is None:
                        first_preset_file = filename
                except Exception as e:
                    err_msg = f"Error loading preset {filename}: {e}"
                    print(f"[PromptMaster] {err_msg}")
                    # Optional: Show error to user if strictly needed, but might spam if many files fail
                    # messagebox.showerror("Preset Load Error", err_msg)

        # 2. Display all initially
        self.update_preset_list(self.preset_cache)
        
        if first_preset_file:
            self.load_preset_file(first_preset_file)

    def update_preset_list(self, items):
        """Update the preset list UI with given items"""
        for widget in self.preset_scroll.winfo_children():
            widget.destroy()
            
        # Re-add header if needed, or just list buttons
        # self.preset_header = ctk.CTkLabel(self.preset_scroll, text="Presets", anchor="w", font=ctk.CTkFont(size=13, weight="bold"))
        # self.preset_header.grid(row=0, column=0, padx=5, pady=(0, 5), sticky="w")
        
        row = 1
        for item in items:
            filename = item["filename"]
            preset_name = item["name"]
            
            btn = ctk.CTkButton(
                self.preset_scroll, 
                text=preset_name, 
                command=lambda f=filename: self.load_preset_file(f),
                anchor="w",
                height=26,
                fg_color=THEME_BG,
                hover_color=THEME_DROPDOWN_HOVER,
                border_width=1,
                border_color=THEME_BORDER
            )
            btn.grid(row=row, column=0, padx=1, pady=1, sticky="ew")
            row += 1

    def filter_presets(self, event=None):
        """Filter presets based on search query"""
        query = self.preset_search.get().lower().strip()
        
        if not query:
            self.update_preset_list(self.preset_cache)
            return
            
        filtered = []
        for item in self.preset_cache:
            # Search in Name
            if query in item["name"].lower():
                filtered.append(item)
                continue
                
            # Search in Tags (if list or string)
            tags = item["tags"]
            if isinstance(tags, list):
                if any(query in t.lower() for t in tags):
                    filtered.append(item)
                    continue
            elif isinstance(tags, str):
                if query in tags.lower():
                    filtered.append(item)
                    continue
                    
            # Search in Raw Prompt Template
            if query in item["template"]:
                filtered.append(item)
                continue
                
        self.update_preset_list(filtered)

    def load_preset_file(self, filename):
        filepath = os.path.join(PRESETS_DIR, self.current_engine, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.current_preset_data = json.load(f)
            self.current_preset_filename = filename # Store filename for saving
            self.build_ui()
            self.update_output()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load preset: {e}")

    def open_presets_folder(self):
        if self.current_engine:
            engine_path = os.path.join(PRESETS_DIR, self.current_engine)
            if os.path.exists(engine_path):
                subprocess.Popen(f'explorer "{engine_path}"')

    def show_add_guide(self):
        """Show preset guide"""
        guide_window = ctk.CTkToplevel(self)
        guide_window.title("Preset Guide")
        guide_window.geometry("700x800")
        
        title = ctk.CTkLabel(guide_window, text="📝 Preset Guide", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=20)
        
        scroll = ctk.CTkScrollableFrame(guide_window)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        guide_text = """
Create JSON in: config/prompt_master/presets/[engine]/

Template:
{
  "engine": "engine_name",
  "name": "Preset Name",
  "description": "Description",
  "example_image": "optional.png",
  "inputs": [
    {"id": "var", "label": "Label", "default": ""}
  ],
  "options": [
    {"id": "opt", "label": "Label", "choices": [...], "default": ""}
  ],
  "template": "Text with {var} and {opt}"
}
        """
        
        ctk.CTkLabel(scroll, text=guide_text, justify="left", anchor="w").pack(fill="both", padx=10, pady=10)
