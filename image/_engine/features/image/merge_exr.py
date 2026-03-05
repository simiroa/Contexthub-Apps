import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import sys
import threading
# Heavy imports moved to lazy loading inside export_exr
# import cv2
# import numpy as np
# import imageio
# from PIL import Image, ImageTk
# import OpenEXR
# import Imath
from PIL import Image, ImageTk

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/image -> src
sys.path.append(str(src_dir))

from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, THEME_TEXT_DIM
from utils.files import get_safe_path
from utils.image_utils import scan_for_images

# Strict Column Width Configuration - TIGHTER AND TUNED
COL_CONFIG = {
    0: {"width": 30, "weight": 0},   # Check
    1: {"width": 150, "weight": 1},  # Source File (Flexible)
    2: {"width": 25, "weight": 0},   # Arrow
    3: {"width": 150, "weight": 1},  # Target Name (Flexible)
    4: {"width": 75, "weight": 0},   # Mode
    5: {"width": 110, "weight": 0},  # Options
    6: {"width": 35, "weight": 0}    # Del
}

class ChannelRow(ctk.CTkFrame):
    def __init__(self, parent, source_file, file_options, onDelete, index):
        super().__init__(parent, corner_radius=6)  # Use theme default
        self.pack(fill="x", pady=2, padx=0) # Removed padx to align with header
        
        self.source_file = source_file
        self.file_options = file_options
        self.onDelete = onDelete
        self.index = index
        
        # Apply Strict Column Widths
        for col, cfg in COL_CONFIG.items():
            self.grid_columnconfigure(col, minsize=cfg["width"], weight=cfg["weight"])
            
        # Col 0: Checkbox
        self.var_include = ctk.BooleanVar(value=True)
        self.chk_include = ctk.CTkCheckBox(self, text="", variable=self.var_include, width=20, height=20, border_width=2, command=self.on_toggle)
        self.chk_include.grid(row=0, column=0, padx=2, pady=5)
        
        # Col 1: Source File (STRICT CONTAINER)
        # Use weight=1 in frame to extend
        self.frame_source = ctk.CTkFrame(self, height=28, fg_color="transparent")
        self.frame_source.grid(row=0, column=1, padx=2, sticky="ew") # Sticky EW
        self.frame_source.pack_propagate(False) 
        self.frame_source.grid_propagate(False)
        
        if source_file:
            disp_name = source_file
            if len(disp_name) > 35: disp_name = "..." + disp_name[-32:]
            self.lbl_source = ctk.CTkLabel(self.frame_source, text=disp_name, anchor="w", font=("", 12))
            self.lbl_source.pack(fill="both", expand=True, side="left")
            self.var_file = ctk.StringVar(value=source_file)
        else:
            self.var_file = ctk.StringVar(value="(None)")
            self.opt_file = ctk.CTkOptionMenu(self.frame_source, variable=self.var_file, values=["(Choose File)"] + file_options, 
                                              height=24, dynamic_resizing=False,
                                              fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER)
            self.opt_file.pack(fill="x",  pady=2)

        # Col 2: Arrow
        ctk.CTkLabel(self, text="➜", text_color=THEME_TEXT_DIM, width=COL_CONFIG[2]["width"]).grid(row=0, column=165)

        # Col 3: Target Layer Name
        self.entry_name = ctk.CTkEntry(self, placeholder_text="Layer Name", height=28)
        self.entry_name.grid(row=0, column=3, padx=5, sticky="ew") # Sticky EW
        
        # Col 4: Mode
        self.var_comp = ctk.StringVar(value="RGB") 
        self.opt_comp = ctk.CTkOptionMenu(self, variable=self.var_comp, values=["RGB", "RGBA", "R", "G", "B", "A", "L"], 
                                          width=COL_CONFIG[4]["width"]-5, height=24,
                                          fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER)
        self.opt_comp.grid(row=0, column=4, padx=2, sticky="ew")
        
        # Col 5: Options
        sub_opts = ctk.CTkFrame(self, fg_color="transparent", width=COL_CONFIG[5]["width"], height=28)
        sub_opts.grid(row=0, column=5, padx=2)
        sub_opts.pack_propagate(False) 
        
        self.chk_invert = ctk.CTkCheckBox(sub_opts, text="Inv", width=45, checkbox_width=16, checkbox_height=16, font=("", 11), border_width=2)
        self.chk_invert.pack(side="left", padx=2)
        self.chk_linear = ctk.CTkCheckBox(sub_opts, text="Lin", width=45, checkbox_width=16, checkbox_height=16, font=("", 11), border_width=2)
        self.chk_linear.pack(side="left", padx=2)
        
        # Col 6: Delete
        self.btn_del = ctk.CTkButton(self, text="×", width=24, height=24, fg_color="transparent", text_color="#e74c3c", hover_color="#333", command=lambda: onDelete(self))
        self.btn_del.grid(row=0, column=6, padx=2)

        self.on_toggle()

    def on_toggle(self):
        color = "white" if self.var_include.get() else THEME_TEXT_DIM
        if hasattr(self, 'lbl_source'): self.lbl_source.configure(text_color=color)

    def get_config(self):
        if not self.var_include.get(): return None
        return {
            "name": self.entry_name.get().strip(),
            "comp": self.var_comp.get(),
            "file": self.var_file.get(),
            "invert": self.chk_invert.get(),
            "linear": self.chk_linear.get()
        }
        
    def set_values(self, name, mode):
        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, name)
        self.var_comp.set(mode)

