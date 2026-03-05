"""
RigReady Vectorizer GUI - Main Application Window
Converts raster images/PSD files to rigging-ready SVG vectors.
"""
import sys
import threading
import subprocess
import multiprocessing
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tempfile
import gc

# Path setup
current_file = Path(__file__).resolve()
src_dir = current_file.parent.parent.parent.parent  # vectorizer -> image -> features -> src
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import customtkinter as ctk
from tkinter import messagebox, filedialog
from PIL import Image

from utils.gui_lib import BaseWindow, THEME_BORDER, THEME_TEXT_DIM, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_CARD
from utils.i18n import t
from core.config import MenuConfig


# --- Tooltip Class ---
class CTkTooltip:
    def __init__(self, widget, text, delay=300):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule)
        self.widget.bind("<Leave>", self.unschedule)
        self.widget.bind("<ButtonPress>", self.unschedule)

    def schedule(self, event=None):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        self.hide()

    def show(self):
        if self.tooltip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes('-topmost', True)
        label = ctk.CTkLabel(tw, text=self.text, corner_radius=6, fg_color="#333333", text_color="#FFFFFF", padx=10, pady=5, font=("", 11))
        label.pack()

    def hide(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# --- Constants ---
THEME_BG = "#1A1A1A"

# Heavy domain imports moved to lazy loading in methods
# from features.image.vectorizer.vectorizer_core import vectorize_image, DEFAULT_CONFIG
# from features.image.vectorizer.psd_parser import parse_psd, LayerInfo, get_flat_layer_list
# from features.image.vectorizer.anchor_estimator import estimate_anchor_point
# from features.image.vectorizer.svg_builder import ...


class VectorizerGUI(BaseWindow):
    """Main GUI for RigReady Vectorizer."""
    
    def __init__(self, initial_path: Path = None):
        self.tool_name = "RigReady Vectorizer"
        try:
            config = MenuConfig()
            item = config.get_item_by_id("rigreader_vectorizer")
            if item:
                self.tool_name = item.get("name", self.tool_name)
        except:
            pass
        
        super().__init__(title=t("rigready_vectorizer_gui.title", self.tool_name), width=900, height=800, scrollable=False, icon_name="vectorizer")
        
        self.layers = []
        self.layer_checkboxes = {}
        self.layer_row_frames = {} # Cache for widget reuse
        self.psd_data = None
        self.temp_dir = Path(tempfile.mkdtemp(prefix="vectorizer_"))
        self.processing = False
        
        self.create_widgets()
        
        if initial_path:
            if isinstance(initial_path, (list, tuple)):
                self.load_multiple_files(initial_path)
            else:
                self.load_file(initial_path)
        
        self.after(100, self.adjust_window_size)
    
    def create_widgets(self):
        # Header
        self.add_header(t("rigready_vectorizer_gui.title", "RigReady Vectorizer"), font_size=22)
        ctk.CTkLabel(
            self.main_frame, 
            text=t("rigready_vectorizer_gui.header_desc"),
            text_color=THEME_TEXT_DIM,
            font=("", 11)
        ).pack(pady=(0, 10))
        
        # Header Toolbar (File Loading)
        toolbar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=(0, 10))
        
        self.btn_load = ctk.CTkButton(
            toolbar,
            text=t("rigready_vectorizer_gui.open_file"),
            width=120,
            height=32,
            fg_color=THEME_BTN_PRIMARY,
            hover_color=THEME_BTN_HOVER,
            command=self.browse_file
        )
        self.btn_load.pack(side="right")
        
        self.lbl_file = ctk.CTkLabel(
            toolbar,
            text=t("rigready_vectorizer_gui.no_file_selected"),
            text_color=THEME_TEXT_DIM,
            font=("", 12)
        )
        self.lbl_file.pack(side="left", padx=5)
        
        # Main content area (2 columns)
        content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=5)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # Left: File Input & Layer List
        left_frame = ctk.CTkFrame(content, fg_color=THEME_CARD, corner_radius=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=5)
        
        # Layer list
        # Layer Header Frame
        list_header = ctk.CTkFrame(left_frame, fg_color="transparent")
        list_header.pack(fill="x", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(
            list_header,
            text=t("rigready_vectorizer_gui.layer_list"),
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        self.lbl_layer_count = ctk.CTkLabel(
            list_header,
            text="(0)",
            text_color=THEME_TEXT_DIM,
            font=("", 12)
        )
        self.lbl_layer_count.pack(side="left", padx=5)
        
        self.layer_scroll = ctk.CTkScrollableFrame(left_frame, fg_color="transparent", height=300)
        self.layer_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Select all/none buttons
        sel_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        sel_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkButton(
            sel_frame, text=t("rigready_vectorizer_gui.select_all"), width=80, height=28,
            fg_color=THEME_BTN_PRIMARY,
            command=lambda: self.toggle_all(True)
        ).pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(
            sel_frame, text=t("rigready_vectorizer_gui.deselect_all"), width=80, height=28,
            fg_color="transparent", border_width=1, border_color=THEME_BORDER,
            text_color=("gray10", "gray90"),
            command=lambda: self.toggle_all(False)
        ).pack(side="left")
        
        # Right: Settings & Preview
        right_frame = ctk.CTkFrame(content, fg_color=THEME_CARD, corner_radius=10)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=5)
        
        # VTracer settings
        # Settings Header with Help
        settings_header = ctk.CTkFrame(right_frame, fg_color="transparent")
        settings_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(
            settings_header,
            text=t("rigready_vectorizer_gui.settings"),
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        ctk.CTkButton(
            settings_header,
            text="?",
            width=24,
            height=24,
            corner_radius=12,
            fg_color="gray50",
            hover_color="gray60",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.show_guide
        ).pack(side="right")
        
        settings_grid = ctk.CTkFrame(right_frame, fg_color="transparent")
        settings_grid.pack(fill="x", padx=15)
        
        # Filter Speckle
        ctk.CTkLabel(settings_grid, text=t("rigready_vectorizer_gui.filter_speckle")).grid(row=0, column=0, sticky="w", pady=3)
        self.var_speckle = ctk.IntVar(value=4)
        self.slider_speckle = ctk.CTkSlider(settings_grid, from_=1, to=20, variable=self.var_speckle, width=150)
        self.slider_speckle.grid(row=0, column=1, padx=10)
        self.lbl_speckle = ctk.CTkLabel(settings_grid, text="4")
        self.lbl_speckle.grid(row=0, column=2)
        self.var_speckle.trace_add("write", lambda *a: self.lbl_speckle.configure(text=str(self.var_speckle.get())))
        CTkTooltip(self.slider_speckle, t("rigready_vectorizer_gui.tooltip_speckle"))
        
        # Color Precision
        ctk.CTkLabel(settings_grid, text=t("rigready_vectorizer_gui.color_precision")).grid(row=1, column=0, sticky="w", pady=3)
        self.var_color_prec = ctk.IntVar(value=6)
        self.slider_color = ctk.CTkSlider(settings_grid, from_=1, to=10, variable=self.var_color_prec, width=150)
        self.slider_color.grid(row=1, column=1, padx=10)
        self.lbl_color = ctk.CTkLabel(settings_grid, text="6")
        self.lbl_color.grid(row=1, column=2)
        self.var_color_prec.trace_add("write", lambda *a: self.lbl_color.configure(text=str(self.var_color_prec.get())))
        CTkTooltip(self.slider_color, t("rigready_vectorizer_gui.tooltip_color"))
        
        # Corner Threshold
        ctk.CTkLabel(settings_grid, text=t("rigready_vectorizer_gui.corner_threshold")).grid(row=2, column=0, sticky="w", pady=3)
        self.var_corner = ctk.IntVar(value=60)
        self.slider_corner = ctk.CTkSlider(settings_grid, from_=15, to=180, variable=self.var_corner, width=150)
        self.slider_corner.grid(row=2, column=1, padx=10)
        self.lbl_corner = ctk.CTkLabel(settings_grid, text="60")
        self.lbl_corner.grid(row=2, column=2)
        self.var_corner.trace_add("write", lambda *a: self.lbl_corner.configure(text=str(self.var_corner.get())))
        CTkTooltip(self.slider_corner, t("rigready_vectorizer_gui.tooltip_corner"))
        
        # Options
        self.var_remove_bg = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            right_frame,
            text=t("rigready_vectorizer_gui.remove_bg"),
            variable=self.var_remove_bg,
            fg_color=THEME_BTN_PRIMARY
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        self.var_gen_jsx = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            right_frame,
            text=t("rigready_vectorizer_gui.gen_jsx"),
            variable=self.var_gen_jsx,
            fg_color=THEME_BTN_PRIMARY
        ).pack(anchor="w", padx=15, pady=5)
        
        self.var_split_paths = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            right_frame,
            text=t("rigready_vectorizer_gui.split_paths"),
            variable=self.var_split_paths,
            fg_color=THEME_BTN_PRIMARY
        ).pack(anchor="w", padx=15, pady=5)
        
        self.var_use_anchor = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            right_frame,
            text=t("rigready_vectorizer_gui.use_anchor"),
            variable=self.var_use_anchor,
            fg_color=THEME_BTN_PRIMARY
        ).pack(anchor="w", padx=15, pady=5)
        
        # New: Exclusion options
        self.var_skip_text = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            right_frame,
            text=t("rigready_vectorizer_gui.skip_text"),
            variable=self.var_skip_text,
            fg_color=THEME_BTN_PRIMARY,
            command=self._on_filter_change
        ).pack(anchor="w", padx=15, pady=5)
        
        self.var_skip_smart = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            right_frame,
            text=t("rigready_vectorizer_gui.skip_smart"),
            variable=self.var_skip_smart,
            fg_color=THEME_BTN_PRIMARY,
            command=self._on_filter_change
        ).pack(anchor="w", padx=15, pady=5)
        
        # Output folder
        out_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        out_frame.pack(fill="x", padx=15, pady=(20, 10))
        
        ctk.CTkLabel(out_frame, text=t("rigready_vectorizer_gui.output_folder")).pack(anchor="w")
        
        out_row = ctk.CTkFrame(out_frame, fg_color="transparent")
        out_row.pack(fill="x", pady=(5, 0))
        
        self.var_output = ctk.StringVar(value="")
        self.entry_output = ctk.CTkEntry(out_row, textvariable=self.var_output, placeholder_text="...")
        self.entry_output.pack(side="left", fill="x", expand=True)
        
        ctk.CTkButton(
            out_row, text="📁", width=40,
            fg_color=THEME_BTN_PRIMARY,
            hover_color=THEME_BTN_HOVER,
            command=self.browse_output
        ).pack(side="left", padx=(5, 0))
        
        # Progress
        self.progress = ctk.CTkProgressBar(right_frame, height=10, progress_color=THEME_BTN_PRIMARY)
        self.progress.pack(fill="x", padx=15, pady=(20, 5))
        self.progress.set(0)
        
        self.lbl_status = ctk.CTkLabel(
            right_frame,
            text=t("rigready_vectorizer_gui.no_file_selected"),
            text_color=THEME_TEXT_DIM,
            font=("", 11)
        )
        self.lbl_status.pack(pady=(0, 15))
        
        # Footer buttons (Centralized)
        self.btn_cancel = ctk.CTkButton(
            self.footer_frame,
            text=t("rigready_vectorizer_gui.close"),
            height=45,
            width=120,
            fg_color="transparent",
            border_width=1,
            border_color=THEME_BORDER,
            text_color=("gray10", "gray90"),
            command=self.destroy
        )
        self.btn_cancel.pack(side="left")
        
        self.btn_convert = ctk.CTkButton(
            self.footer_frame,
            text=t("rigready_vectorizer_gui.start"),
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=THEME_BTN_PRIMARY,
            hover_color=THEME_BTN_HOVER,
            command=self.start_conversion
        )
        self.btn_convert.pack(side="right", fill="x", expand=True, padx=(20, 0))
    
    def browse_file(self):
        filetypes = [
            ("Supported Files", "*.psd *.psb *.png *.jpg *.jpeg"),
            ("Photoshop", "*.psd *.psb"),
            ("Images", "*.png *.jpg *.jpeg"),
        ]
        path = filedialog.askopenfilename(title="파일 선택", filetypes=filetypes)
        if path:
            self.load_file(Path(path))
    
    def browse_output(self):
        path = filedialog.askdirectory(title="출력 폴더 선택")
        if path:
            self.var_output.set(path)
    
    def load_file(self, path: Path):
        path = Path(path)
        if not path.exists():
            messagebox.showerror(t("rigready_vectorizer_gui.error"), f"File not found: {path}")
            return
        
        self.lbl_file.configure(text=path.name)
        self.lbl_status.configure(text=t("rigready_vectorizer_gui.analyzing"))
        self.update_idletasks()
        
        ext = path.suffix.lower()
        
        if ext in ('.psd', '.psb'):
            # Parse PSD
            try:
                from features.image.vectorizer.psd_parser import parse_psd
                self._clear_layer_widgets()
                self.psd_data = parse_psd(path, include_hidden=False)
                self._populate_layers()
            except Exception as e:
                messagebox.showerror(t("rigready_vectorizer_gui.parse_error"), str(e))
                self.lbl_status.configure(text=t("rigready_vectorizer_gui.error"))
                return
        else:
            # Single image - use a more robust image loader/checker
            try:
                self.psd_data = None
                self._clear_layer_widgets()
                
                with Image.open(path) as img:
                    w, h = img.size
                    has_alpha = img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                    
                    self._add_layer_row(path.stem, w, h, path, str(path))
                    
                    note = "" if has_alpha else " (Background removal needed)"
                    self.lbl_status.configure(text=f"Loaded ({w}x{h}){note}")
            except Exception as e:
                messagebox.showerror(t("rigready_vectorizer_gui.image_load_error"), str(e))
                return
        
        # Set default output path
        if not self.var_output.get():
            self.var_output.set(str(path.parent / "vectorized"))

    def load_multiple_files(self, paths: list[Path]):
        """Load multiple image files as 'layers' for vectorization."""
        self._clear_layer_widgets()
        self.psd_data = None
        
        valid_paths = [Path(p) for p in paths if Path(p).exists() and Path(p).suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp', '.tga', '.webp')]
        
        if not valid_paths:
            messagebox.showwarning("Warning", "No valid image files found in selection.")
            return

        self.lbl_file.configure(text=f"Multiple Files ({len(valid_paths)})")
        
        for p in valid_paths:
            try:
                with Image.open(p) as img:
                    w, h = img.size
                    self._add_layer_row(p.stem, w, h, p, str(p))
            except:
                continue
        
        if valid_paths and not self.var_output.get():
            self.var_output.set(str(valid_paths[0].parent / "vectorized"))
        
        self._update_layer_count()
        self.lbl_status.configure(text=f"Loaded {len(self.layers)} images")

    def _clear_layer_widgets(self):
        """Destroy all layer widgets and clear caches."""
        for widget in self.layer_scroll.winfo_children():
            widget.destroy()
        self.layer_checkboxes.clear()
        self.layer_row_frames.clear()
        self.layers.clear()

    def _on_filter_change(self):
        """Handle checkbox changes for layer filtering."""
        if hasattr(self, 'psd_data') and self.psd_data:
            self._populate_layers()

    def _update_layer_count(self):
        """Update the header label with current selection/total status."""
        total = len(self.layer_checkboxes)
        selected = sum(1 for var in self.layer_checkboxes.values() if var.get())
        
        # Determine visible count
        visible = 0
        for uid, row_frame in self.layer_row_frames.items():
            if row_frame.winfo_manager() == "pack":
                visible += 1
                
        self.lbl_layer_count.configure(text=f"({selected}/{total}) [Visible: {visible}]" if visible != total else f"({selected}/{total})")

    def _populate_layers(self):
        """Populate the layer list with filtering (Optimized with visibility toggle)."""
        if not self.psd_data:
            # Handle single image case
            self._update_layer_count()
            return
            
        from features.image.vectorizer.psd_parser import get_flat_layer_list
        flat_layers = get_flat_layer_list(self.psd_data)
        
        # Determine filters
        skip_text = self.var_skip_text.get()
        skip_smart = self.var_skip_smart.get()
        
        # If widgets don't exist yet, create them all once
        if not self.layer_row_frames:
            for layer in flat_layers:
                display_name = layer.path if getattr(layer, "path", None) else layer.name
                self._add_layer_row(display_name, layer.width, layer.height, layer, layer.uid, True)
        
        # Toggle visibility based on filters
        for uid, row_frame in self.layer_row_frames.items():
            # Find the layer data for this UID
            layer = next((l for l in flat_layers if l.uid == uid), None)
            if not layer:
                row_frame.pack_forget()
                continue
                
            # Apply filters
            is_visible = True
            if skip_text and getattr(layer, 'is_text', False):
                is_visible = False
            if skip_smart and getattr(layer, 'is_smart_object', False):
                is_visible = False
            
            if is_visible:
                row_frame.pack(fill="x", pady=2)
            else:
                row_frame.pack_forget()
        
        self._update_layer_count()
        self.lbl_status.configure(text=t("common.ready"))

    def _add_layer_row(self, name, width, height, data, uid, is_checked=True):
        row = ctk.CTkFrame(self.layer_scroll, fg_color="transparent", height=30)
        row.pack(fill="x", pady=2)
        
        self.layer_row_frames[uid] = row
        
        var = ctk.BooleanVar(value=is_checked)
        var.trace_add("write", lambda *a: self._update_layer_count())
        chk = ctk.CTkCheckBox(
            row,
            text="",
            variable=var,
            width=24,
            height=24,
            checkbox_width=20,
            checkbox_height=20,
            fg_color=THEME_BTN_PRIMARY
        )
        chk.pack(side="left", padx=(5, 5))
        
        kind_marker = "T" if getattr(data, 'is_text', False) else "S" if getattr(data, 'is_smart_object', False) else ""
        if kind_marker:
            ctk.CTkLabel(row, text=f"[{kind_marker}]", font=("", 10), width=20, text_color="gray").pack(side="left")

        # Truncate long names (keep the end for paths)
        display_name = name
        if len(name) > 35:
            display_name = "..." + name[-32:]
            
        name_lbl = ctk.CTkLabel(row, text=display_name, anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True)
        
        if len(name) > 35:
            CTkTooltip(name_lbl, name)
        
        # Details
        dim_text = f"{width}×{height}"
        ctk.CTkLabel(row, text=dim_text, width=80, text_color=THEME_TEXT_DIM, font=("", 10)).pack(side="right", padx=5)
        
        self.layer_checkboxes[uid] = var
        self.layers.append((uid, name, data))
    
    def toggle_all(self, state):
        for var in self.layer_checkboxes.values():
            var.set(state)
        self._update_layer_count()
    
    def start_conversion(self):
        if self.processing:
            return
        
        selected = [
            (uid, name, data)
            for uid, name, data in self.layers
            if self.layer_checkboxes.get(uid, ctk.BooleanVar()).get()
        ]
        
        if not selected:
            messagebox.showwarning(t("rigready_vectorizer_gui.warning"), t("rigready_vectorizer_gui.select_layers"))
            return
        
        output_dir = Path(self.var_output.get()) if self.var_output.get() else (
            self.psd_data.file_path.parent / "vectorized"
            if self.psd_data
            else Path(self.layers[0][2]).parent / "vectorized"
        )
        
        # Overwrite Check
        if output_dir.exists() and any(output_dir.iterdir()):
            if not messagebox.askyesno(
                t("rigready_vectorizer_gui.overwrite_confirm"),
                t("rigready_vectorizer_gui.overwrite_msg", path=output_dir)
            ):
                return
        
        self.processing = True
        self.btn_convert.configure(state="disabled", text=t("rigready_vectorizer_gui.processing"))
        self.progress.set(0)
        
        def process():
            try:
                self._run_vectorization(selected, output_dir)
            except Exception as e:
                import traceback
                traceback.print_exc()
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: messagebox.showerror(t("rigready_vectorizer_gui.error"), msg))
            finally:
                self.after(0, self._finish_processing)
        
        threading.Thread(target=process, daemon=True).start()
    
    def _run_vectorization(self, selected, output_dir):
        from concurrent.futures import ThreadPoolExecutor
        from features.image.vectorizer.vectorizer_core import vectorize_image, DEFAULT_CONFIG
        from features.image.vectorizer.anchor_estimator import estimate_anchor_point
        from features.image.vectorizer.svg_builder import (
            build_structured_svg,
            build_metadata_json,
            build_ae_jsx_script,
            parse_svg_document,
            svg_paths_to_ae_shapes,
            save_individual_svgs,
            LayerSVG
        )

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        total = len(selected)
        vectorized_map = {}

        config = {
            **DEFAULT_CONFIG,
            "filter_speckle": self.var_speckle.get(),
            "color_precision": self.var_color_prec.get(),
            "corner_threshold": self.var_corner.get()
        }

        canvas_w = self.psd_data.canvas_width if self.psd_data else 0
        canvas_h = self.psd_data.canvas_height if self.psd_data else 0

        # Phase 1: Prepare images (may include GPU-accelerated background removal)
        prepared_layers = []
        for i, (uid, display_name, data) in enumerate(selected):
            self.after(0, lambda v=(i+0.5)/total, n=display_name: (
                self.progress.set(v * 0.5),
                self.lbl_status.configure(text=f"{t('rigready_vectorizer_gui.preparing')} {n}")
            ))

            if hasattr(data, 'image') and data.image:
                img = data.image
                offset_x, offset_y = data.offset_x, data.offset_y
                width, height = data.width, data.height
                layer_name = data.name
                layer_path = getattr(data, "path", display_name)
                parent_uid = getattr(data, "parent_uid", None)
            else:
                img = Image.open(data)
                offset_x, offset_y = 0, 0
                width, height = img.size
                canvas_w = max(canvas_w, width)
                canvas_h = max(canvas_h, height)
                layer_name = display_name
                layer_path = display_name
                parent_uid = None

            if self.var_remove_bg.get() and img.mode not in ('RGBA', 'LA'):
                label_text = t("rigready_vectorizer_gui.remove_bg") # Or a more specific key if available
                self.after(0, lambda n=display_name: self.lbl_status.configure(text=f"{label_text}: {n}"))
                try:
                    from rembg import remove
                    img = remove(img)
                except Exception as e:
                    print(f"Rembg failed for {display_name}: {e}")
            safe_name = uid.replace("/", "_").replace("\\", "_").replace(":", "_").replace(" ", "_")
            temp_png = self.temp_dir / f"{safe_name}.png"
            img.save(temp_png, format='PNG')

            prepared_layers.append({
                'uid': uid,
                'name': layer_name,
                'path': layer_path,
                'parent_uid': parent_uid,
                'display_name': display_name,
                'temp_png': temp_png,
                'offset_x': offset_x,
                'offset_y': offset_y,
                'width': width,
                'height': height,
                'vector_mask_d': getattr(data, 'vector_mask_d', None)
            })

            del img
            gc.collect()

        # Phase 2: Parallel vectorization (CPU multicore)
        max_workers = max(1, multiprocessing.cpu_count() - 1)
        self.after(0, lambda: self.lbl_status.configure(text=t("rigready_vectorizer_gui.analyzing")))

        use_anchor = self.var_use_anchor.get()
        split_paths = self.var_split_paths.get()

        def get_layer_color(png_path):
            try:
                from PIL import Image
                with Image.open(png_path) as img:
                    # Resize to 1x1 to get average color
                    color = img.resize((1, 1)).getpixel((0, 0))
                    # Handle RGBA
                    if len(color) == 4:
                        if color[3] < 10: return "#000000" # Transparent
                        return "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
                    return "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
            except:
                return "#000000"

        def vectorize_layer(layer_data):
            try:
                if layer_data.get('vector_mask_d'):
                    # HYBRID MODE: Use direct vector data for Shape Layers
                    print(f"Direct extracting: {layer_data['name']}")
                    hex_color = get_layer_color(layer_data['temp_png'])
                    
                    # Create synthetic SVG with coordinate transform (Global -> Local)
                    ox = layer_data['offset_x']
                    oy = layer_data['offset_y']
                    d = layer_data['vector_mask_d']
                    w = layer_data['width']
                    h = layer_data['height']
                    
                    svg_content = (
                        f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">'
                        f'<g transform="translate({-ox}, {-oy})">'
                        f'<path d="{d}" fill="{hex_color}" />'
                        f'</g>'
                        f'</svg>'
                    )
                else:
                    # NORMAL MODE: Trace raster image
                    print(f"Tracing: {layer_data['name']}")
                    svg_content = vectorize_image(layer_data['temp_png'], config=config)

                svg_paths, _, _ = parse_svg_document(
                    svg_content,
                    target_width=layer_data['width'],
                    target_height=layer_data['height']
                )

                if use_anchor:
                    anchor = estimate_anchor_point(
                        layer_data['name'],
                        layer_data['offset_x'],
                        layer_data['offset_y'],
                        layer_data['width'],
                        layer_data['height']
                    )
                    ax, ay = anchor.x, anchor.y
                    duik_name = anchor.duik_name
                else:
                    ax = layer_data['offset_x'] + (layer_data['width'] / 2)
                    ay = layer_data['offset_y'] + (layer_data['height'] / 2)
                    duik_name = None

                # If split_paths is enabled, create a group with each path as a child
                if split_paths and len(svg_paths) > 1:
                    children = []
                    for i, sp in enumerate(svg_paths):
                        child_name = f"{layer_data['name']}_path{i+1}"
                        children.append(LayerSVG(
                            name=child_name,
                            uid=f"{layer_data['uid']}_path{i+1}",
                            path=child_name,
                            offset_x=layer_data['offset_x'],
                            offset_y=layer_data['offset_y'],
                            width=layer_data['width'],
                            height=layer_data['height'],
                            anchor_x=ax,
                            anchor_y=ay,
                            is_group=False,
                            duik_name=duik_name,
                            parent_uid=layer_data['uid'],
                            svg_paths=[sp]
                        ))
                    return LayerSVG(
                        name=layer_data['name'],
                        uid=layer_data['uid'],
                        path=layer_data['path'],
                        offset_x=layer_data['offset_x'],
                        offset_y=layer_data['offset_y'],
                        width=layer_data['width'],
                        height=layer_data['height'],
                        anchor_x=ax,
                        anchor_y=ay,
                        is_group=True,
                        duik_name=duik_name,
                        parent_uid=layer_data.get('parent_uid'),
                        children=children
                    )

                return LayerSVG(
                    name=layer_data['name'],
                    uid=layer_data['uid'],
                    path=layer_data['path'],
                    offset_x=layer_data['offset_x'],
                    offset_y=layer_data['offset_y'],
                    width=layer_data['width'],
                    height=layer_data['height'],
                    anchor_x=ax,
                    anchor_y=ay,
                    is_group=False,
                    duik_name=duik_name,
                    parent_uid=layer_data.get('parent_uid'),
                    svg_paths=svg_paths
                )
            except Exception as e:
                import traceback
                print(f"[ERROR] vectorize_layer failed for {layer_data.get('name', 'unknown')}: {e}")
                traceback.print_exc()
                raise

        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_list = [executor.submit(vectorize_layer, layer) for layer in prepared_layers]
            for future in future_list:
                layer_svg = future.result()
                vectorized_map[layer_svg.uid] = layer_svg
                completed += 1
                self.after(0, lambda v=0.5 + (completed/total)*0.5, n=layer_svg.name: (
                    self.progress.set(v),
                    self.lbl_status.configure(text=f"Vectorized: {n}")
                ))

        def build_tree(layer_info):
            if layer_info.is_group:
                children = [build_tree(child) for child in layer_info.children]
                children = [child for child in children if child]
                if not children:
                    return None
                return LayerSVG(
                    name=layer_info.name,
                    uid=layer_info.uid,
                    path=layer_info.path,
                    offset_x=layer_info.offset_x,
                    offset_y=layer_info.offset_y,
                    width=layer_info.width,
                    height=layer_info.height,
                    anchor_x=None,
                    anchor_y=None,
                    is_group=True,
                    parent_uid=layer_info.parent_uid,
                    children=children
                )
            return vectorized_map.get(layer_info.uid)

        if self.psd_data:
            layer_tree = []
            for layer in self.psd_data.layers:
                node = build_tree(layer)
                if node:
                    layer_tree.append(node)
        else:
            layer_tree = [vectorized_map[uid] for uid, _, _ in selected if uid in vectorized_map]

        def iter_leaf(nodes):
            for node in nodes:
                if node.is_group:
                    yield from iter_leaf(node.children)
                else:
                    yield node

        leaf_nodes = list(iter_leaf(layer_tree))

        # Build outputs
        base_name = self.psd_data.file_path.stem if self.psd_data else "vectorized"

        svg_path = output_dir / f"{base_name}.svg"
        json_path = output_dir / f"{base_name}_metadata.json"
        jsx_path = output_dir / f"{base_name}_import.jsx"

        self.after(0, lambda: self.lbl_status.configure(text="Building SVG..."))
        build_structured_svg(layer_tree, canvas_w, canvas_h, svg_path)

        self.after(0, lambda: self.lbl_status.configure(text="Saving layer SVGs..."))
        save_individual_svgs(layer_tree, output_dir)

        # Prepare native shape data for JSX
        self.after(0, lambda: self.lbl_status.configure(text="Preparing AE shapes..."))
        jsx_layer_data = []
        for l in leaf_nodes:
            shapes = svg_paths_to_ae_shapes(l.svg_paths)
            jsx_layer_data.append({
                "name": l.name,
                "offset_x": l.offset_x,
                "offset_y": l.offset_y,
                "width": l.width,
                "height": l.height,
                "anchor_x": l.anchor_x,
                "anchor_y": l.anchor_y,
                "shapes": shapes
            })

        self.after(0, lambda: self.lbl_status.configure(text="Writing metadata..."))
        build_metadata_json(layer_tree, canvas_w, canvas_h, json_path)

        if self.var_gen_jsx.get():
            self.after(0, lambda: self.lbl_status.configure(text=t("rigready_vectorizer_gui.writing_jsx")))
            build_ae_jsx_script(
                jsx_layer_data, 
                canvas_w, 
                canvas_h, 
                jsx_path,
                msg_complete=t("rigready_vectorizer_gui.ae_import_complete"),
                msg_error=t("rigready_vectorizer_gui.ae_import_error")
            )

        self.after(0, lambda: self._show_success(output_dir, len(leaf_nodes)))

    def _finish_processing(self):
        self.processing = False
        self.btn_convert.configure(state="normal", text=t("rigready_vectorizer_gui.start"))
        self.progress.set(1)
    
    def _show_success(self, output_dir, count):
        self.lbl_status.configure(text=t("rigready_vectorizer_gui.complete"))
        
        if messagebox.askyesno(t("common.done"), t("rigready_vectorizer_gui.complete_msg", count=count, path=output_dir) + "\n\n" + t("marigold_gui.open_folder_prompt")):
            subprocess.Popen(f'explorer "{output_dir}"')

    def save_helper_script(self):
        """Save the helper JSX script to user location."""
        import shutil
        
        script_name = "SmartObjectToShape.jsx"
        source = Path(__file__).parent / "resources" / script_name
        
        if not source.exists():
            messagebox.showerror(t("common.error"), f"Script not found:\n{source}")
            return
            
        dest = filedialog.asksaveasfilename(
            title=t("rigready_vectorizer_gui.guide.save_script"),
            initialfile=script_name,
            filetypes=[("Photoshop Script", "*.jsx")]
        )
        
        if dest:
            try:
                shutil.copy2(source, dest)
                messagebox.showinfo(t("common.success"), f"Saved to:\n{dest}")
            except Exception as e:
                messagebox.showerror(t("common.error"), f"Save failed:\n{e}")

    def show_guide(self):
        """Show User Guide popup."""
        # Prevent GC and multiple windows
        if hasattr(self, 'guide_window') and self.guide_window is not None and self.guide_window.winfo_exists():
            self.guide_window.lift()
            self.guide_window.focus_force()
            return

        self.guide_window = ctk.CTkToplevel(self)
        self.guide_window.title(t("rigready_vectorizer_gui.guide.title"))
        self.guide_window.geometry("550x750")
        
        # Keep on top
        self.guide_window.attributes('-topmost', True)
        self.guide_window.transient(self)
        
        # Center popup
        x = self.winfo_x() + (self.winfo_width()//2) - 275
        y = self.winfo_y() + (self.winfo_height()//2) - 375
        self.guide_window.geometry(f"+{x}+{y}")
        
        # Main Scroll Container
        scroll = ctk.CTkScrollableFrame(self.guide_window, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- Section 1: Smart Object Warning ---
        card_smart = ctk.CTkFrame(scroll, fg_color=THEME_CARD, corner_radius=10)
        card_smart.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(card_smart, text=t("rigready_vectorizer_gui.guide.smart_object_title"), font=("", 16, "bold"), text_color="#FF5555").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(card_smart, text=t("rigready_vectorizer_gui.guide.smart_object_desc"), font=("", 12), justify="left").pack(anchor="w", padx=15, pady=(0, 10))
        
        # Action Button Frame
        action_frame = ctk.CTkFrame(card_smart, fg_color="transparent")
        action_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkButton(
            action_frame,
            text=t("rigready_vectorizer_gui.guide.save_script"),
            height=35,
            fg_color="#3B8ED0",
            font=("", 12, "bold"),
            command=self.save_helper_script
        ).pack(fill="x")
        
        ctk.CTkLabel(action_frame, text=t("rigready_vectorizer_gui.guide.script_desc"), font=("", 11), text_color="gray70", justify="center").pack(pady=(5, 0))

        # --- Section 2: Parameters ---
        ctk.CTkLabel(scroll, text=t("rigready_vectorizer_gui.guide.param_title"), font=("", 16, "bold")).pack(anchor="w", pady=(0, 5))
        
        card_param = ctk.CTkFrame(scroll, fg_color=THEME_CARD, corner_radius=10)
        card_param.pack(fill="x", pady=(0, 15))
        
        def add_param_desc(parent, title, desc_map):
            ctk.CTkLabel(parent, text=title, font=("", 14, "bold"), text_color="#AAAAAA").pack(anchor="w", padx=15, pady=(15, 5))
            for key, val in desc_map.items():
                row = ctk.CTkFrame(parent, fg_color="transparent")
                row.pack(fill="x", padx=15, pady=2)
                ctk.CTkLabel(row, text=f"• {key}:", font=("", 12, "bold"), width=80, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=val, font=("", 12), anchor="w").pack(side="left")

        # 1. Filter Speckle
        add_param_desc(card_param, t("rigready_vectorizer_gui.guide.param_speckle"), {
            f"{t('rigready_vectorizer_gui.guide.default')} (4)": "Standard",
            f"{t('rigready_vectorizer_gui.guide.low')} (1~2)": "Details/Texture",
            f"{t('rigready_vectorizer_gui.guide.high')} (10+)": "Clean/Flat"
        })
        
        # 2. Color Precision
        add_param_desc(card_param, t("rigready_vectorizer_gui.guide.param_color"), {
            f"{t('rigready_vectorizer_gui.guide.default')} (6)": "Balanced",
            f"{t('rigready_vectorizer_gui.guide.low')} (2~4)": "Posterized",
            f"{t('rigready_vectorizer_gui.guide.high')} (8)": "Detailed Color"
        })
        
        # 3. Corner Threshold
        add_param_desc(card_param, t("rigready_vectorizer_gui.guide.param_corner"), {
            f"{t('rigready_vectorizer_gui.guide.default')} (60)": "Natural",
            f"{t('rigready_vectorizer_gui.guide.low')} (30)": "Angular/Pixel",
            f"{t('rigready_vectorizer_gui.guide.high')} (90)": "Round/Organic"
        })
        # Add padding at bottom of param card
        ctk.CTkLabel(card_param, text="", height=5).pack()

        # --- Section 3: Tips ---
        card_tip = ctk.CTkFrame(scroll, fg_color="#2B2B40", corner_radius=10, border_width=1, border_color="#444466")
        card_tip.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(card_tip, text=t("rigready_vectorizer_gui.guide.tip_title"), font=("", 13, "bold"), text_color="#DDDDFF").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(card_tip, text=t("rigready_vectorizer_gui.guide.tip_desc"), font=("", 12), text_color="#CCCCEE", justify="left").pack(anchor="w", padx=15, pady=(0, 10))
        
        tip_row = ctk.CTkFrame(card_tip, fg_color="transparent")
        tip_row.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(tip_row, text=t("rigready_vectorizer_gui.guide.tip_val"), font=("", 12, "bold"), bg_color="#333355", corner_radius=5).pack()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        paths = [Path(p) for p in sys.argv[1:]]
        if len(paths) == 1:
            app = VectorizerGUI(paths[0])
        else:
            app = VectorizerGUI(paths)
    else:
        app = VectorizerGUI(None)
    app.mainloop()
