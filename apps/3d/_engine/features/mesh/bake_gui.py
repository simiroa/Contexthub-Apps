"""
Blender Texture Baker & Remesher
Separated from AutoLOD functionality.
Decimates a high-poly mesh to a target count and bakes textures using Blender.
"""
import customtkinter as ctk
from tkinter import messagebox
import threading
import sys
import os
from pathlib import Path
import subprocess

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent  # features/mesh -> src
sys.path.append(str(src_dir))

import logging
from utils.gui_lib import BaseWindow, FileListFrame, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, run_silent_command
from utils.explorer import get_selection_from_explorer
from utils.external_tools import get_blender
from utils.i18n import t

def _is_headless():
    return os.environ.get("CTX_HEADLESS") == "1" or os.environ.get("CTX_CAPTURE_MODE") == "1"

# Setup logging
log_file = Path(__file__).parent.parent.parent / "debug_bake.log"
logging.basicConfig(filename=str(log_file), level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class BlenderBakeGUI(BaseWindow):
    def __init__(self, target_path):
        super().__init__(title="ContextUp Remesh & Bake", width=550, height=600, scrollable=True, icon_name="mesh_remesh_bake")
        
        logging.info(f"Initializing BlenderBakeGUI with target: {target_path}")
        
        self.demo_mode = _is_headless()
        mesh_exts = {'.obj', '.ply', '.stl', '.off', '.gltf', '.glb', '.fbx'}
        if self.demo_mode:
            self.files = [Path("demo_mesh.obj")]
            self.create_widgets()
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            return

        if isinstance(target_path, (list, tuple)):
            self.selection = [Path(p) for p in target_path]
        else:
            self.target_path = Path(target_path) if target_path else Path.cwd()
            if self.target_path.is_file() and self.target_path.suffix.lower() in mesh_exts:
                self.selection = [self.target_path]
            else:
                self.selection = get_selection_from_explorer(target_path)
                if not self.selection:
                    self.selection = [self.target_path]
                
        logging.info(f"Selection: {self.selection}")
        
        self.files = [Path(p) for p in self.selection if Path(p).suffix.lower() in mesh_exts]
        
        if not self.files:
            messagebox.showerror(t("common.error"), t("blender_bake.no_files"))
            self.destroy()
            return

        if not self.check_pymeshlab():
            return

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.after(100, self.adjust_window_size)
        
        # Start analysis
        threading.Thread(target=self.analyze_inputs, daemon=True).start()

    def check_pymeshlab(self):
        try:
            import pymeshlab
            self.pymeshlab = pymeshlab
            return True
        except ImportError:
            if messagebox.askyesno("Dependency Error", "PyMeshLab not found. Install now?"):
                run_silent_command([sys.executable, "-m", "pip", "install", "pymeshlab"])
                try:
                    import pymeshlab
                    self.pymeshlab = pymeshlab
                    return True
                except:
                    messagebox.showerror(t("common.error"), t("blender_bake.install_failed"))
                    self.destroy()
                    return False
            self.destroy()
            return False

    def create_widgets(self):
        # 1. Header
        self.add_header(t("blender_bake.header") + f" ({len(self.files)})", font_size=20)
        
        # 2. File List
        self.file_scroll = FileListFrame(self.main_frame, self.files, height=130)
        self.file_scroll.pack(fill="x", padx=20, pady=(0, 10))
        
        # Analysis Label
        self.lbl_analysis = ctk.CTkLabel(self.main_frame, text="Analyzing input...", text_color="gray", anchor="w")
        self.lbl_analysis.pack(fill="x", padx=25, pady=(0, 10))

        # 3. Parameters
        param_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        param_frame.pack(fill="x", padx=20, pady=5)
        param_frame.grid_columnconfigure(0, weight=1)
        param_frame.grid_columnconfigure(1, weight=1)
        
        # Left Column: Remesh Settings
        left_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(left_frame, text=t("blender_bake.target_faces"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.var_target_count = ctk.StringVar(value="10000")
        ctk.CTkEntry(left_frame, textvariable=self.var_target_count).pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(left_frame, text=t("blender_bake.preservation"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.var_uv = ctk.BooleanVar(value=True)
        self.var_normal = ctk.BooleanVar(value=True)
        self.var_boundary = ctk.BooleanVar(value=True)
        
        chk_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        chk_frame.pack(fill="x")
        ctk.CTkCheckBox(chk_frame, text=t("blender_bake.uvs"), variable=self.var_uv).pack(anchor="w", pady=2)
        ctk.CTkCheckBox(chk_frame, text=t("blender_bake.normal"), variable=self.var_normal).pack(anchor="w", pady=2)
        ctk.CTkCheckBox(chk_frame, text=t("blender_bake.boundary"), variable=self.var_boundary).pack(anchor="w", pady=2)

        # Right Column: Bake Settings
        right_frame = ctk.CTkFrame(param_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(right_frame, text=t("blender_bake.resolution"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.var_bake_size = ctk.StringVar(value="2048")
        ctk.CTkComboBox(right_frame, variable=self.var_bake_size, values=["1024", "2048", "4096", "8192"],
                        fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER).pack(fill="x", pady=(0, 10))
        
        grid_sub = ctk.CTkFrame(right_frame, fg_color="transparent")
        grid_sub.pack(fill="x", pady=0)
        grid_sub.columnconfigure(0, weight=1)
        grid_sub.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(grid_sub, text=t("blender_bake.ray_dist")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(grid_sub, text=t("blender_bake.margin")).grid(row=0, column=1, sticky="w")
        
        self.var_ray_dist = ctk.StringVar(value="0.1")
        ctk.CTkEntry(grid_sub, textvariable=self.var_ray_dist).grid(row=1, column=0, sticky="ew", padx=(0, 5))
        
        self.var_margin = ctk.StringVar(value="16")
        ctk.CTkEntry(grid_sub, textvariable=self.var_margin).grid(row=1, column=1, sticky="ew", padx=(5, 0))

        # 4. Map Types
        map_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        map_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(map_frame, text=t("blender_bake.output_maps"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        
        row1 = ctk.CTkFrame(map_frame, fg_color="transparent")
        row1.pack(fill="x")
        self.var_bake_normal = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row1, text=t("blender_bake.normal"), variable=self.var_bake_normal).pack(side="left", padx=(0, 15))
        self.var_flip_green = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row1, text=t("blender_bake.flip_green"), variable=self.var_flip_green).pack(side="left")
        
        row2 = ctk.CTkFrame(map_frame, fg_color="transparent")
        row2.pack(fill="x", pady=(5, 0))
        self.var_bake_diffuse = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row2, text=t("blender_bake.diffuse"), variable=self.var_bake_diffuse).pack(side="left", padx=(0, 15))
        self.var_bake_orm = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row2, text=t("blender_bake.orm_pack"), variable=self.var_bake_orm).pack(side="left")

        # 5. Footer (Centralized)
        self.progress = ctk.CTkProgressBar(self.footer_frame, height=10)
        self.progress.pack(fill="x", pady=(0, 15))
        self.progress.set(0)
        
        btn_row = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        btn_row.pack(fill="x")
        
        self.btn_cancel = ctk.CTkButton(btn_row, text=t("common.cancel"), height=45, fg_color="transparent", 
                                         border_width=1, border_color=THEME_BORDER, text_color=("gray10", "gray90"), command=self.on_closing)
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_run = ctk.CTkButton(btn_row, text=t("blender_bake.run_btn"), height=45, 
                                    font=ctk.CTkFont(size=14, weight="bold"), 
                                    fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER,
                                    command=self.start_process)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 0))
        
        self.lbl_status = ctk.CTkLabel(self.main_frame, text=t("common.ready"), text_color="gray", font=("", 11))
        self.lbl_status.pack(pady=(0, 5))

    def analyze_inputs(self):
        try:
            ms = self.pymeshlab.MeshSet()
            path = self.files[0]
            ms.load_new_mesh(str(path))
            m = ms.current_mesh()
            faces = m.face_number()
            has_uv = m.has_wedge_tex_coord()
            
            msg = f"Input: {path.name} | Faces: {faces:,}"
            if not has_uv:
                msg += " | Warning: No UVs detected!"
                self.lbl_analysis.configure(text_color="orange")
            else:
                msg += " | UVs detected"
            
            self.lbl_analysis.configure(text=msg)
        except Exception as e:
            self.lbl_analysis.configure(text=f"Analysis error: {e}")

    def get_blender_path(self):
        try: return get_blender()
        except: return None

    def start_process(self):
        blender = self.get_blender_path()
        if not blender:
            messagebox.showerror("Error", "Blender not found. Baking requires Blender.")
            return

        params = {
            'target_count': int(self.var_target_count.get()),
            'preserve_uv': self.var_uv.get(),
            'preserve_normal': self.var_normal.get(),
            'preserve_boundary': self.var_boundary.get(),
            'size': self.var_bake_size.get(),
            'ray_dist': self.var_ray_dist.get(),
            'margin': self.var_margin.get(),
            'bake_normal': self.var_bake_normal.get(),
            'flip_green': self.var_flip_green.get(),
            'bake_diffuse': self.var_bake_diffuse.get(),
            'bake_orm': self.var_bake_orm.get(),
            'blender_exe': blender
        }
        
        self.btn_run.configure(state="disabled", text="Processing...")
        self.btn_cancel.configure(state="disabled")
        self.progress.set(0)
        threading.Thread(target=self.run_generation, args=(params,), daemon=True).start()

    def run_generation(self, params):
        ms = self.pymeshlab.MeshSet()
        total = len(self.files)
        
        for i, path in enumerate(self.files):
            self.update_status(f"Processing {i+1}/{total}: {path.name}")
            
            try:
                ms.clear()
                ms.load_new_mesh(str(path))
                filter_name = 'meshing_decimation_quadric_edge_collapse'
                if params['preserve_uv']:
                    filter_name += '_with_texture'
                
                try:
                    ms.apply_filter(filter_name, 
                                  targetfacenum=params['target_count'],
                                  preserveboundary=params['preserve_boundary'],
                                  preservenormal=params['preserve_normal'])
                except Exception as e:
                    logging.error(f"Decimation error: {e}")
                
                stem = path.stem.split("_LOD")[0]
                out_dir = path.parent
                low_path = out_dir / f"{stem}_LowPoly.obj"
                ms.save_current_mesh(str(low_path))
                
                self.update_status("Baking in Blender...")
                bake_script = src_dir / "blender_scripts" / "blender_bake.py"
                bake_out = out_dir / f"{stem}_Bake_Normal.png"
                
                cmd = [
                    str(params['blender_exe']),
                    "--background", "--python", str(bake_script), "--",
                    "--high", str(path),
                    "--low", str(low_path),
                    "--out", str(bake_out),
                    "--size", str(params['size']),
                    "--ray_dist", str(params['ray_dist']),
                    "--margin", str(params['margin'])
                ]
                
                if params['bake_normal']: cmd.append("--bake_normal")
                if params['flip_green']: cmd.append("--flip_green")
                if params['bake_diffuse']: cmd.append("--bake_diffuse")
                if params['bake_orm']: cmd.append("--bake_orm")
                
                result = run_silent_command(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logging.error(f"Blender Error: {result.stderr}")
                    raise Exception(f"Blender bake failed: {result.stderr}")
                    
            except Exception as e:
                logging.error(f"Process failed: {e}")
                
            self.progress.set((i+1)/total)
            
        self.after(0, lambda: self.finish())

    def update_status(self, text):
        self.lbl_status.configure(text=text)

    def finish(self):
        self.btn_run.configure(state="normal", text=t("blender_bake.run_btn"))
        self.btn_cancel.configure(state="normal")
        self.lbl_status.configure(text=t("common.complete"))
        messagebox.showinfo(t("common.success"), t("common.complete"))
        self.destroy()

    def on_closing(self):
        self.destroy()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        anchor = sys.argv[1]
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("blender_bake_gui", anchor, timeout=0.2) is None:
            sys.exit(0)

        paths = [Path(p) for p in sys.argv[1:] if Path(p).exists()]
        app = BlenderBakeGUI(paths if len(paths) > 1 else paths[0])
        app.mainloop()
    else:
        app = BlenderBakeGUI(None)
        app.mainloop()
