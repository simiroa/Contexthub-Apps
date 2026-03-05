"""
Image Compare GUI - Multi-image comparison with EXR channel support
"""
import sys
import threading
from pathlib import Path
from typing import List, Optional
import tkinter as tk
from tkinter import messagebox, filedialog

try:
    import customtkinter as ctk
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", "CustomTkinter is required.")
    sys.exit(1)

from PIL import Image, ImageTk
# import numpy as np # Moved to lazy loading in methods

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Domain logic imports are handled lazily within class methods
# from features.image.compare_core import ...

from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from utils.i18n import t
from core.logger import setup_logger

logger = setup_logger("image_compare")



class ImageCompareGUI(BaseWindow):
    """Image comparison GUI with EXR channel support."""
    
    def __init__(self, files: List[str]):
        super().__init__(title=t("image_compare_gui.title"), width=1280, height=800, icon_name="image_compare")
        
        # Remove default padding from BaseWindow main_frame for full canvas experience
        self.main_frame.pack_configure(padx=0, pady=0)
        
        # State
        self.files = [Path(f) for f in files]
        self.images: List[Optional[np.ndarray]] = []
        self.original_pils: List[Optional[Image.Image]] = []
        self.photo_images: List[Optional[ImageTk.PhotoImage]] = []
        
        # Caching layer
        self._resize_cache = {}
        self._diff_cache = None
        self._cache_job = None  # For predictive caching debounce
        
        self.current_channel = "RGB"
        self.current_mode = "Side by Side"
        self.zoom_level = 1.0
        self.pan_offset = [0, 0]
        self._drag_start = (0, 0)
        self._dragging_slider = False
        self.slider_pos = 0.5 # Internal state for slider comparison
        
        # Slots for comparison
        self.slots = {"A": 0, "B": 1 if len(files) > 1 else 0}
        self.active_slot = "A"
        
        
        # Remove default padding from BaseWindow main_frame for full canvas experience
        self.main_frame.pack_configure(padx=0, pady=0)
        
        self._build_ui()
        self._load_initial_images()
        self._setup_hotkeys()
        
        self.lift()
        self.focus_force()

    def _build_ui(self):
        # Top toolbar - Unified and Clean
        toolbar = ctk.CTkFrame(self.main_frame, height=50, fg_color=THEME_CARD, corner_radius=0)
        toolbar.pack(fill="x", padx=0, pady=0)
        toolbar.pack_propagate(False) # Fixed height
        
        # Center Container for alignment
        center_row = ctk.CTkFrame(toolbar, fg_color="transparent")
        center_row.pack(expand=True, fill="y")
        
        # Unified Dropdown Style
        dd_width = 130
        dd_height = 32
        dd_font = ("", 11)
        
        # 1. Add Button (Leftmost)
        self.btn_add = ctk.CTkButton(center_row, text="+ Add Image", width=90, height=dd_height, font=dd_font,
                                    command=self._add_image)
        self.btn_add.pack(side="left", padx=(0, 15))

        # 2. Mode Selector
        self.mode_map = {
            t("image_compare_gui.mode_single"): "Single",
            t("image_compare_gui.mode_side"): "Side by Side",
            t("image_compare_gui.mode_slider"): "Slider",
            t("image_compare_gui.mode_diff"): "Difference",
            t("image_compare_gui.mode_grid"): "Grid"
        }
        self.mode_var = ctk.StringVar(value=t("image_compare_gui.mode_side"))
        self.mode_menu = ctk.CTkOptionMenu(center_row, variable=self.mode_var,
                                           values=list(self.mode_map.keys()),
                                           width=dd_width, height=dd_height, font=dd_font,
                                           command=self._on_mode_change)
        self.mode_menu.pack(side="left", padx=5)
        
        # 3. Channel Selector
        self.channel_var = ctk.StringVar(value="RGB")
        self.channel_menu = ctk.CTkOptionMenu(center_row, variable=self.channel_var,
                                               values=["RGB", "R", "G", "B", "A"],
                                               width=80, height=dd_height, font=dd_font,
                                               command=self._on_channel_change)
        self.channel_menu.pack(side="left", padx=5)

        # 4. Slot A Selector
        self.slot_a_var = ctk.StringVar(value="Slot A")
        self.slot_a_menu = ctk.CTkOptionMenu(center_row, variable=self.slot_a_var,
                                             width=180, height=dd_height, font=dd_font,
                                             anchor="w",
                                             command=lambda v: self._on_slot_selector_change("A", v))
        self.slot_a_menu.pack(side="left", padx=(15, 5))
        
        # 5. Slot B Selector
        self.slot_b_var = ctk.StringVar(value="Slot B")
        self.slot_b_menu = ctk.CTkOptionMenu(center_row, variable=self.slot_b_var,
                                             width=180, height=dd_height, font=dd_font,
                                             anchor="w",
                                             command=lambda v: self._on_slot_selector_change("B", v))
        self.slot_b_menu.pack(side="left", padx=5)
        
        # 6. Stats (Rightmost)
        self.stats_label = ctk.CTkLabel(center_row, text="", font=("", 11), text_color="#00b894")
        self.stats_label.pack(side="left", padx=(20, 0))
        
        # Main Layout: Just Canvas (No Sidebar)
        # Main Layout: Just Canvas (No Sidebar)
        # We pack directly into self.main_frame which is already inside outer_frame
        self.canvas_container = ctk.CTkFrame(self.main_frame, fg_color="#000000")
        self.canvas_container.pack(fill="both", expand=True, padx=2, pady=(5, 5))
        
        self.canvas = tk.Canvas(self.canvas_container, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        

        
        # Pixel info and Help in Centralized Footer
        help_text = "[Click] Flip A/B (Single Mode) | [Drag Image] Pan | [Drag Center] Slider"
        self.help_label = ctk.CTkLabel(self.footer_frame, text=help_text, 
                                        font=ctk.CTkFont(size=10), text_color="#555")
        self.help_label.pack(side="left", padx=10)
        
        self.pixel_label = ctk.CTkLabel(self.footer_frame, text="Pos: -, -", font=ctk.CTkFont(size=10), text_color="#00b894")
        self.pixel_label.pack(side="left", padx=20)
        
        # Zoom Buttons in Footer
        ctk.CTkButton(self.footer_frame, text="-", width=30, height=28,
                     fg_color="transparent", border_width=1,
                     command=self._zoom_out).pack(side="right", padx=2)
        ctk.CTkButton(self.footer_frame, text="+", width=30, height=28,
                     fg_color="transparent", border_width=1,
                     command=self._zoom_in).pack(side="right", padx=2)
        ctk.CTkButton(self.footer_frame, text="Reset Zoom", width=80, height=28,
                     fg_color="transparent", border_width=1,
                     command=self._reset_zoom).pack(side="right", padx=5)
        
        # Canvas bindings
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Configure>", self._on_resize)

    def _setup_hotkeys(self):
        """Bind keyboard shortcuts."""
        self.bind("<space>", lambda e: self._toggle_slots())
        self.bind("<Tab>", lambda e: self._toggle_slots())
        for i in range(1, 10):
            self.bind(str(i), lambda e, idx=i-1: self._select_image_by_index(idx))

    def _load_initial_images(self):
        """Load initial images from file list."""
        initial_files = list(self.files)
        self.files = [] # Clear so _add_image_to_slots doesn't skip them
        for f in initial_files:
            self._add_image_to_slots(str(f))
        
        # Update EXR channels if first file is EXR
        if self.files and self.files[0].suffix.lower() == ".exr":
            from features.image.compare_core import get_exr_channels
            channels = get_exr_channels(str(self.files[0]))
            if channels:
                all_channels = ["RGB", "R", "G", "B", "A"] + [c for c in channels if c not in "RGBArgba"]
                self.channel_menu.configure(values=all_channels)
        
        self._update_display()

    def _add_image_to_slots(self, path: str):
        """Add a new image to the internal lists."""
        from features.image.compare_core import load_image, array_to_pil
        p = Path(path).resolve()
        if p in self.files:
            return # Skip duplicates
            
        arr = load_image(str(p), self.current_channel)
        if arr is not None:
            self.images.append(arr)
            pil = array_to_pil(arr)
            self.original_pils.append(pil)
            self.photo_images.append(None)
            
            self.files.append(p)
            self._update_slot_selectors()

    # Gallery and Context Menu methods removed (Cleanup)

    def _set_slot(self, slot_id, index):
        self.slots[slot_id] = index
        self._update_slot_selectors() # Sync dropdowns
        self._update_display()

    def _select_image_by_index(self, index):
        if 0 <= index < len(self.images):
            # In Single mode, we just update Slot A and show it
            self.slots["A"] = index
            self.active_slot = "A"
            self._update_display()
            self._update_slot_selectors()

    def _toggle_slots(self):
        """Flip between Slot A and B in single mode."""
        if self.active_slot == "A":
            self.active_slot = "B"
        else:
            self.active_slot = "A"
        self._update_display()

    def _load_image_at(self, index: int, path: str):
        """Load image at specific index."""
        from features.image.compare_core import load_image, array_to_pil
        arr = load_image(path, self.current_channel)
        if arr is not None:
            self.images[index] = arr
            self.original_pils[index] = array_to_pil(arr)
            if index >= len(self.files):
                self.files.append(Path(path))
            else:
                self.files[index] = Path(path)

    def _update_display(self):
        """Update canvas with current images and mode."""
        self.canvas.delete("all")
        
        # Get canvas size
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        
        valid_indices = [i for i, img in enumerate(self.images) if img is not None]
        if not valid_indices:
            self.canvas.create_text(cw//2, ch//2, text=t("image_common.no_images_loaded"), 
                                   fill="#666", font=("Arial", 14))
            return
        
        mode_label = self.mode_var.get()
        mode = self.mode_map.get(mode_label, "Side by Side")
        
        if mode == "Single":
            idx = self.slots[self.active_slot]
            self._draw_single(cw, ch, idx)
        elif mode == "Difference":
            self._draw_difference(cw, ch)
        elif mode == "Slider":
            self._draw_slider(cw, ch)
        elif mode == "Grid":
            self._draw_grid(cw, ch)
        else:  # Side by Side
            self._draw_side_by_side(cw, ch)
        
        # Update stats
        self._update_stats()
        
        # Trigger predictive cache
        if self._cache_job:
            self.after_cancel(self._cache_job)
        self._cache_job = self.after(200, self._run_predictive_cache)

    def _run_predictive_cache(self):
        """Cache current view size for ALL images to prevent flicker."""
        try:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            if cw < 50 or ch < 50: return # Skip if too small
            
            # Determine target size based on current mode & zoom
            mode = self.mode_var.get()
            panel_w = cw // 2 if mode == "Side by Side" else cw
            
            # We want to cache for the CURRENT Zoom level
            # Strategy: For all loaded images, compute resize and store if missing
            
            # Limit caching to first 10 images to avoid OOM on huge lists? 
            # Or just cache neighbors? For now, all is fine as they are just TkImages (shared memory usually ok)
            
            for i, pil_img in enumerate(self.original_pils):
                if pil_img is None: continue
                
                # Calculate target dimensions
                base_scale = min(panel_w / pil_img.width, ch / pil_img.height) 
                if mode == "Side by Side": base_scale *= 0.95 
                else: base_scale *= 0.98
                
                scale = base_scale * self.zoom_level
                new_w = int(pil_img.width * scale)
                new_h = int(pil_img.height * scale)
                
                if new_w <= 0 or new_h <= 0: continue

                # Check keys
                # We need to cover Single/Slider (full width) AND Side by Side (half width)?
                # Actually mode changes trigger redraw, so we just cache for the CURRENT mode.
                
                cache_key_single = (i, self.zoom_level, self.current_channel)
                cache_key_side = (i, self.zoom_level, self.current_channel, "side")
                cache_key_slider = (i, self.zoom_level, self.current_channel, "slider")
                
                target_key = cache_key_single
                if mode == "Side by Side": target_key = cache_key_side
                elif mode == "Slider": target_key = cache_key_slider
                
                if target_key not in self._resize_cache:
                    # Generate
                    img_display = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img_display)
                    self._resize_cache[target_key] = photo
                    
                    # Also update photo_images list if this is a currently visible slot
                    # But the drawing loop handles that.
            
            # No UI update needed, just filling cache
            
        except Exception as e:
            logger.error(f"Cache Error: {e}")

    def _update_slot_selectors(self):
        """Update the dropdown values matching file list."""
        names = [f"{i+1}: {f.name}" for i, f in enumerate(self.files)]
        if not names: return
        
        self.slot_a_menu.configure(values=names)
        self.slot_b_menu.configure(values=names)
        
        # Sync values
        idx_a = self.slots["A"]
        idx_b = self.slots["B"]
        if idx_a < len(names): self.slot_a_var.set(names[idx_a])
        if idx_b < len(names): self.slot_b_var.set(names[idx_b])

    def _on_slot_selector_change(self, slot, value):
        """Handle dropdown selection."""
        try:
            # Value format "1: filename.png"
            idx = int(value.split(":")[0]) - 1
            if 0 <= idx < len(self.files):
                self._set_slot(slot, idx)
        except: pass

    def _draw_single(self, cw: int, ch: int, index: int):
        """Draw a single focused image with caching."""
        if index >= len(self.images) or self.images[index] is None:
            return
            
        pil_img = self.original_pils[index]
        base_scale = min(cw / pil_img.width, ch / pil_img.height) * 0.98
        scale = base_scale * self.zoom_level
        
        new_w = int(pil_img.width * scale)
        new_h = int(pil_img.height * scale)
        
        if new_w > 0 and new_h > 0:
            # Cache lookup
            cache_key = (index, self.zoom_level, self.current_channel)
            if cache_key in self._resize_cache:
                photo = self._resize_cache[cache_key]
            else:
                img_display = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img_display)
                self._resize_cache[cache_key] = photo
                
            self.photo_images[index] = photo
            
            x = cw // 2 + self.pan_offset[0]
            y = ch // 2 + self.pan_offset[1]
            self.canvas.create_image(x, y, image=photo, anchor="center")
            
            # Label
            name = self.files[index].name
            slot_label = "SLOT A" if self.slots["A"] == index else ("SLOT B" if self.slots["B"] == index else "")
            display_text = f"{name} ({slot_label})" if slot_label else name
            self.canvas.create_text(10, 20, text=display_text, fill="#00b894", anchor="nw", font=("", 12, "bold"))

    def _draw_side_by_side(self, cw: int, ch: int):
        """Draw Slot A and Slot B side by side with caching."""
        idx_a = self.slots["A"]
        idx_b = self.slots["B"]
        
        if idx_a >= len(self.images) or self.images[idx_a] is None: return
        if idx_b >= len(self.images) or self.images[idx_b] is None:
            self._draw_single(cw, ch, idx_a)
            return

        panel_w = cw // 2
        for idx, i in enumerate([idx_a, idx_b]):
            pil_img = self.original_pils[i]
            base_scale = min(panel_w / pil_img.width, ch / pil_img.height) * 0.95
            scale = base_scale * self.zoom_level
            
            new_w = int(pil_img.width * scale)
            new_h = int(pil_img.height * scale)
            
            if new_w > 0 and new_h > 0:
                # Cache lookup
                cache_key = (i, self.zoom_level, self.current_channel, "side")
                if cache_key in self._resize_cache:
                    photo = self._resize_cache[cache_key]
                else:
                    img_display = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img_display)
                    self._resize_cache[cache_key] = photo
                
                self.photo_images[i] = photo
                
                x = idx * panel_w + panel_w // 2 + self.pan_offset[0]
                y = ch // 2 + self.pan_offset[1]
                self.canvas.create_image(x, y, image=photo, anchor="center")

            # Label
            label_y = 20
            name = f"{'A' if idx==0 else 'B'}: {self.files[i].name}"
            self.canvas.create_text(idx * panel_w + 10, label_y, text=name, fill="#00b894", 
                                   anchor="nw", font=("", 10, "bold"))

    def _draw_difference(self, cw: int, ch: int):
        """Draw only the difference result."""
        idx_a, idx_b = self.slots["A"], self.slots["B"]
        if self.images[idx_a] is None or self.images[idx_b] is None:
            return
        
        self._update_stats()
        _, _, _, diff_img, _, _ = self._diff_cache
        
        # Draw focused Diff
        base_scale = min(cw / diff_img.width, ch / diff_img.height) * 0.98
        scale = base_scale * self.zoom_level
        new_w, new_h = int(diff_img.width * scale), int(diff_img.height * scale)
        
        cache_key = ("diff_result", self.zoom_level, self.current_channel)
        if cache_key in self._resize_cache:
            photo = self._resize_cache[cache_key]
        else:
            photo = ImageTk.PhotoImage(diff_img.resize((new_w, new_h), Image.LANCZOS))
            self._resize_cache[cache_key] = photo
            
        x = cw // 2 + self.pan_offset[0]
        y = ch // 2 + self.pan_offset[1]
        self.canvas.create_image(x, y, image=photo, anchor="center")
        self.canvas.create_text(10, 20, text=t("image_compare_gui.diff_result"), fill="#e74c3c", anchor="nw", font=("", 12, "bold"))

    def _draw_slider(self, cw: int, ch: int):
        """Draw slider comparison internally driven."""
        idx_a, idx_b = self.slots["A"], self.slots["B"]
        if self.images[idx_a] is None or self.images[idx_b] is None:
            return
        
        img_a = self.original_pils[idx_a]
        img_b = self.original_pils[idx_b]
        
        base_scale = min(cw / img_a.width, ch / img_a.height) * 0.98
        scale = base_scale * self.zoom_level
        new_w, new_h = int(img_a.width * scale), int(img_a.height * scale)
        
        cache_key_a = (idx_a, self.zoom_level, self.current_channel, "slider")
        cache_key_b = (idx_b, self.zoom_level, self.current_channel, "slider")
        
        res_a = self._resize_cache.get(cache_key_a)
        if not res_a:
            res_a = img_a.resize((new_w, new_h), Image.LANCZOS)
            self._resize_cache[cache_key_a] = res_a
            
        res_b = self._resize_cache.get(cache_key_b)
        if not res_b:
            res_b = img_b.resize((new_w, new_h), Image.LANCZOS)
            self._resize_cache[cache_key_b] = res_b
            
        # Composite using internal slider_pos
        split_x = int(new_w * self.slider_pos)
        
        composite = Image.new("RGB", (new_w, new_h))
        composite.paste(res_a.crop((0, 0, split_x, new_h)), (0, 0))
        composite.paste(res_b.crop((split_x, 0, new_w, new_h)), (split_x, 0))
        
        photo = ImageTk.PhotoImage(composite)
        self.photo_images[0] = photo
        
        cx = cw // 2 + self.pan_offset[0]
        cy = ch // 2 + self.pan_offset[1]
        self.canvas.create_image(cx, cy, image=photo, anchor="center")
        
        line_x = cx - new_w // 2 + split_x
        self.canvas.create_line(line_x, cy - new_h // 2, line_x, cy + new_h // 2, fill="#fff", width=2)
        self.canvas.create_oval(line_x-6, cy-6, line_x+6, cy+6, fill="#00b894", outline="#fff")

    def _draw_grid(self, cw: int, ch: int):
        """Draw 2x2 grid."""
        from features.image.compare_core import array_to_pil
        valid = [(i, img) for i, img in enumerate(self.images) if img is not None]
        if not valid:
            return
        
        # Calculate grid layout
        cols = 2 if len(valid) > 1 else 1
        rows = (len(valid) + cols - 1) // cols
        
        panel_w = cw // cols
        panel_h = ch // rows
        
        for idx, (i, arr) in enumerate(valid):
            row = idx // cols
            col = idx % cols
            
            pil_img = array_to_pil(arr)
            scale = min(panel_w / pil_img.width, panel_h / pil_img.height) * 0.85
            new_w = int(pil_img.width * scale)
            new_h = int(pil_img.height * scale)
            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
            
            photo = ImageTk.PhotoImage(pil_img)
            self.photo_images[i] = photo
            
            x = col * panel_w + panel_w // 2
            y = row * panel_h + panel_h // 2
            self.canvas.create_image(x, y, image=photo, anchor="center")
            
            label = self.files[i].name if i < len(self.files) else f"Image {i+1}"
            self.canvas.create_text(x, row * panel_h + 12, text=label, 
                                   fill="#aaa", font=("Arial", 9))

    def _update_stats(self):
        """Update statistics label with caching."""
        idx_a, idx_b = self.slots["A"], self.slots["B"]
        if idx_a < len(self.images) and idx_b < len(self.images):
            # Check cache
            cache_key = (idx_a, idx_b, self.current_channel)
            if self._diff_cache and self._diff_cache[0:3] == cache_key:
                _, _, _, _, count, ssim = self._diff_cache
            else:
                try:
                    from features.image.compare_core import compute_diff, compute_ssim, array_to_pil
                    img_a, img_b = self.images[idx_a], self.images[idx_b]
                    diff, count = compute_diff(img_a, img_b)
                    ssim = compute_ssim(img_a, img_b)
                    # Cache it
                    diff_img = array_to_pil(diff)
                    self._diff_cache = (idx_a, idx_b, self.current_channel, diff_img, count, ssim)
                except Exception as e:
                    logger.error(f"Stat calculation failed: {e}")
                    self.stats_label.configure(text="")
                    return

            self.stats_label.configure(text=f"{t('image_compare_gui.ssim')}: {ssim:.4f}  |  {t('image_compare_gui.diff_pixels')}: {count:,}")
        else:
            n = len([img for img in self.images if img is not None])
            self.stats_label.configure(text=f"{n} {t('image_common.images_loaded')}")

    def _on_channel_change(self, value):
        """Handle channel selection change."""
        self.current_channel = value
        self._resize_cache.clear()
        self._diff_cache = None
        # Reload all images with new channel
        from features.image.compare_core import load_image, array_to_pil
        for i, f in enumerate(self.files):
            arr = load_image(str(f), self.current_channel)
            if arr is not None:
                self.images[i] = arr
                self.original_pils[i] = array_to_pil(arr)
        self._update_display()

    def _on_mode_change(self, value):
        """Handle mode selection change."""
        self._resize_cache.clear()
        self._update_display()

    def _on_slider_change(self, value):
        """Handle slider movement."""
        self._update_display()

    def _on_mouse_move(self, event):
        """Show pixel info and handle slider cursor."""
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        mode_label = self.mode_var.get()
        mode = self.mode_map.get(mode_label, "Side by Side")
        
        # 1. Update Cursor for Slider
        if mode == "Slider":
            split_x = self._get_slider_split_x(cw)
            if abs(event.x - split_x) < 10:
                self.canvas.configure(cursor="sb_h_double_arrow")
            else:
                self.canvas.configure(cursor="")
        else:
            self.canvas.configure(cursor="")

        # 2. Pixel Info
        img_idx = -1
        cx, cy = 0, 0
        panel_w = cw
        
        if mode == "Single":
            img_idx = self.slots[self.active_slot]
            cx, cy = cw // 2 + self.pan_offset[0], ch // 2 + self.pan_offset[1]
        elif mode == "Side by Side":
            panel_w = cw // 2
            col = 0 if event.x < panel_w else 1
            img_idx = self.slots["A"] if col == 0 else self.slots["B"]
            cx = col * panel_w + panel_w // 2 + self.pan_offset[0]
            cy = ch // 2 + self.pan_offset[1]
        
        if img_idx >= 0 and img_idx < len(self.images) and self.images[img_idx] is not None:
            arr = self.images[img_idx]
            pil_img = self.original_pils[img_idx]
            base_scale = min(panel_w / pil_img.width, ch / pil_img.height) * (0.95 if mode=="Side by Side" else 0.98)
            scale = base_scale * self.zoom_level
            
            rel_x = (event.x - cx) / scale + pil_img.width / 2
            rel_y = (event.y - cy) / scale + pil_img.height / 2
            
            px, py = int(rel_x), int(rel_y)
            if 0 <= px < arr.shape[1] and 0 <= py < arr.shape[0]:
                val = arr[py, px]
                text = f"Pos: {px}, {py} | "
                if len(val) >= 3:
                    rgb = [int(v * 255) for v in val]
                    text += f"RGB: {rgb[0]}, {rgb[1]}, {rgb[2]}"
                else:
                    text += f"Val: {val[0]:.3f}"
                self.pixel_label.configure(text=text, text_color="#00b894")
            else:
                self.pixel_label.configure(text="Outside Image", text_color="#888")

    def _get_slider_split_x(self, cw):
        """Calculate line position using internal slider_pos."""
        idx_a = self.slots["A"]
        if idx_a >= len(self.original_pils): return cw // 2
        pil_img = self.original_pils[idx_a]
        ch = self.canvas.winfo_height()
        base_scale = min(cw / pil_img.width, ch / pil_img.height) * 0.98
        scale = base_scale * self.zoom_level
        new_w = int(pil_img.width * scale)
        
        cx = cw // 2 + self.pan_offset[0]
        return cx - new_w // 2 + int(new_w * self.slider_pos)

    def _on_scroll(self, event):
        """Handle mouse wheel for zoom."""
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()

    def _zoom_in(self):
        """Increase zoom level."""
        self.zoom_level = min(20.0, self.zoom_level * 1.2)
        self._update_display()

    def _zoom_out(self):
        """Decrease zoom level."""
        self.zoom_level = max(0.05, self.zoom_level / 1.2)
        self._update_display()

    def _on_click(self, event):
        """Handle click for flip (Single) or slider drag."""
        mode = self.mode_var.get()
        if mode == "Single":
            self._toggle_slots()
            return
            
        if mode == "Slider":
            cw = self.canvas.winfo_width()
            split_x = self._get_slider_split_x(cw)
            if abs(event.x - split_x) < 20:
                self._dragging_slider = True
                return
        
        self._drag_start = (event.x, event.y)
        self._dragging_slider = False

    def _on_drag(self, event):
        """Handle drag for panning or slider move."""
        if self._dragging_slider:
            cw = self.canvas.winfo_width()
            idx_a = self.slots["A"]
            pil_img = self.original_pils[idx_a]
            ch = self.canvas.winfo_height()
            base_scale = min(cw / pil_img.width, ch / pil_img.height) * 0.98
            scale = base_scale * self.zoom_level
            new_w = int(pil_img.width * scale)
            
            cx = cw // 2 + self.pan_offset[0]
            rel_pos = (event.x - (cx - new_w // 2)) / new_w
            self.slider_pos = max(0, min(1, rel_pos))
            self._update_display()
            return

        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        self.pan_offset[0] += dx
        self.pan_offset[1] += dy
        self._drag_start = (event.x, event.y)
        self._update_display()

    def _on_resize(self, event):
        """Handle canvas resize."""
        self.after(100, self._update_display)

    def _add_image(self):
        """Add image via file dialog."""
        filetypes = [
            ("Images", "*.png *.jpg *.jpeg *.exr *.tiff *.tga *.bmp"),
            ("All files", "*.*")
        ]
        paths = filedialog.askopenfilenames(filetypes=filetypes)
        if paths:
            for path in paths:
                self._add_image_to_slots(path)
            self._update_display()
            self._update_slot_selectors()
            
    def _replace_image(self, index: int):
        """Replace image at index via file dialog."""
        filetypes = [
            ("Images", "*.png *.jpg *.jpeg *.exr *.tiff *.tga *.bmp"),
            ("All files", "*.*")
        ]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            from features.image.compare_core import load_image, array_to_pil
            arr = load_image(path, self.current_channel)
            if arr is not None:
                self.images[index] = arr
                pil = array_to_pil(arr)
                self.original_pils[index] = pil
                self.files[index] = Path(path)
                
                # Update thumbnail removed
                
                self._update_display()
                self._update_slot_selectors()

    def _remove_image(self, index: int):
        """Remove image at index."""
        if 0 <= index < len(self.images):
            self.images.pop(index)
            self.original_pils.pop(index)
            self.photo_images.pop(index)
            # Thumbnails removed
            self.files.pop(index)
            
            # Clean up slots if they point to removed index
            if self.slots["A"] == index: self.slots["A"] = 0
            if self.slots["B"] == index: self.slots["B"] = 0
            
            self._update_display()
            self._update_slot_selectors()

    def _reset_zoom(self):
        """Reset zoom to 100%."""
        self.zoom_level = 1.0
        self.pan_offset = [0, 0]
        self._update_display()


def launch_compare_gui(target_path: str = None, selection=None):
    """Entry point for menu.py"""
    from utils.batch_runner import collect_batch_context
    
    paths = collect_batch_context("image_compare", target_path, timeout=1.5)
    if not paths:
        return
    
    # Filter to image files
    image_exts = {".png", ".jpg", ".jpeg", ".exr", ".tiff", ".tif", ".tga", ".bmp"}
    images = [p for p in paths if Path(p).suffix.lower() in image_exts]
    
    if not images:
        messagebox.showwarning("Warning", "이미지 파일을 선택해주세요.")
        return
    
    gui = ImageCompareGUI(images)
    gui.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        files = [arg for arg in sys.argv[1:] if Path(arg).exists()]
        if files:
            gui = ImageCompareGUI(files)
            gui.mainloop()
    else:
        print("Usage: compare_gui.py <image1> [image2] [image3] [image4]")
