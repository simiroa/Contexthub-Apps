"""
Image Converter GUI - High Performance Edition
Fast multi-file conversion with multi-threading and instant Explorer selection.
"""
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

# === FAST IMPORTS - delay heavy modules ===
# Only import what's needed for startup
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/image -> src
sys.path.append(str(src_dir))

def _is_headless():
    return os.environ.get("CTX_HEADLESS") == "1" or os.environ.get("CTX_CAPTURE_MODE") == "1"


def get_all_selected_files(anchor_path: str) -> list[Path]:
    """Get all selected files from Explorer using COM - INSTANT."""
    try:
        from utils.explorer import get_selection_from_explorer
        selected = get_selection_from_explorer(anchor_path)
        if selected and len(selected) > 0:
            return selected
    except Exception as e:
        print(f"Explorer selection failed: {e}")
    return [Path(anchor_path)]


def main():
    """Main entry - imports heavy modules only when needed."""
    import customtkinter as ctk
    from PIL import Image, ImageOps
    from tkinter import messagebox, filedialog
    import threading
    
    from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_TEXT_DIM, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, THEME_BTN_PRIMARY, THEME_BTN_HOVER
    from utils.image_utils import scan_for_images
    from utils.i18n import t
    from core.config import MenuConfig
    from utils.logger import setup_logger
    
    logger = setup_logger("image_converter")

    
    class ImageConverterGUI(BaseWindow):
        def __init__(self, files_list=None):
            # Sync Name
            self.tool_name = "ContextUp Image Converter"
            try:
                 config = MenuConfig()
                 item = config.get_item_by_id("image_convert")
                 if item: self.tool_name = item.get("name", self.tool_name)
            except: pass

            super().__init__(title=self.tool_name, width=450, height=500, scrollable=False, icon_name="image_format_convert")
            
            if files_list and len(files_list) > 0:
                self.selection, _ = scan_for_images(files_list)
            else:
                self.selection = []
            
            if not self.selection:
                if _is_headless():
                    self.selection = [Path("demo_image.png")]
                else:
                    messagebox.showerror(t("common.error"), t("image_convert_gui.no_valid_images"))
                    self.destroy()
                    return
            
            self.fmt_var = ctk.StringVar(value="PNG")
            self.resize_enabled = ctk.BooleanVar(value=False)
            self.resize_size = ctk.StringVar(value="1024")
            
            self.create_widgets()
            self.update_preview()
            self.after(100, self.adjust_window_size)

        def create_widgets(self):
            # 1. Header
            self.add_header(t("image_convert_gui.header") + f" ({len(self.selection)})", font_size=20)
            
            # 2. File List
            from utils.gui_lib import FileListFrame
            self.file_list = FileListFrame(self.main_frame, self.selection, height=180)
            self.file_list.pack(fill="x", padx=20, pady=(0, 10))
            
            # 3. Parameters (2-Column Grid)
            param_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            param_frame.pack(fill="x", padx=20, pady=5)
            param_frame.grid_columnconfigure(0, weight=1)
            param_frame.grid_columnconfigure(1, weight=1)

            # Left Column (Format)
            left_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
            left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            
            ctk.CTkLabel(left_frame, text=t("image_convert_gui.format_label"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
            formats = ["PNG", "JPG", "WEBP", "BMP", "TGA", "TIFF", "ICO", "DDS", "EXR"]
            ctk.CTkOptionMenu(left_frame, variable=self.fmt_var, values=formats, command=lambda _: self.update_preview(),
                              fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER).pack(fill="x", pady=(0, 5))
            
            # Right Column (Resize)
            right_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
            right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
            
            self.chk_resize = ctk.CTkCheckBox(right_frame, text="Resize (px):", variable=self.resize_enabled, 
                                              fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER, command=self.on_resize_toggle)
            self.chk_resize.pack(anchor="w", pady=(5, 2))
            
            self.opt_size = ctk.CTkComboBox(right_frame, variable=self.resize_size, values=["256", "512", "1024", "2048", "4096"], state="disabled")
            self.opt_size.pack(fill="x", pady=(0, 5))

            # 4. Footer (Centralized)
            self.progress = ctk.CTkProgressBar(self.footer_frame, height=10)
            self.progress.pack(fill="x", pady=(0, 15))
            self.progress.set(0)
            
            # Options
            opt_row = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
            opt_row.pack(fill="x", pady=(0, 15))
            
            self.var_new_folder = ctk.BooleanVar(value=False)
            self.var_delete_org = ctk.BooleanVar(value=False)
            
            ctk.CTkCheckBox(opt_row, text=t("image_convert_gui.save_to_folder"), variable=self.var_new_folder).pack(side="left", padx=(0, 20))
            ctk.CTkCheckBox(opt_row, text=t("image_convert_gui.delete_original"), variable=self.var_delete_org, 
                           text_color="#E74C3C").pack(side="left")
            
            # Buttons
            btn_row = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
            btn_row.pack(fill="x")
            
            self.btn_cancel = ctk.CTkButton(btn_row, text=t("common.cancel"), height=45, fg_color="transparent", 
                                            border_width=1, border_color=THEME_BORDER, text_color=("gray10", "gray90"), command=self.destroy)
            self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))
            
            self.btn_convert = ctk.CTkButton(btn_row, text=t("image_convert_gui.convert_all"), height=45, 
                                            font=ctk.CTkFont(size=14, weight="bold"), 
                                            command=self.run_conversion)
            self.btn_convert.pack(side="left", fill="x", expand=True, padx=(0, 0))
            
            self.lbl_status = ctk.CTkLabel(self.footer_frame, text=t("common.ready"), text_color=THEME_TEXT_DIM, font=("", 11))
            self.lbl_status.pack(pady=(5, 0))

        def add_files(self):
            filetypes = [
                ("All Supported Images", "*.png *.jpg *.jpeg *.bmp *.tga *.webp *.tiff *.ico *.exr *.ai *.svg *.hdr *.heic *.avif *.psd *.dds *.cr2 *.nef *.arw *.dng *.orf *.raf"),
                ("Web/Standard", "*.png *.jpg *.jpeg *.webp *.gif *.ico"),
                ("Professional/HDR", "*.exr *.hdr *.psd *.tif *.tiff *.dds *.tga"),
                ("RAW/Camera", "*.cr2 *.nef *.arw *.dng *.orf *.rw2 *.raf *.sr2"),
                ("Vector/PDF", "*.ai *.svg *.pdf *.eps"),
                ("HEIF/AVIF", "*.heic *.avif"),
                ("All Files", "*.*")
            ]
            files = filedialog.askopenfilenames(title="Add Images", filetypes=filetypes)
            if files:
                for f in files:
                    p = Path(f)
                    if p not in self.selection:
                        self.selection.append(p)
                self.update_preview()

        def on_resize_toggle(self):
            self.opt_size.configure(state="normal" if self.resize_enabled.get() else "disabled")

        def update_preview(self):
            for widget in self.file_list.winfo_children():
                widget.destroy()
            
            target_fmt = self.fmt_var.get().lower()
            target_ext = ".jpg" if target_fmt == "jpg" else f".{target_fmt}"
            
            max_display = 8
            for path in self.selection[:max_display]:
                row = ctk.CTkFrame(self.file_list, fg_color="transparent", height=22)
                row.pack(fill="x", pady=1)
                
                src = path.name[:28] + "..." if len(path.name) > 28 else path.name
                tgt = (path.stem + target_ext)[:28]
                
                ctk.CTkLabel(row, text=src, font=("", 10), text_color="gray", anchor="w", width=150).pack(side="left")
                ctk.CTkLabel(row, text="->", font=("", 10), text_color="gray", width=20).pack(side="left")
                ctk.CTkLabel(row, text=tgt, font=("", 10), text_color="#4da6ff", anchor="w").pack(side="left")
            
            remaining = len(self.selection) - max_display
            if remaining > 0:
                ctk.CTkLabel(self.file_list, text=f"... +{remaining} more", 
                            text_color="gray", font=("", 10)).pack(anchor="w", pady=3)
            
            self.btn_convert.configure(text=f"Convert {len(self.selection)} files")

        def run_conversion(self):
            if not self.selection:
                return
            
            target_fmt = self.fmt_var.get().lower()
            if target_fmt == "jpg":
                target_fmt = "jpeg"
            
            resize_size = None
            if self.resize_enabled.get():
                try:
                    resize_size = int(self.resize_size.get())
                except:
                    pass
            
            # Always use max threads
            threads = multiprocessing.cpu_count()
            
            self.btn_convert.configure(state="disabled", text=f"Converting... ({threads} threads)")
            self.progress.set(0)
            
            def _process_all():
                """Process all files using thread pool."""
                args_list = [(p, target_fmt, resize_size) for p in self.selection]
                
                # Check options
                save_new_folder = self.var_new_folder.get()
                delete_original = self.var_delete_org.get()
                
                success = 0
                errors = []
                total = len(args_list)
                completed = 0
                
                with ThreadPoolExecutor(max_workers=threads) as executor:
                    # Modify args to include new options if needed, but for now we handle path calculation inside convert_single?
                    # Actually convert_single needs to know about the output folder.
                    # Let's redefine convert_single to accept output_dir
                    
                    # Prepare output directories first
                    output_map = {} # src_path -> out_path
                    
                    for src, fmt, _ in args_list:
                        out_dir = src.parent
                        if save_new_folder:
                            out_dir = src.parent / "Converted_Images"
                            out_dir.mkdir(exist_ok=True)
                            
                        # Calculate output path
                        new_ext = ".jpg" if fmt == "jpeg" else f".{fmt}"
                        new_path = out_dir / src.with_suffix(new_ext).name
                        if new_path == src:
                            new_path = out_dir / f"{src.stem}_converted{new_ext}"
                            
                        output_map[src] = new_path
                        
                    # Re-pack arguments for the worker
                    worker_args = []
                    for src, fmt, sz in args_list:
                        worker_args.append((src, fmt, sz, output_map[src]))
                        
                    futures = [executor.submit(convert_single_v2, args) for args in worker_args]
                    
                    for i, future in enumerate(futures):
                        src_path = args_list[i][0]
                        result = future.result()
                        completed += 1
                        
                        if result[0]:
                            success += 1
                            # Handle Deletion
                            if delete_original and src_path.exists():
                                try:
                                    os.remove(src_path)
                                except Exception as e:
                                    errors.append(f"Delete failed: {src_path.name} ({e})")
                        else:
                            errors.append(result[1])
                        
                        # Update progress
                        self.after(0, lambda v=completed/total: self.progress.set(v))
                
                self.after(0, lambda: self.finish_conversion(success, errors))
            
            def convert_single_v2(args):
                path, target_fmt, resize_size, out_path = args
                try:
                    # LOAD
                    img = Image.open(path)
                    img.load()

                    # Handle alpha for matching formats
                    if target_fmt in ['jpeg', 'bmp'] and img.mode in ('RGBA', 'LA', 'P'):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        if 'A' in img.getbands():
                            bg.paste(img, mask=img.split()[-1])
                        else:
                            bg.paste(img)
                        img = bg
                    elif target_fmt in ['jpeg', 'bmp'] and img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                    
                    if target_fmt == "ico" and (img.size[0] > 256 or img.size[1] > 256):
                        img = ImageOps.contain(img, (256, 256), method=Image.Resampling.LANCZOS)
                    
                    if resize_size:
                        w, h = img.size
                        if w >= h:
                            new_w, new_h = resize_size, int(h * (resize_size / w))
                        else:
                            new_h, new_w = resize_size, int(w * (resize_size / h))
                        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    
                    # Save
                    save_kwargs = {}
                    if target_fmt == "jpeg":
                        save_kwargs['quality'] = 95
                        save_kwargs['optimize'] = True
                    elif target_fmt == "webp":
                        save_kwargs['quality'] = 90
                        save_kwargs['method'] = 6
                    elif target_fmt == "exr":
                        # Use OpenEXR for saving
                        try:
                            import OpenEXR
                            import Imath
                            import numpy as np
                            
                            # Convert to linear float32
                            img_rgb = img.convert('RGB') if img.mode != 'RGB' else img
                            arr = np.array(img_rgb, dtype=np.float32) / 255.0
                            
                            # Remove sRGB gamma (convert to linear)
                            arr = np.power(arr, 2.2)
                            
                            h, w = arr.shape[:2]
                            header = OpenEXR.Header(w, h)
                            header['compression'] = Imath.Compression(Imath.Compression.PIZ_COMPRESSION)
                            
                            header['channels']['R'] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
                            header['channels']['G'] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
                            header['channels']['B'] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
                            
                            exr_out = OpenEXR.OutputFile(str(out_path), header)
                            exr_out.writePixels({
                                'R': arr[:,:,0].tobytes(),
                                'G': arr[:,:,1].tobytes(),
                                'B': arr[:,:,2].tobytes()
                            })
                            exr_out.close()
                            return (True, None)
                        except ImportError:
                            return (False, f"{path.name}: OpenEXR module not installed")
                    
                    img.save(out_path, **save_kwargs)
                    return (True, None)
                    
                except Exception as e:
                    return (False, f"{path.name}: {e}")

            threading.Thread(target=_process_all, daemon=True).start()

        def finish_conversion(self, count, errors):
            self.progress.set(1)
            self.lbl_status.configure(text="Complete")
            
            msg = f"Converted {count} image{'s' if count != 1 else ''}."
            if errors:
                msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    msg += "\n..."
                messagebox.showwarning("Done with Errors", msg)
            else:
                messagebox.showinfo("Success", msg)
            
            self.destroy()
    
    return ImageConverterGUI


if __name__ == "__main__":
    if len(sys.argv) > 1:
        anchor = sys.argv[1]

        # STEP 1: Get ALL selected files instantly via Explorer COM
        all_files = get_all_selected_files(anchor)
        if len(sys.argv) > 2:
            cli_files = [Path(p) for p in sys.argv[1:] if Path(p).exists()]
            if len(all_files) <= 1 and len(cli_files) > 1:
                all_files = cli_files

        # STEP 2: Mutex - ensure only one GUI window opens
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("image_convert", anchor, timeout=0.2) is None:
            sys.exit(0)

        # STEP 3: Launch GUI with complete file list
        ImageConverterGUI = main()
        app = ImageConverterGUI(all_files)
        app.mainloop()
    else:
        ImageConverterGUI = main()
        app = ImageConverterGUI([])
        app.mainloop()
