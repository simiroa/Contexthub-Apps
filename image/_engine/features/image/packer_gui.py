"""
Texture Packer GUI - Pack ORM (Occlusion, Roughness, Metallic) textures and more.
Combines separate texture maps into a single RGB or RGBA image.
"""
import sys
import re
from pathlib import Path
import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import messagebox, filedialog
import threading
import numpy as np

try:
    import OpenEXR
    import Imath
    HAS_OPENEXR = True
except ImportError:
    HAS_OPENEXR = False

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/image -> src
sys.path.append(str(src_dir))

from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_BTN_DANGER, THEME_BTN_DANGER_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, THEME_TEXT_MAIN, THEME_TEXT_DIM
from utils.explorer import get_selection_from_explorer
from utils.i18n import t
from core.logger import setup_logger

logger = setup_logger("texture_packer")


PRESETS = {
    "Custom": ["Red", "Green", "Blue", "Alpha"],
    "ORM": ["Occlusion", "Roughness", "Metallic", ""],
    "ORM + Alpha": ["Occlusion", "Roughness", "Metallic", "Alpha"],
    "Unity Mask": ["Metallic", "Occlusion", "Detail", "Smoothness"],
    "Unreal ORM": ["Occlusion", "Roughness", "Metallic", ""]
}

# Mapping labels to search patterns
KEYWORD_PATTERNS = {
    "occlusion": ["*occlusion*", "*ao*", "*ambient*"],
    "roughness": ["*roughness*", "*rough*", "*gloss*"],
    "metallic": ["*metallic*", "*metal*", "*metalness*"],
    "smoothness": ["*smoothness*", "*smooth*"],
    "detail": ["*detail*", "*mask*"],
    "alpha": ["*alpha*", "*opacity*", "*transparent*"],
    "height": ["*height*", "*disp*"],
    "displacement": ["*displacement*", "*disp*"],
    "specular": ["*specular*", "*spec*"]
}

