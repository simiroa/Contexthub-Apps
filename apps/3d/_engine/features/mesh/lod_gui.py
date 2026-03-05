"""
Auto LOD Generator using PyMeshLab
Generates LODs (Level of Detail) for 3D meshes.
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

# Setup logging
log_file = Path(__file__).parent.parent.parent / "debug_gui.log"
logging.basicConfig(filename=str(log_file), level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

from utils.gui_lib import BaseWindow, THEME_CARD, THEME_BORDER, THEME_BTN_PRIMARY, THEME_BTN_HOVER, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER, run_silent_command
from utils.explorer import get_selection_from_explorer
from utils.external_tools import get_blender
from utils.i18n import t

def _is_headless():
    return os.environ.get("CTX_HEADLESS") == "1" or os.environ.get("CTX_CAPTURE_MODE") == "1"

class AutoLODGUI(BaseWindow):
    def __init__(self, target_path, demo=False):
        logging.info(f"Initializing AutoLODGUI with target: {target_path}")
        try:
            super().__init__(title=t("mesh_lod_gui.title"), width=500, height=480, icon_name="mesh_lod")
            logging.info("BaseWindow init complete")
            
            self.demo_mode = demo or _is_headless()
            
            # Demo mode: skip validation
            if self.demo_mode:
                self.files = [Path("demo_mesh.obj")]
                self.pymeshlab = None  # Mock
                self.create_widgets()
                self.protocol("WM_DELETE_WINDOW", self.on_closing)
                return
            
            # Handle multiple targets
            if isinstance(target_path, (list, tuple)):
                self.selection = [Path(p) for p in target_path]
            else:
                self.target_path = Path(target_path) if target_path else Path.cwd()
                mesh_exts = {'.obj', '.ply', '.stl', '.off', '.gltf', '.glb', '.fbx'} 
                if self.target_path.is_file() and self.target_path.suffix.lower() in mesh_exts:
                    self.selection = [self.target_path]
                else:
                    self.selection = get_selection_from_explorer(target_path)
                    if not self.selection:
                        self.selection = [self.target_path]
            
            logging.info(f"Selection: {self.selection}")
            
            self.files = [Path(p) for p in self.selection if Path(p).suffix.lower() in mesh_exts]
            logging.info(f"Filtered files: {self.files}")
            
            if not self.files:
                logging.error("No supported mesh files found.")
                # Show error but don't crash immediately, maybe allow browsing?
                # For now, just show error and close safely
                messagebox.showerror("Error", "No supported mesh files selected.\n(Supported: OBJ, PLY, STL, GLTF, FBX)")
                self.destroy()
                return

            if not self.check_pymeshlab():
                logging.error("PyMeshLab check failed")
                return

            self.create_widgets()
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            logging.info("Initialization complete, entering mainloop")
        except Exception as e:
            logging.exception("Error during initialization")
            # Ensure we don't hang
            try: self.destroy()
            except: pass
            raise e

    def check_pymeshlab(self):
        """
        Check if PyMeshLab is installed and provide user-friendly guidance if not.
        Simplified logic with clear error messages.
        """
        logging.info("Checking PyMeshLab dependency...")
        
        # Step 1: Try to import PyMeshLab
        try:
            import pymeshlab
            self.pymeshlab = pymeshlab
            logging.info("PyMeshLab found.")
            return True
        except ImportError:
            logging.warning("PyMeshLab not found in current environment.")
        
        # Step 2: Show user-friendly dialog with options
        msg = (
            "🔧 PyMeshLab이 설치되지 않았습니다.\n\n"
            "PyMeshLab은 3D 메시 처리에 필수적인 라이브러리입니다.\n\n"
            "지금 설치하시겠습니까?\n"
            "(pip install pymeshlab 실행)"
        )
        
        if not messagebox.askyesno("의존성 설치 필요", msg):
            logging.info("User declined PyMeshLab installation.")
            self.destroy()
            return False
        
        # Step 3: Try to install PyMeshLab
        try:
            logging.info("Installing PyMeshLab...")
            
            # Show progress dialog - simple version
            progress_msg = "PyMeshLab 설치 중...\n\n이 작업은 몇 분 정도 소요될 수 있습니다."
            messagebox.showinfo("설치 중", progress_msg)
            
            # Run pip install
            result = run_silent_command(
                [sys.executable, "-m", "pip", "install", "pymeshlab"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = (
                    f"PyMeshLab 설치에 실패했습니다.\n\n"
                    f"에러:\n{result.stderr[:500]}\n\n"
                    f"수동 설치 방법:\n"
                    f"1. 명령 프롬프트 실행 (관리자 권한)\n"
                    f"2. pip install pymeshlab 입력"
                )
                logging.error(f"pip install failed: {result.stderr}")
                messagebox.showerror("설치 실패", error_msg)
                self.destroy()
                return False
            
            # Step 4: Verify installation
            import pymeshlab
            self.pymeshlab = pymeshlab
            messagebox.showinfo("설치 완료", "PyMeshLab이 성공적으로 설치되었습니다!")
            logging.info("PyMeshLab installed successfully.")
            return True
            
        except subprocess.TimeoutExpired:
            error_msg = (
                "설치 시간이 초과되었습니다.\n\n"
                "네트워크 연결을 확인하시고 다시 시도해주세요."
            )
            logging.error("pip install timeout")
            messagebox.showerror("설치 시간 초과", error_msg)
            self.destroy()
            return False
            
        except Exception as e:
            error_msg = (
                f"PyMeshLab 설치 중 오류가 발생했습니다.\n\n"
                f"에러: {e}\n\n"
                f"수동 설치 방법:\n"
                f"명령 프롬프트에서 'pip install pymeshlab' 실행"
            )
            logging.error(f"Failed to install PyMeshLab: {e}")
            messagebox.showerror("설치 오류", error_msg)
            self.destroy()
            return False

    def get_embedded_python(self):
        """Get path to embedded Python if available. (Deprecated - kept for compatibility)"""
        try:
            script_dir = Path(__file__).parent
            tools_dir = script_dir.parent.parent / "tools"
            python_exe = tools_dir / "python" / "python.exe"
            if python_exe.exists():
                return python_exe
        except:
            pass
        return None


    def create_widgets(self):
        # Main Container
        self.main_frame.pack_configure(padx=5, pady=5)
        
        # Header
        self.add_header(t("mesh_lod_gui.header") + f" ({len(self.files)})", font_size=16)
        
        # Analysis
        self.lbl_analysis = ctk.CTkLabel(self.main_frame, text=t("mesh_lod_gui.analyzing"), text_color="gray", justify="center")
        self.lbl_analysis.pack(pady=(0, 5))
        
        # Center Content (LOD Settings)
        content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=5)
        
        # LOD Count
        ctk.CTkLabel(content, text=t("mesh_lod_gui.lod_count"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=15, sticky="e")
        self.var_lod_count = ctk.IntVar(value=3)
        ctk.CTkComboBox(content, variable=self.var_lod_count, values=["2", "3", "4", "5"], width=70,
                        fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER).grid(row=0, column=1, padx=10, sticky="w")
        
        # Reduction Ratio
        ctk.CTkLabel(content, text=t("mesh_lod_gui.reduction_ratio"), font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=15, sticky="e")
        
        ratio_frame = ctk.CTkFrame(content, fg_color="transparent")
        ratio_frame.grid(row=1, column=1, columnspan=2, sticky="ew")
        
        self.var_ratio = ctk.DoubleVar(value=0.5)
        self.lbl_ratio = ctk.CTkLabel(ratio_frame, text="50%", width=40)
        self.lbl_ratio.pack(side="right", padx=5)
        
        self.slider_ratio = ctk.CTkSlider(ratio_frame, from_=0.1, to=0.9, variable=self.var_ratio, command=self.update_ratio_label)
        self.slider_ratio.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(content, text=t("mesh_lod_gui.ratio_hint"), text_color="gray").grid(row=2, column=1, sticky="w", padx=10)
        
        # Buttons & Progress
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=5, pady=10)
        btn_inner = ctk.CTkFrame(btn_frame, fg_color="transparent")
        btn_inner.pack(expand=True)
        
        ctk.CTkButton(btn_inner, text=t("common.cancel"), fg_color="transparent", border_width=1, border_color=THEME_BORDER, command=self.destroy, width=100).pack(side="left", padx=10)
        self.btn_run = ctk.CTkButton(btn_inner, text=t("mesh_lod_gui.generate_btn"), command=self.start_generation, height=40, 
                                     font=ctk.CTkFont(size=14, weight="bold"), width=160,
                                     fg_color=THEME_BTN_PRIMARY, hover_color=THEME_BTN_HOVER)
        self.btn_run.pack(side="left", padx=10)

        self.progress = ctk.CTkProgressBar(self.main_frame)
        self.progress.pack(side="bottom", fill="x", padx=20, pady=(5, 5))
        self.progress.set(0)

        self.lbl_status = ctk.CTkLabel(self.main_frame, text=t("common.ready"), text_color="gray")
        self.lbl_status.pack(side="bottom", pady=(0, 5))

        # Preservation & Policy Options
        pres_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        pres_frame.pack(side="bottom", fill="x", padx=5, pady=(5, 15))
        
        pres_inner = ctk.CTkFrame(pres_frame, fg_color="transparent")
        pres_inner.pack(expand=True)
        
        ctk.CTkLabel(pres_inner, text=t("blender_bake.preservation"), font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 5))
        self.var_uv = ctk.BooleanVar(value=True)
        self.var_normal = ctk.BooleanVar(value=True)
        self.var_boundary = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(pres_inner, text="UVs", variable=self.var_uv, width=50).pack(side="left", padx=5)
        ctk.CTkCheckBox(pres_inner, text="Normals", variable=self.var_normal, width=60).pack(side="left", padx=5)
        ctk.CTkCheckBox(pres_inner, text="Boundary", variable=self.var_boundary, width=60).pack(side="left", padx=5)

        # Start Analysis
        threading.Thread(target=self.analyze_inputs, daemon=True).start()

    def update_ratio_label(self, value):
        self.lbl_ratio.configure(text=f"{int(value * 100)}%")

    def analyze_inputs(self):
        try:
            ms = self.pymeshlab.MeshSet()
            if self.files:
                path = self.files[0]
                ms.load_new_mesh(str(path))
                m = ms.current_mesh()
                total_faces = m.face_number()
                msg = f"Input: {path.name} | Faces: {total_faces:,} (+ {len(self.files)-1} others)"
                self.after(0, lambda: self.lbl_analysis.configure(text=msg))
        except Exception as e:
            msg = f"Analysis failed: {e}"
            self.after(0, lambda: self.lbl_analysis.configure(text=msg))

    def start_generation(self):
        params = {}
        params['count'] = self.var_lod_count.get()
        params['ratio'] = self.var_ratio.get()
        params['preserve_uv'] = self.var_uv.get()
        params['preserve_normal'] = self.var_normal.get()
        params['preserve_boundary'] = self.var_boundary.get()
        
        self.btn_run.configure(state="disabled", text="Processing...")
        threading.Thread(target=self.run_generation, args=(params,), daemon=True).start()

    def run_generation(self, params):
        ms = self.pymeshlab.MeshSet()
        count = params['count']
        ratio = params['ratio']
        
        total_files = len(self.files)
        success_count = 0
        errors = []
        
        for i, path in enumerate(self.files):
            self.after(0, lambda p=path, idx=i: self.lbl_status.configure(text=f"Processing {idx+1}/{total_files}: {p.name}"))
            self.after(0, lambda val=i/total_files: self.progress.set(val))
            
            try:
                ms.clear()
                ms.load_new_mesh(str(path))
                
                # Flatten layers if merged
                try: ms.flatten_visible_layers()
                except: pass
                
                stem = path.stem
                if "_LOD" in stem: stem = stem.split("_LOD")[0]
                out_suffix = path.suffix
                if out_suffix.lower() == '.fbx': out_suffix = '.obj'

                # LOD 0 (Original/Optimized Base?)
                # Actually usage usually implies LOD0 is full res or slightly optimized.
                # We'll just save current logic: Check if we want LOD0 to be the source or processed.
                # Current logic was: save current mesh as LOD0
                lod0_path = path.parent / f"{stem}_LOD0{out_suffix}"
                ms.save_current_mesh(str(lod0_path))
                
                current_poly_count = ms.current_mesh().face_number()
                
                for lod_level in range(1, count):
                    target_faces = int(current_poly_count * (ratio ** lod_level))
                    if target_faces < 100: target_faces = 100
                    
                    filter_name = 'meshing_decimation_quadric_edge_collapse'
                    if params['preserve_uv']: filter_name += '_with_texture'
                    
                    try:
                        ms.apply_filter(filter_name, 
                                      targetfacenum=target_faces, 
                                      preserveboundary=params['preserve_boundary'], 
                                      preservenormal=params['preserve_normal'])
                    except:
                         ms.apply_filter('meshing_decimation_quadric_edge_collapse', 
                                      targetfacenum=target_faces, 
                                      preserveboundary=params['preserve_boundary'], 
                                      preservenormal=params['preserve_normal'])
                    
                    lod_path = path.parent / f"{stem}_LOD{lod_level}{out_suffix}"
                    ms.save_current_mesh(str(lod_path))
            
                success_count += 1
            except Exception as e:
                errors.append(f"{path.name}: {e}")
        
        self.after(0, lambda: self.finish(success_count, errors))

    def finish(self, count, errors):
        self.progress.set(1.0)
        self.lbl_status.configure(text="Done")
        self.btn_run.configure(state="normal", text="Generate LODs")
        if errors:
            messagebox.showwarning("Result", f"Completed with {len(errors)} errors.")
        else:
            messagebox.showinfo("Success", f"Generated LODs for {count} files.")
        self.destroy()

    def on_closing(self):
        self.destroy()

if __name__ == "__main__":
    # Demo mode for screenshots
    if "--demo" in sys.argv or _is_headless():
        app = AutoLODGUI(None, demo=True)
        app.mainloop()
    elif len(sys.argv) > 1:
        anchor = sys.argv[1]
        from utils.batch_runner import collect_batch_context
        if collect_batch_context("auto_lod", anchor, timeout=0.2) is None:
            sys.exit(0)

        paths = [Path(p) for p in sys.argv[1:] if Path(p).exists()]
        app = AutoLODGUI(paths if len(paths) > 1 else paths[0])
        app.mainloop()
    else:
        app = AutoLODGUI(str(Path.cwd()))
        app.mainloop()