from utils.i18n import t

from core.config import MenuConfig

class ExrChannelPackerGUI(BaseWindow):
    def __init__(self, files_list):
        # Sync Name
        self.tool_name = "ContextUp EXR Manager"
        try:
             config = MenuConfig()
             item = config.get_item_by_id("merge_to_exr")
             if item: self.tool_name = item.get("name", self.tool_name)
        except: pass

        super().__init__(title=self.tool_name, width=900, height=500, scrollable=False, icon_name="image_exr_merge")
        
        self.files, _ = scan_for_images(files_list)
        self.file_names = [f.name for f in self.files] if self.files else []
        self.channel_rows = []
        
        self.create_widgets()
        
        if self.files:
            self.run_auto_create()
            
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1) 
        
        # 1. Top Header
        top_header = ctk.CTkFrame(self.main_frame, height=50, fg_color="transparent")
        top_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(15, 5))
        
        ctk.CTkLabel(top_header, text=self.tool_name, font=("", 18, "bold")).pack(side="left")
        ctk.CTkButton(top_header, text=t("merge_exr.add_custom"), width=120, height=30, command=lambda: self.add_channel(None),
                      fg_color="transparent", border_width=1, border_color=THEME_BORDER).pack(side="right")

        # 2. Table Header Bar
        table_header = ctk.CTkFrame(self.main_frame, height=32, corner_radius=6)  # Use theme default
        table_header.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 0)) # Fixed padx=10 matching body
        
        
        for col, cfg in COL_CONFIG.items():
            table_header.grid_columnconfigure(col, minsize=cfg["width"], weight=cfg["weight"])

        # Labels - SAME PADDING AS ROWS (padx=2)
        ctk.CTkLabel(table_header, text=t("merge_exr.col_use"), text_color=THEME_TEXT_DIM, font=("", 11)).grid(row=0, column=0, padx=2)
        ctk.CTkLabel(table_header, text=t("merge_exr.col_source"), anchor="w", text_color=THEME_TEXT_DIM, font=("", 11)).grid(row=0, column=1, padx=2, sticky="ew")
        ctk.CTkLabel(table_header, text="", width=20).grid(row=0, column=2)
        ctk.CTkLabel(table_header, text=t("merge_exr.col_target"), anchor="w", text_color=THEME_TEXT_DIM, font=("", 11)).grid(row=0, column=3, padx=5, sticky="ew")
        ctk.CTkLabel(table_header, text=t("merge_exr.col_mode"), text_color=THEME_TEXT_DIM, font=("", 11)).grid(row=0, column=4, padx=2)
        ctk.CTkLabel(table_header, text=t("merge_exr.col_options"), text_color=THEME_TEXT_DIM, font=("", 11)).grid(row=0, column=5, padx=2)
        ctk.CTkLabel(table_header, text=t("merge_exr.col_del"), text_color=THEME_TEXT_DIM, font=("", 11)).grid(row=0, column=6, padx=2)

        # 3. Scroll Area
        self.channel_scroll = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
        # Fix padding to match header. Header has padx=10. Scrollframe needs identical visual offset.
        # Inside scroll, ChannelRow has padx=2.
        # Inside header, Label has padx=2.
        # So we just need ScrollFrame to be padx=10 to match Header Frame padx=10.
        # BUT ScrollFrame adds its own borders/scrollbar.
        # Let's try padx=8 to be slightly tighter or just padx=10.
        self.channel_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=2) 

        # 4. Footer
        self.footer = ctk.CTkFrame(self.main_frame, height=70, fg_color="transparent")
        self.footer.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        
        self.progress = ctk.CTkProgressBar(self.footer, height=6)
        self.progress.pack(fill="x", pady=(0, 10))
        self.progress.set(0)
        
        self.btn_export = ctk.CTkButton(self.footer, text=t("merge_exr.export_btn"), 
                                        height=45, font=("", 15, "bold"), 
                                        fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER,
                                        command=self.start_export)
        self.btn_export.pack(fill="x")
        
        self.lbl_status = ctk.CTkLabel(self.footer, text=t("merge_exr.ready"), text_color=THEME_TEXT_DIM, font=("", 11))
        self.lbl_status.pack(pady=(2, 0))

    def add_channel(self, source_filename):
        # If None, ask user to select files (Multi-select)
        if source_filename is None:
            files = filedialog.askopenfilenames(title="Select Images to Add")
            if not files: return
            for f_path in files:
                self._create_channel_row(f_path)
        else:
            self._create_channel_row(source_filename)

    def _create_channel_row(self, source_filename):
        idx = len(self.channel_rows)
        row = ChannelRow(self.channel_scroll, source_filename, self.file_names, self.remove_channel, idx)
        if source_filename:
            # Guess Logic - Re-evaled in auto_create, but good for single add
            f_lower = source_filename.lower()
            mode = "RGB"
            if any(x in f_lower for x in ["_ao", "ambient", "occlusion", "roughness", "_rough", "metallic", "_mask", "_alpha", "opacity", "_gray"]):
                mode = "L"
            
            clean_name = Path(source_filename).stem
            row.set_values(clean_name, mode)
            
        self.channel_rows.append(row)

    def remove_channel(self, row_widget):
        row_widget.destroy()
        if row_widget in self.channel_rows:
            self.channel_rows.remove(row_widget)

    def run_auto_create(self):
        for r in self.channel_rows: r.destroy()
        self.channel_rows.clear()
        
        # 1. Determine Common Prefix to strip
        import os
        all_stems = [f.stem for f in self.files]
        if not all_stems: return
        
        common_prefix = os.path.commonprefix(all_stems)
        # Refine prefix: must be at least 3 chars or significant? 
        # Also, check if it breaks words (e.g. "Space" from "Spaceship"). 
        # Safest is to just strip if it ends in delimiter like "_" or " ".
        # Or just strip it regardless as user requested "exclude common part".
        
        # Avoid stripping everything if prefix == full name (e.g. duplicate files?)
        if len(common_prefix) > 2 and len(common_prefix) < len(all_stems[0]):
             pass # Use it
        else:
             common_prefix = ""

        for f in self.files:
            idx = len(self.channel_rows)
            row = ChannelRow(self.channel_scroll, f.name, self.file_names, self.remove_channel, idx)
            
            # Predict Mode
            f_lower = f.name.lower()
            mode = "RGB"
            if any(x in f_lower for x in ["_ao", "ambient", "occlusion", "roughness", "_rough", "metallic", "_mask", "_alpha", "opacity", "_gray"]):
                mode = "L"
            
            # Predict Name (Strip Common Prefix)
            name_cand = f.stem
            if common_prefix and name_cand.startswith(common_prefix):
                name_cand = name_cand[len(common_prefix):]
            
            # Cleanup leading underscores if left
            name_cand = name_cand.lstrip("_-. ")
            if not name_cand: name_cand = f.stem 
            
            row.set_values(name_cand, mode)
            self.channel_rows.append(row)
            
        self.lbl_status.configure(text=f"Loaded {len(self.files)} files. (Prefix Removed: '{common_prefix}')")

    def start_export(self):
        threading.Thread(target=self.export_exr, daemon=True).start()

    def export_exr(self):
        import cv2
        import numpy as np
        import imageio
        import OpenEXR
        import Imath
        
        try:
            self.progress.set(0)
            configs = [r.get_config() for r in self.channel_rows]
            
            active_configs = [c for c in configs if c['file'] != "(None)"]
            if not active_configs:
                messagebox.showwarning(t("common.warning"), "No layers have assigned files.")
                return

            self.update_status(t("merge_exr.loading"))
            
            # Resolve Paths logic
            def resolve_path(filename):
                if not filename or filename == "(None)": return None
                p = Path(filename)
                if p.is_file(): return p
                # Try in self.files
                match = next((f for f in self.files if f.name == filename), None)
                return match

            first_file_path = resolve_path(active_configs[0]['file'])
            if not first_file_path:
                messagebox.showerror("Error", f"Could not find file: {active_configs[0]['file']}")
                return

            ref_img = imageio.imread(first_file_path)
            h, w = ref_img.shape[:2]
            
            # Prepare Layers
            # We will flatten all layers into a dictionary of plane_name -> float32_array
            # e.g. "Diffuse.R": array, "Diffuse.G": array...
            
            final_planes = {}
            
            for i, cfg in enumerate(active_configs):
                self.update_status(t("merge_exr.processing").format(cfg['name']))
                
                f_path = resolve_path(cfg['file'])
                if not f_path: continue
                src = imageio.imread(f_path)
                
                if src.shape[:2] != (h, w):
                     src = cv2.resize(src, (w, h), interpolation=cv2.INTER_LINEAR)
                
                # Normalize & Process
                data = src.astype(np.float32)
                if src.dtype == np.uint8: data /= 255.0
                elif src.dtype == np.uint16: data /= 65535.0
                
                if cfg['linear']: data = np.power(np.maximum(data, 0), 2.2)
                if cfg['invert']: data = 1.0 - data
                
                # Map to Planes
                layer_name = cfg['name']
                mode = cfg['comp']
                
                # Input channels
                src_channels = 1 if len(data.shape) == 2 else data.shape[2]
                
                if mode == "RGB":
                    # Expect RGB input. If 1 channel, duplicate.
                    if src_channels == 1:
                        final_planes[f"{layer_name}.R"] = data
                        final_planes[f"{layer_name}.G"] = data
                        final_planes[f"{layer_name}.B"] = data
                    else:
                        final_planes[f"{layer_name}.R"] = data[:,:,0]
                        final_planes[f"{layer_name}.G"] = data[:,:,1] if src_channels > 1 else data[:,:,0]
                        final_planes[f"{layer_name}.B"] = data[:,:,2] if src_channels > 2 else data[:,:,0]
                        
                elif mode == "RGBA":
                    if src_channels == 1:
                        final_planes[f"{layer_name}.R"] = data
                        final_planes[f"{layer_name}.G"] = data
                        final_planes[f"{layer_name}.B"] = data
                        final_planes[f"{layer_name}.A"] = np.ones((h,w), dtype=np.float32)
                    else:
                        final_planes[f"{layer_name}.R"] = data[:,:,0]
                        final_planes[f"{layer_name}.G"] = data[:,:,1] if src_channels > 1 else data[:,:,0]
                        final_planes[f"{layer_name}.B"] = data[:,:,2] if src_channels > 2 else data[:,:,0]
                        final_planes[f"{layer_name}.A"] = data[:,:,3] if src_channels > 3 else np.ones((h,w), dtype=np.float32)
                        
                elif mode == "L":
                    # Luminance
                    if src_channels >= 3:
                        lum = 0.299*data[:,:,0] + 0.587*data[:,:,1] + 0.114*data[:,:,2]
                        final_planes[layer_name] = lum
                    elif src_channels == 1:
                        final_planes[layer_name] = data
                    else:
                        final_planes[layer_name] = data[:,:,0]
                        
                elif mode in ["R", "G", "B", "A"]:
                    # Specific source channel to Specific Output Channel Name?
                    # If user chose "R", do they mean "Extract R from source and call it 'LayerName'"? YES.
                    idx = {'R':0, 'G':1, 'B':2, 'A':3}.get(mode, 0)
                    if src_channels > idx:
                        plane = data[:,:,idx]
                    else:
                        plane = data if src_channels==1 else data[:,:,0]
                    final_planes[layer_name] = plane
                    
                self.progress.set((i+1) / len(active_configs))

            # WRITE using OpenEXR directly for proper channel naming
            sorted_keys = sorted(final_planes.keys())
            height, width = h, w
            
            header = OpenEXR.Header(width, height)
            header['compression'] = Imath.Compression(Imath.Compression.PIZ_COMPRESSION)
            
            # Add channels to header and prepare data
            exr_channel_data = {}
            for key in sorted_keys:
                # Add channel definition
                header['channels'][key] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
                # Prepare data
                exr_channel_data[key] = final_planes[key].tobytes()
            
            # Determine Output Path
            output_dir = first_file_path.parent
            out_name = output_dir / "MultiLayer_Output.exr"
            
            self.update_status(t("merge_exr.saving").format(out_name.name))
            
            out = OpenEXR.OutputFile(str(out_name), header)
            out.writePixels(exr_channel_data)
            out.close()
            
            self.update_status(t("merge_exr.done"))
            
            msg = t("merge_exr.success_msg").format(out_name, "\n".join(sorted_keys))
            messagebox.showinfo(t("common.success"), msg)
            
        except Exception as e:
            self.update_status("Error")
            print(f"[EXR EXPORT ERROR] {e}")
            import traceback
            traceback.print_exc()
            
            # UI Error Report
            err_msg = f"Export Failed:\n{str(e)}\n\nCheck console for details."
            self.after(0, lambda: messagebox.showerror("Export Error", err_msg))

    def update_status(self, text):
        self.lbl_status.configure(text=text)

    def on_closing(self):
        self.destroy()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        anchor = sys.argv[1]
        
        from utils.explorer import get_selection_from_explorer
        all_files = []
        try:
            selected = get_selection_from_explorer(anchor)
            if selected: all_files = selected
        except: pass
            
        if not all_files:
            all_files = [Path(anchor)]
            
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("merge_exr", anchor, timeout=0.2) is None:
            sys.exit(0)
            
        app = ExrChannelPackerGUI(all_files)
        app.mainloop()