class TexturePackerGUI(BaseWindow):
    """GUI for packing textures into a single image (RGB/RGBA)."""
    
    def __init__(self, target_path=None, demo_mode=False):
        super().__init__(title=t("texture_packer_gui.title"), width=850, height=600, scrollable=False, icon_name="texture_packer")
        self.demo_mode = demo_mode
        
        self.target_path = Path(target_path) if target_path else None
        
        # Slots: 'r', 'g', 'b', 'a'
        self.slots = {
            "r": None,
            "g": None,
            "b": None,
            "a": None
        }
        
        # GUI Elements Storage
        self.previews = {}
        self.lbl_filenames = {}
        self.entry_labels = {}
        
        self.current_preset = ctk.StringVar(value="ORM")
        
        self.create_widgets()
        
        # Initialize with ORM preset
        self.apply_preset("ORM")
        
        # Auto-parse if target provided
        if self.target_path:
            self.auto_parse_textures()
            
        self.after(100, self.adjust_window_size)
    
    def create_widgets(self):
        # --- Header ---
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(header, text=t("texture_packer_gui.header"), font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        # Preset Selector
        preset_frame = ctk.CTkFrame(header, fg_color="transparent")
        preset_frame.pack(side="right")
        
        ctk.CTkLabel(preset_frame, text="Preset:", font=("", 12)).pack(side="left", padx=5)
        self.combo_preset = ctk.CTkComboBox(preset_frame, values=list(PRESETS.keys()), 
                                            variable=self.current_preset,
                                            command=self.apply_preset, width=120,
                                            fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, border_color=THEME_BORDER)
        self.combo_preset.pack(side="left")
        
        # --- Slots Frame ---
        slots_frame = ctk.CTkFrame(self.main_frame, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        slots_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Configure grid for 4 columns
        for i in range(4):
            slots_frame.grid_columnconfigure(i, weight=1)
        slots_frame.grid_rowconfigure(2, weight=1) # Preview row
        
        channels = [
            ("r", "Red Channel", "#FF6B6B"),
            ("g", "Green Channel", "#6BCB77"),
            ("b", "Blue Channel", "#4D96FF"),
            ("a", "Alpha Channel", "#9CA3AF")
        ]
        
        for col, (key, chan_name, color) in enumerate(channels):
            # 1. Channel Title
            lbl_title = ctk.CTkLabel(slots_frame, text=chan_name, font=ctk.CTkFont(size=11, weight="bold"), text_color=color)
            lbl_title.grid(row=0, column=col, pady=(10, 2))
            
            # 2. Editable Label (Map Type)
            entry_lbl = ctk.CTkEntry(slots_frame, justify="center", height=24, font=("", 12))
            entry_lbl.grid(row=1, column=col, padx=10, pady=(0, 10), sticky="ew")
            self.entry_labels[key] = entry_lbl
            
            # Bind entry change to switch preset to Custom (if not already)
            entry_lbl.bind("<KeyRelease>", lambda e: self.check_custom_preset())
            
            # 3. Preview Frame
            preview_frame = ctk.CTkFrame(slots_frame, fg_color=THEME_CARD) 
            preview_frame.grid(row=2, column=col, padx=10, pady=5, sticky="nsew")
            preview_frame.grid_propagate(False)
            
            # Preview Image/Text
            preview_label = ctk.CTkLabel(preview_frame, text="Drop or Load", 
                                         font=("", 11), text_color=THEME_TEXT_DIM)
            preview_label.place(relx=0.5, rely=0.5, anchor="center")
            self.previews[key] = preview_label
            
            # Enable drag and drop
            self._setup_drop_target(preview_frame, key)
            
            # 4. Filename Label
            fn_lbl = ctk.CTkLabel(slots_frame, text="", font=("", 10), text_color=THEME_TEXT_DIM, height=12)
            fn_lbl.grid(row=3, column=col, pady=(2, 0))
            self.lbl_filenames[key] = fn_lbl
            
            # 5. Load/Clear Buttons
            btn_frame = ctk.CTkFrame(slots_frame, fg_color="transparent")
            btn_frame.grid(row=4, column=col, pady=(5, 10))
            
            ctk.CTkButton(btn_frame, text="Load", width=60, height=24, font=ctk.CTkFont(size=11),
                         fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER,
                         command=lambda k=key: self.load_texture(k)).pack(side="left", padx=2)
            
            ctk.CTkButton(btn_frame, text="X", width=24, height=24, fg_color=THEME_BTN_DANGER_HOVER, hover_color=THEME_BTN_DANGER,
                         command=lambda k=key: self.clear_slot(k)).pack(side="left", padx=2)

        # --- Output Settings ---
        out_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        out_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(out_frame, text="Output Name:").pack(side="left", padx=5)
        self.entry_output = ctk.CTkEntry(out_frame, width=200)
        self.entry_output.pack(side="left", padx=5)
        self.entry_output.insert(0, "_Packed")
        
        ctk.CTkLabel(out_frame, text="Format:").pack(side="left", padx=(15, 5))
        self.var_format = ctk.StringVar(value=".png")
        
        formats = [".png", ".jpg", ".tga"]
        if HAS_OPENEXR: formats.append(".exr")
            
        ctk.CTkOptionMenu(out_frame, variable=self.var_format, values=formats, width=80).pack(side="left", padx=5)
        
        # Resize Controls
        self.var_resize_enabled = ctk.BooleanVar(value=False)
        self.chk_resize = ctk.CTkCheckBox(out_frame, text="Resize:", variable=self.var_resize_enabled, 
                                          command=self.toggle_resize_options, width=70)
        self.chk_resize.pack(side="left", padx=(15, 5))
        
        self.resize_var = ctk.StringVar(value="2048")
        self.opt_size = ctk.CTkOptionMenu(out_frame, variable=self.resize_var, 
                                          values=["512", "1024", "2048", "4096"], width=80, state="disabled")
        self.opt_size.pack(side="left", padx=5)
        
        # --- Action Buttons (Centralized Footer) ---
        ctk.CTkButton(self.footer_frame, text="Pack Textures", command=self.pack_textures, 
                      width=140, height=36, font=("", 13, "bold"),
                      fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER).pack(side="right", padx=5)
        
        ctk.CTkButton(self.footer_frame, text="Clear All", command=self.clear_all,
                      fg_color="transparent", border_width=1, border_color=THEME_BORDER, text_color=THEME_TEXT_DIM, width=100).pack(side="right", padx=5)
        
        ctk.CTkButton(self.footer_frame, text="Auto-Parse", command=self.auto_parse_textures, width=100,
                      fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER).pack(side="right", padx=5)

    def toggle_resize_options(self):
        """Enable/Disable resize dropdown."""
        if self.var_resize_enabled.get():
            self.opt_size.configure(state="normal")
        else:
            self.opt_size.configure(state="disabled")

    def apply_preset(self, choice):
        """Update labels based on preset."""
        labels = PRESETS.get(choice, PRESETS["Custom"])
        
        keys = ['r', 'g', 'b', 'a']
        for i, key in enumerate(keys):
            if i < len(labels):
                val = labels[i]
                self.entry_labels[key].delete(0, "end")
                self.entry_labels[key].insert(0, val)
                
                # Visual cue for unused slots?
                if not val:
                    self.entry_labels[key].configure(text_color="gray")
                else:
                    self.entry_labels[key].configure(text_color=("black", "white"))
    
    def check_custom_preset(self):
        """If user edits labels, switch combo to Custom."""
        if self.combo_preset.get() != "Custom":
            self.combo_preset.set("Custom")

    def _setup_drop_target(self, widget, slot_key):
        try:
            widget.drop_target_register("DND_Files")
            widget.dnd_bind("<<Drop>>", lambda e, k=slot_key: self._on_drop(e, k))
        except: pass
    
    def _on_drop(self, event, slot_key):
        try:
            files = self.tk.splitlist(event.data)
            if files:
                self.set_slot(slot_key, Path(files[0]))
        except Exception as e:
            logger.error(f"Drop error: {e}")

    def load_texture(self, slot_key):
        filetypes = [("Image files", "*.png *.jpg *.jpeg *.tga *.tif *.tiff *.exr"), ("All files", "*.*")]
        initial_dir = self.target_path.parent if self.target_path else None
        
        path = filedialog.askopenfilename(title=f"Select Texture", filetypes=filetypes, initialdir=initial_dir)
        if path:
            self.set_slot(slot_key, Path(path))
            
    def clear_slot(self, key):
        self.slots[key] = None
        self.previews[key].configure(text="Drop or Load", image=None)
        self.lbl_filenames[key].configure(text="")
        
    def set_slot(self, slot_key, path: Path):
        if not path.exists(): return
        
        self.slots[slot_key] = path
        
        # Update preview
        try:
            img = Image.open(path)
            img.thumbnail((160, 160), Image.Resampling.LANCZOS)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size) # Keep aspect ratio in thumbnail logic
            
            # Better fitting for preview
            # CTkImage size argument sets display size.
            disp_w, disp_h = img.size
            self.previews[slot_key].configure(image=photo, text="")
            self.previews[slot_key].image = photo
            self.lbl_filenames[slot_key].configure(text=path.name)
        except Exception as e:
            logger.warning(f"Preview failed: {e}")
            self.previews[slot_key].configure(text=path.name[:15]+"...", image=None)
            self.lbl_filenames[slot_key].configure(text=path.name)
        
        self._update_output_name()

    def _update_output_name(self):
        # ... (Similar to old logic but maybe simplified)
        loaded = [p for p in self.slots.values() if p]
        if not loaded: return
        
        # Find common prefix logic
        stems = [p.stem for p in loaded]
        if not stems: return
        
        s1 = min(stems)
        s2 = max(stems)
        common = s1
        for i, c in enumerate(s1):
            if c != s2[i]:
                common = s1[:i]
                break
        
        common = common.rstrip(" _-.")
        if not common: common = "Packed"
        
        # Suffix based on preset?
        suffix = "_Packed"
        preset = self.current_preset.get()
        if preset == "ORM": suffix = "_ORM"
        elif preset == "ORM + Alpha": suffix = "_ORM_Alpha"
        elif preset == "Unity Mask": suffix = "_MaskMap"
        
        self.entry_output.delete(0, "end")
        self.entry_output.insert(0, common + suffix)

    def auto_parse_textures(self):
        if not self.target_path: return
        
        search_dir = self.target_path.parent if self.target_path.is_file() else self.target_path
        base_name = self.target_path.stem if self.target_path.is_file() else ""
        
        # Clean base_name of potential common suffixes to widen search
        base_name = re.sub(r'_(occlusion|roughness|metallic|ao|rough|metal|orm|base|albedo|diffuse|nrm|normal|mask).*', 
                           '', base_name, flags=re.IGNORECASE)
        
        logger.info(f"Auto-parsing based on: {base_name}")
        
        img_exts = {'.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr'}
        
        keys = ['r', 'g', 'b', 'a']
        found_count = 0
        
        for key in keys:
            if self.slots[key]: continue # Skip if already loaded
            
            # Get label text to determine what to look for
            label_text = self.entry_labels[key].get().lower().strip()
            if not label_text: continue
            
            # Find matching patterns
            patterns = []
            for kw, pats in KEYWORD_PATTERNS.items():
                if kw in label_text:
                    patterns.extend(pats)
            
            # If no specific patterns found, try using the label itself as pattern
            if not patterns:
                patterns = [f"*{label_text}*"]
            
            # Search
            found_file = None
            for pattern in patterns:
                # Try with base_name prefix first
                matches = list(search_dir.glob(f"{base_name}{pattern}"))
                matches = [m for m in matches if m.suffix.lower() in img_exts]
                
                if not matches:
                    # Fallback: search just by pattern in folder (risky if multiple sets)
                    matches = list(search_dir.glob(pattern))
                    matches = [m for m in matches if m.suffix.lower() in img_exts]
                
                if matches:
                    found_file = matches[0]
                    break
            
            if found_file:
                self.set_slot(key, found_file)
                found_count += 1
        
        if found_count > 0:
            logger.info(f"Auto-parsed {found_count} textures")
        else:
            if not self.demo_mode:
                messagebox.showinfo("Info", "No matching textures found.")

    def clear_all(self):
        for key in self.slots:
            self.clear_slot(key)
        self.entry_output.delete(0, "end")

    def pack_textures(self):
        if not any(self.slots.values()):
            if not self.demo_mode: messagebox.showerror("Error", "No textures to pack.")
            return

        out_name = self.entry_output.get().strip() or "Packed"
        out_ext = self.var_format.get()
        
        def _process():
            try:
                # 1. Determine size
                size = None
                
                # Check Resize
                if self.var_resize_enabled.get():
                     s = int(self.resize_var.get())
                     size = (s, s)
                else:
                    # Find MAX size from all inputs
                    max_w, max_h = 0, 0
                    for p in self.slots.values():
                        if p:
                            with Image.open(p) as tmp:
                                w, h = tmp.size
                                if w > max_w: max_w = w
                                if h > max_h: max_h = h
                    
                    if max_w == 0: raise ValueError("Invalid texture size")
                    size = (max_w, max_h)
                
                # 2. Prepare channels
                channels = []
                keys = ['r', 'g', 'b', 'a']
                
                for key in keys:
                    path = self.slots[key]
                    label = self.entry_labels[key].get().strip()
                    
                    # Process image
                    if path:
                        with Image.open(path) as img:
                            gray = img.convert('L')
                            # Always resize to target 'size' (whether it's max or custom)
                            if gray.size != size:
                                gray = gray.resize(size, Image.Resampling.LANCZOS)
                            channels.append(gray)
                    else:
                        # ... (default value logic same as before)
                        lname = label.lower()
                        val = 0 # Default black
                        if "rough" in lname or "occlusion" in lname or "ao" in lname or "alpha" in lname or "opacity" in lname:
                            val = 255
                        
                        channels.append(Image.new('L', size, val))
                
                # 3. Merge
                has_alpha_input = (self.slots['a'] is not None)
                
                if has_alpha_input:
                    mode = 'RGBA'
                    final_channels = channels # R, G, B, A
                else:
                    mode = 'RGB'
                    final_channels = channels[:3] # R, G, B only
                
                result = Image.merge(mode, final_channels)
                
                # 4. Save
                out_dir = self.target_path.parent if self.target_path else Path.cwd()
                out_path = out_dir / f"{out_name}{out_ext}"
                
                if out_ext == ".exr":
                    if not HAS_OPENEXR:
                        raise ImportError("OpenEXR module not found. Cannot save EXR.")
                    
                    # Convert to EXR
                    # We have channels (R, G, B, [A])
                    # OpenEXR expects dictionary of bytes
                    
                    header = OpenEXR.Header(size[0], size[1])
                    header['compression'] = Imath.Compression(Imath.Compression.PIZ_COMPRESSION)
                    
                    # Define Channels
                    exr_channels = {}
                    
                    # Store Custom Names in Header Attributes
                    # e.g. "Channel_Name_R": "Occlusion"
                    
                    channel_map = {}
                    
                    # Prepare data
                    # final_channels has [R, G, B, (A)] images
                    
                    # Mapping standard output channels (R, G, B, A) to OpenEXR channels
                    # OpenEXR standard matches: R, G, B, A
                    output_keys = ['R', 'G', 'B', 'A'] if len(final_channels) == 4 else ['R', 'G', 'B']
                    
                    # Map input slots to output channels to get correct label
                    # But final_channels is a list.
                    # R came from slots['r'], G from slots['g'], etc.
                    # Unless we skipped one? No, we pack into standard RGB/RGBA.
                    
                    input_keys = ['r', 'g', 'b', 'a']
                    
                    failed_conversion = False
                    
                    for i, out_k in enumerate(output_keys):
                        # Add channel to Header
                        header['channels'][out_k] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
                        
                        # Add Metadata for what this channel represents
                        if i < len(input_keys):
                            in_k = input_keys[i]
                            label = self.entry_labels[in_k].get().strip()
                            if label:
                                # Add custom attribute
                                # OpenEXR attributes must be typed. StringAttribute.
                                header[f"ContextUp_Channel_{out_k}"] = label
                        
                        # Convert data
                        chan_img = final_channels[i]
                        # Convert to float32 numpy
                        arr = np.array(chan_img, dtype=np.float32) / 255.0
                        
                        exr_channels[out_k] = arr.tobytes()
                    
                    out = OpenEXR.OutputFile(str(out_path), header)
                    out.writePixels(exr_channels)
                    out.close()
                    
                else:
                    save_kwargs = {}
                    if out_ext in ['.jpg', '.jpeg']:
                        result = result.convert('RGB')
                        save_kwargs['quality'] = 95
                    
                    result.save(out_path, **save_kwargs)
                
                logger.info(f"Saved: {out_path}")
                if not self.demo_mode:
                    self.after(0, lambda: messagebox.showinfo("Success", f"Packed to {out_name}"))
                    # self.after(0, self.destroy) 
                
            except Exception as e:
                logger.error(f"Pack error: {e}")
                if not self.demo_mode:
                    self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=_process, daemon=True).start()

def run_texture_packer(target_path=None, demo_mode=False):
    app = TexturePackerGUI(target_path, demo_mode)
    app.mainloop()

if __name__ == "__main__":
    demo = "--demo" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--demo"]
    
    path = args[0] if args else None
    
    if path and not demo:
        # Prevent multiple instances
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("imp_packer", path, timeout=0.2) is None:
            sys.exit(0)
            
    run_texture_packer(path, demo)
