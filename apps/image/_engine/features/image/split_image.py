import customtkinter as ctk
from tkinter import messagebox, filedialog
from pathlib import Path
import sys
import threading
# import numpy as np # Moved to lazy loading in methods
from PIL import Image

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/image -> src
sys.path.append(str(src_dir))

from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, PremiumScrollableFrame
from utils.files import get_safe_path

# EXR Optional Import moved to lazy loading
HAS_EXR = True # Assume true for UI check, verified in methods


class ImageSplitGUI(BaseWindow):
    def __init__(self, target_file=None):
        super().__init__(title="Image Channel Splitter", width=540, height=680, icon_name="image_exr_split")
        
        self.file_list = [] # List of Path objects
        self.primary_file = None # The file used for channel configuration
        self.exr_header = None
        self.is_exr = False
        
        # Generic Image Data (for primary file)
        self.pil_image = None
        
        self.layer_map = {} # { "LayerName": [channels] } or { "Red": ["R"], ... }
        self.layer_vars = {} # layer_name -> BooleanVar
        self.suffix_vars = {} # layer_name -> StringVar (for suffix dropdown)
        self.invert_vars = {} # layer_name -> BooleanVar (for invert checkbox)
        
        self.preset_map = {
            "Standard": ["_Red", "_Green", "_Blue", "_Alpha"],
            "Unity MaskMap": ["_Metallic", "_Occlusion", "_Detail", "_Smoothness"],
            "Unreal ORM": ["_Occlusion", "_Roughness", "_Metallic", "_Specular"],
            "Texture Packing": ["_R", "_G", "_B", "_A"]
        }
        
        self.create_widgets()
        
        if target_file and Path(target_file).exists():
            self.add_files([Path(target_file)])
            
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # Main Layout: Top (Title), Middle (Files), Middle (Layers/Preset), Bottom (Output/Extract)
        
        # --- Bottom Section (Pack first to ensure visibility at the very bottom) ---
        footer = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=15, pady=(5, 12))
        
        # Row 1: Output Format + Status
        status_row = ctk.CTkFrame(footer, fg_color="transparent", height=28)
        status_row.pack(fill="x", pady=(0, 5))
        
        out_sel_frame = ctk.CTkFrame(status_row, fg_color="transparent")
        out_sel_frame.pack(side="right")
        ctk.CTkLabel(out_sel_frame, text="Format:", font=("Arial", 11, "bold")).pack(side="left", padx=(5, 2))
        self.format_var = ctk.StringVar(value="PNG")
        self.combo_format = ctk.CTkComboBox(out_sel_frame, variable=self.format_var, values=["PNG", "JPG", "TGA", "EXR"], width=65, height=24)
        self.combo_format.pack(side="left")

        self.lbl_status = ctk.CTkLabel(status_row, text="Ready", text_color="gray", font=("Arial", 11), anchor="w")
        self.lbl_status.pack(side="left")
        
        self.progress = ctk.CTkProgressBar(footer, height=4, width=150)
        self.progress.pack(fill="x", pady=(0, 10))
        self.progress.set(0)
        
        # Main Action Button
        self.btn_extract = ctk.CTkButton(footer, text="Extract Selected Channels", height=45, 
                                         font=("Arial", 14, "bold"), 
                                         fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER,
                                         command=self.extract_channels, state="disabled")
        self.btn_extract.pack(fill="x")

        # --- Top Section ---
        top_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=15, pady=(5, 1))
        
        ctk.CTkLabel(top_frame, text="Image Channel Splitter", font=("Arial", 16, "bold")).pack(side="left")

        # --- File Section ---
        file_card = ctk.CTkFrame(self.main_frame, fg_color=THEME_CARD, border_width=1, border_color=THEME_BORDER)
        file_card.pack(fill="x", padx=15, pady=(2, 2))
        
        # Toolbar for Files
        f_toolbar = ctk.CTkFrame(file_card, fg_color="transparent", height=24)
        f_toolbar.pack(fill="x", padx=10, pady=(4, 0))
        
        ctk.CTkLabel(f_toolbar, text="Input Files", font=("Arial", 11, "bold")).pack(side="left")
        
        ctk.CTkButton(f_toolbar, text="Clear", width=50, height=20, fg_color="transparent", border_width=1, font=("Arial", 10), command=self.clear_files).pack(side="right", padx=2)
        ctk.CTkButton(f_toolbar, text="+ Add", width=60, height=20, font=("Arial", 10), 
                     fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER,
                     command=self.browse_files).pack(side="right", padx=2)
        
        # File List Scroll
        self.scroll_files = PremiumScrollableFrame(file_card, height=50, fg_color="transparent")
        self.scroll_files.pack(fill="x", padx=5, pady=0)
        
        self.lbl_no_files = ctk.CTkLabel(self.scroll_files, text="Drag & Drop files here or click + Add", text_color="gray", font=("Arial", 11))
        self.lbl_no_files.pack(pady=2)
        
        # Info Row
        f_info_row = ctk.CTkFrame(file_card, fg_color="transparent", height=16)
        f_info_row.pack(fill="x", padx=10, pady=(0, 4))
        
        self.lbl_info = ctk.CTkLabel(f_info_row, text="No files loaded", text_color="gray", font=("Arial", 10), anchor="w")
        self.lbl_info.pack(side="left", fill="x", expand=True)

        # --- Table Configuration (Preset / Header) ---
        config_row = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        config_row.pack(fill="x", padx=15, pady=(5, 1))
        
        ctk.CTkLabel(config_row, text="Channels Configuration", font=("Arial", 12, "bold")).pack(side="left")
        
        # Preset
        preset_frame = ctk.CTkFrame(config_row, fg_color="transparent")
        preset_frame.pack(side="right")
        ctk.CTkLabel(preset_frame, text="Naming Preset:", font=("Arial", 11, "bold"), text_color="gray").pack(side="left", padx=(5, 2))
        self.preset_var = ctk.StringVar(value="Standard")
        self.combo_preset = ctk.CTkComboBox(preset_frame, variable=self.preset_var, values=list(self.preset_map.keys()), width=130, height=24, command=self.apply_preset)
        self.combo_preset.pack(side="left")

        # Table Header
        header_container = ctk.CTkFrame(self.main_frame, fg_color=THEME_CARD, height=32, corner_radius=2, border_width=1, border_color=THEME_BORDER)
        header_container.pack(fill="x", padx=15, pady=0)
        
        layer_header = ctk.CTkFrame(header_container, fg_color="transparent")
        layer_header.pack(fill="both", expand=True, padx=5)
        
        layer_header.grid_columnconfigure(0, weight=1)
        layer_header.grid_columnconfigure(1, weight=0, minsize=50)
        layer_header.grid_columnconfigure(2, weight=0, minsize=140)
        
        col0_frame = ctk.CTkFrame(layer_header, fg_color="transparent")
        col0_frame.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkLabel(col0_frame, text="Channel", font=("Arial", 11, "bold")).pack(side="left", padx=(5, 5))
        btn_all = ctk.CTkButton(col0_frame, text="All", width=30, height=18, font=("Arial", 9), fg_color="transparent", border_width=1, command=lambda: self.toggle_all_layers(True))
        btn_all.pack(side="left", padx=2)
        btn_none = ctk.CTkButton(col0_frame, text="None", width=35, height=18, font=("Arial", 9), fg_color="transparent", border_width=1, command=lambda: self.toggle_all_layers(False))
        btn_none.pack(side="left", padx=2)
        
        ctk.CTkLabel(layer_header, text="Inv", font=("Arial", 11, "bold")).grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkLabel(layer_header, text="Suffix", font=("Arial", 11, "bold"), anchor="w").grid(row=0, column=2, sticky="ew", padx=5)

        # Scrollable Area (The Table Body) - Pack last with expand=True
        self.scroll_layers = PremiumScrollableFrame(self.main_frame, height=180, fg_color="transparent")
        self.scroll_layers.pack(fill="both", expand=True, padx=15, pady=0)


    def browse_files(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=[("Image files", "*.exr *.png *.jpg *.jpeg *.tga *.bmp *.tif *.tiff"), ("All files", "*.*")]
        )
        if file_paths:
            paths = [Path(p) for p in file_paths]
            self.add_files(paths)

    def add_files(self, paths):
        valid_paths = [p for p in paths if p.exists()]
        if not valid_paths:
            return
            
        new_files = [p for p in valid_paths if p not in self.file_list]
        if not new_files:
            return
            
        self.file_list.extend(new_files)
        self.update_file_list_ui()
        
        # If this is the first file added (or we had no primary file), use it to setup config
        if self.primary_file is None:
            self.load_primary_file(self.file_list[0])

    def clear_files(self):
        self.file_list = []
        self.primary_file = None
        self.update_file_list_ui()
        # Clear layers
        self.update_layer_list([])
        self.lbl_info.configure(text="No files loaded")
        self.btn_extract.configure(state="disabled")

    def update_file_list_ui(self):
        for w in self.scroll_files.winfo_children():
            w.destroy()
            
        if not self.file_list:
            self.lbl_no_files = ctk.CTkLabel(self.scroll_files, text="Drag & Drop files here or click Add Files", text_color="gray", font=("Arial", 11))
            self.lbl_no_files.pack(pady=10)
            return
            
        for i, path in enumerate(self.file_list):
            f_row = ctk.CTkFrame(self.scroll_files, fg_color="transparent")
            f_row.pack(fill="x", pady=1)
            
            # Index or Bullet
            ctk.CTkLabel(f_row, text=f"{i+1}.", width=20, font=("Arial", 10)).pack(side="left")
            # Filename
            lbl = ctk.CTkLabel(f_row, text=path.name, anchor="w", font=("Arial", 11))
            lbl.pack(side="left", fill="x", expand=True)
            # Remove Button (Optional, can add later if requested - keeping simple for now)

    def load_primary_file(self, path):
        self.primary_file = path
        self.lbl_status.configure(text=f"Analyzing {path.name}...")
        self.btn_extract.configure(state="disabled")
        
        # Determine type
        suffix = path.suffix.lower()
        if suffix == ".exr":
            self.is_exr = True
            if not self._check_exr_available():
                self.update_status("Error: OpenEXR library not found")
                return
            self.format_var.set("EXR")
            threading.Thread(target=self._parse_exr_header, args=(path,), daemon=True).start()
        else:
            self.is_exr = False
            self.format_var.set("PNG")
            threading.Thread(target=self._parse_generic_image, args=(path,), daemon=True).start()

    def _check_exr_available(self):
        try:
            import OpenEXR
            import Imath
            return True
        except ImportError:
            return False


    def _parse_exr_header(self, path):
        try:
            import OpenEXR
            import Imath
            if not OpenEXR.isOpenExrFile(str(path)):
                self.update_status("Invalid EXR file")
                return

            exr_file = OpenEXR.InputFile(str(path))
            header = exr_file.header()
            self.exr_header = header
            
            # Extract channels
            channels = list(header['channels'].keys())
            
            # Group into layers
            self.layer_map = self._group_channels_to_layers(channels)
            
            # Update Info
            dw = header['dataWindow']
            w = dw.max.x - dw.min.x + 1
            h = dw.max.y - dw.min.y + 1
            
            info_text = f"Analyzed: {path.name} | Size: {w}x{h} | Layers: {len(self.layer_map)}"
            self.lbl_info.configure(text=info_text)
            
            # Update Layer List
            self.update_layer_list(sorted(self.layer_map.keys()))
            
            self.update_status(f"Ready ({len(self.file_list)} files)")
            self.btn_extract.configure(state="normal")
            
        except Exception as e:
            print(f"EXR Parse Error: {e}")
            self.update_status(f"Error: {str(e)}")

    def _parse_generic_image(self, path):
        try:
            img = Image.open(path)
            self.pil_image = img
            
            w, h = img.size
            mode = img.mode
            bands = img.getbands() # ('R', 'G', 'B', 'A') etc
            
            self.layer_map = {}
            for band in bands:
                # Map 'R' to 'Red', etc.
                name_map = {'R': 'Red', 'G': 'Green', 'B': 'Blue', 'A': 'Alpha', 'L': 'Gray', 'P': 'Palette'}
                layer_name = name_map.get(band, band)
                self.layer_map[layer_name] = [band] # Store the band key
                
            info_text = f"Analyzed: {path.name} | Size: {w}x{h} | Channels: {len(bands)}"
            self.lbl_info.configure(text=info_text)
            
            self.update_layer_list(sorted(self.layer_map.keys(), key=lambda x: {'Red':0, 'Green':1, 'Blue':2, 'Alpha':3, 'Gray':0}.get(x, 99)))
            
            self.update_status(f"Ready ({len(self.file_list)} files)")
            self.btn_extract.configure(state="normal")
            
        except Exception as e:
            print(f"Image Parse Error: {e}")
            self.update_status(f"Error: {str(e)}")

    def _group_channels_to_layers(self, channels):
        """
        Group channels by layer prefix (e.g., 'Diffuse.R' -> 'Diffuse')
        """
        layers = {}
        
        for chan in channels:
            parts = chan.split('.')
            if len(parts) > 1:
                # Has layer prefix
                layer_name = ".".join(parts[:-1])
            else:
                # Root channel (R, G, B, etc)
                layer_name = "Main"
                
            if layer_name not in layers:
                layers[layer_name] = []
            layers[layer_name].append(chan)
            
        return layers

    def update_layer_list(self, layer_names):
        for w in self.scroll_layers.winfo_children():
            w.destroy()
        self.layer_vars = {}
        self.suffix_vars = {}
        self.invert_vars = {}
        
        # Common Suffixes
        common_suffixes = ["_Red", "_Green", "_Blue", "_Alpha", "_Gray", "_R", "_G", "_B", "_A", "_Mask", "_Roughness", "_Metallic", "_Normal", "_Height", "_AO", "_Detail", "_Smoothness", "_Occlusion", "_Specular"]
        
        for i, layer in enumerate(layer_names):
            # Zebra striping
            row_color = THEME_CARD if i % 2 == 0 else "transparent"
            
            row_frame = ctk.CTkFrame(self.scroll_layers, fg_color=row_color, height=32, corner_radius=0)
            row_frame.pack(fill="x")
            
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=0, minsize=50)
            row_frame.grid_columnconfigure(2, weight=0, minsize=140)
            
            var = ctk.BooleanVar(value=True)
            self.layer_vars[layer] = var
            
            # Label Text
            if self.is_exr:
                ch_count = len(self.layer_map[layer])
                ch_names = ", ".join([c.split('.')[-1] for c in self.layer_map[layer][:4]])
                if ch_count > 4:
                    ch_names += "..."
                display_text = f"{layer} ({ch_count} ch: {ch_names})"
                default_suffix = f"_{layer.replace('/', '_')}" # Default to layer name
            else:
                display_text = layer
                # Smart Default
                default_suffix = f"_{layer}"
            
            # Checkbox (Column 0)
            chk = ctk.CTkCheckBox(row_frame, text=display_text, variable=var, font=("Arial", 11), border_width=1)
            chk.grid(row=0, column=0, sticky="w", padx=10, pady=4)
            
            # Invert Checkbox (Column 1)
            inv_var = ctk.BooleanVar(value=False)
            self.invert_vars[layer] = inv_var
            chk_inv = ctk.CTkCheckBox(row_frame, text="", variable=inv_var, width=20, height=20)
            chk_inv.grid(row=0, column=1, padx=5, pady=4)

            # Suffix Dropdown (Column 2)
            suffix_var = ctk.StringVar(value=default_suffix)
            self.suffix_vars[layer] = suffix_var
            
            opts = list(common_suffixes)
            if default_suffix not in opts:
                opts.insert(0, default_suffix)
                
            combo = ctk.CTkComboBox(row_frame, variable=suffix_var, values=opts, width=130, height=24)
            combo.grid(row=0, column=2, sticky="e", padx=5, pady=4)

    def apply_preset(self, choice):
        if choice not in self.preset_map:
            return
            
        suffixes = self.preset_map[choice]
        # Order: R, G, B, A (or generic order)
        # We try to map the first 4 generic layers or known layers
        
        # Generic Mapping
        target_keys = ["Red", "Green", "Blue", "Alpha"]
        
        for idx, key in enumerate(target_keys):
            if idx < len(suffixes):
                if key in self.suffix_vars:
                    # Generic Image Case
                    self.suffix_vars[key].set(suffixes[idx])
                else:
                    # EXR Case or partial image
                    # For EXR we usually don't have Red/Green/Blue keys unless it is a generic import
                    # But if the layer list matches order, we could try
                    pass

    def toggle_all_layers(self, state):
        for var in self.layer_vars.values():
            var.set(state)

    def extract_channels(self):
        if not self.file_list:
            return
        threading.Thread(target=self.run_extraction, daemon=True).start()

    def run_extraction(self):
        try:
            self.update_status("Preparing batch...")
            self.after(0, lambda: self.btn_extract.configure(state="disabled"))
            
            selected_layers = [l for l, v in self.layer_vars.items() if v.get()]
            if not selected_layers:
                self.update_status("No layers selected")
                self.after(0, lambda: self.btn_extract.configure(state="normal"))
                return
            
            out_format = self.format_var.get().lower()
            
            total_files = len(self.file_list)
            
            for f_idx, f_path in enumerate(self.file_list):
                self.update_status(f"Processing {f_idx+1}/{total_files}: {f_path.name}")
                
                # Check for Stop? (Skipping cancellation for now for simplicity)
                
                # Setup Output Dir
                out_dir = f_path.parent / f"{f_path.stem}_split"
                out_dir.mkdir(exist_ok=True)
                
                # For each file, we need to extract the configured layers.
                # If generic, we open it. If EXR, we open it.
                # Note: 'self.exr_header' and 'self.pil_image' are ONLY for the primary file (display purposes).
                # We must re-open each file here to process it.
                
                try:
                    if f_path.suffix.lower() == ".exr":
                         self._extract_exr_file(f_path, selected_layers, out_dir, out_format)
                    else:
                         self._extract_generic_file(f_path, selected_layers, out_dir, out_format)
                except Exception as e:
                    print(f"Failed to process {f_path.name}: {e}")
                    # Continue to next file?
                    
                self.after(0, lambda v=(f_idx + 1) / total_files: self.progress.set(v))
            
            self.after(0, lambda: self.progress.set(1.0))
            self.update_status("Batch Complete!")
            self.after(0, lambda: self.btn_extract.configure(state="normal"))
            self.after(0, lambda: messagebox.showinfo("Success", f"Processed {total_files} files."))
            
        except Exception as e:
            print(f"Extraction Error: {e}")
            self.update_status(f"Error: {str(e)}")
            self.after(0, lambda: self.btn_extract.configure(state="normal"))
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _get_out_filename(self, file_path, layer_name):
        suffix = self.suffix_vars.get(layer_name, ctk.StringVar(value=f"_{layer_name}")).get()
        # Clean suffix
        if not suffix.startswith("_") and not suffix.startswith("-"):
           suffix = "_" + suffix
           
        return f"{file_path.stem}{suffix}"

    def _extract_exr_file(self, file_path, selected_layers, out_dir, out_format):
        import OpenEXR
        import Imath
        import numpy as np
        # Local open for extraction
        exr_file = OpenEXR.InputFile(str(file_path))
        header = exr_file.header()
        dw = header['dataWindow']
        w = dw.max.x - dw.min.x + 1
        h = dw.max.y - dw.min.y + 1
        
        # We need to map 'LayerName' to channels for THIS file.
        # Ideally, strict mode: layers must exist. 
        # Or loose mode: look for matching channels.
        # Since we use 'self.layer_map' which is from primary file, we need a way to find channels in THIS file.
        # We'll re-parse channels for this file.
        
        f_channels = list(header['channels'].keys())
        f_layer_map = self._group_channels_to_layers(f_channels)
        
        for layer_name in selected_layers:
            if layer_name not in f_layer_map:
                print(f"Skipping {layer_name} in {file_path.name} (not found)")
                continue
                
            channels = f_layer_map[layer_name]
            do_invert = self.invert_vars[layer_name].get()
            
            # Sort channels (R, G, B, A order)
            def chan_sort_key(name):
                suffix = name.split('.')[-1]
                order = {'R':0, 'G':1, 'B':2, 'A':3, 'X':0, 'Y':1, 'Z':2}
                return order.get(suffix, 99)
                
            sorted_chans = sorted(channels, key=chan_sort_key)
            
            pt = Imath.PixelType(Imath.PixelType.FLOAT)
            bytes_list = exr_file.channels(sorted_chans, pt)
            
            base_name = self._get_out_filename(file_path, layer_name)
            
            # Save Logic
            if out_format == "exr":
                new_header = OpenEXR.Header(w, h)
                chan_data = {}
                for i, old_name in enumerate(sorted_chans):
                    parts = old_name.split('.')
                    simple_name = parts[-1] if len(parts) > 1 else old_name
                    new_header['channels'][simple_name] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
                    chan_data[simple_name] = bytes_list[i]
                    
                out = OpenEXR.OutputFile(str(out_dir / f"{base_name}.exr"), new_header)
                out.writePixels(chan_data)
                out.close()
            else:
                arrays = []
                for b in bytes_list:
                    arr = np.frombuffer(b, dtype=np.float32)
                    arr = arr.reshape(h, w)
                    arrays.append(arr)
                
                if len(arrays) == 1:
                    img = arrays[0]
                elif len(arrays) >= 3:
                    img = np.dstack(arrays[:3])
                else:
                    img = np.dstack([arrays[0], arrays[1], np.zeros_like(arrays[0])])
                    
                if do_invert:
                    img = 1.0 - img
                    
                img = np.nan_to_num(img)
                img = np.power(np.clip(img, 0, 1), 1/2.2) * 255
                img = img.astype(np.uint8)
                
                pil_img = Image.fromarray(img)
                pil_img.save(out_dir / f"{base_name}.{out_format}")

    def _extract_generic_file(self, file_path, selected_layers, out_dir, out_format):
        img = Image.open(file_path)
        img.load() # Ensure loaded
        
        # Generic Mapping (R -> Red, etc)
        # We need to see which bands adhere to selected layers.
        # self.layer_map (from primary) maps "Red" -> ["R"].
        # If this file has "R", we extract it.
        
        # Bands in this file
        f_bands = img.split()
        f_band_names = img.getbands()
        f_band_dict = {name: band for name, band in zip(f_band_names, f_bands)}
        
        for layer_name in selected_layers:
            # We need the 'target_bands' e.g. ["R"] for "Red"
            # But we must look it up in self.layer_map?
            # self.layer_map logic: {'Red': ['R'], 'Green': ['G']}
            # We trust self.layer_map provides the correct band key 'R' for the layer 'Red'.
            
            target_bands_keys = self.layer_map.get(layer_name)
            if not target_bands_keys:
                continue
                
            base_name = self._get_out_filename(file_path, layer_name)
            do_invert = self.invert_vars[layer_name].get()
            
            # We only support single channel extraction for generic images here based on current logic
            # (Red, Green, Blue, Alpha)
             
            # Take the first key (e.g. 'R')
            band_key = target_bands_keys[0]
            
            if band_key in f_band_dict:
                band_img = f_band_dict[band_key]
                if do_invert:
                    band_img = Image.eval(band_img, lambda x: 255 - x)
                
                # If asking to save as same format, great.
                # Note: Some formats like TGA usually expect RGB. 
                # Saving single channel as PNG/JPG is fine (Grayscale).
                
                save_path = out_dir / f"{base_name}.{out_format}"
                band_img.save(save_path)


    def update_status(self, text):
        self.after(0, lambda: self.lbl_status.configure(text=text))

    def on_closing(self):
        self.destroy()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        app = ImageSplitGUI(sys.argv[1])
    else:
        app = ImageSplitGUI()
    app.mainloop()
