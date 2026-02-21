"""
Blender mesh processing tools.
"""
import subprocess
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox
import threading
import sys
import os

# Add src to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent  # features/mesh -> src
sys.path.append(str(src_dir))

from utils.external_tools import get_blender
from utils.gui_lib import BaseWindow, THEME_DROPDOWN_FG, THEME_DROPDOWN_BTN, THEME_DROPDOWN_HOVER
from utils.explorer import get_selection_from_explorer

def _is_headless():
    return os.environ.get("CTX_HEADLESS") == "1" or os.environ.get("CTX_CAPTURE_MODE") == "1"

def _show_blender_install_guide():
    """Show Blender installation guide with download link."""
    if _is_headless():
        return
    msg = (
        "Blender가 설치되어 있지 않습니다.\n\n"
        "Blender는 3D 메시 변환 및 최적화에 사용되는 무료 오픈소스 프로그램입니다.\n\n"
        "설치 방법:\n"
        "1. https://blender.org/download 에서 다운로드\n"
        "2. 또는 Steam에서 'Blender' 검색하여 설치\n"
        "3. 설치 후 ContextUp 재시작\n\n"
        "다운로드 페이지를 열까요?"
    )
    
    if messagebox.askyesno("Blender 필요", msg):
        import webbrowser
        webbrowser.open("https://www.blender.org/download/")

def _get_blender_script(script_name):
    """Get path to blender script."""
    current_dir = Path(__file__).resolve().parent
    src_dir = current_dir.parent.parent  # features/mesh -> src
    return src_dir / "blender_scripts" / script_name

class ConvertMeshGUI(BaseWindow):
    def __init__(self, target_path):
        super().__init__(title="ContextUp Mesh Converter", width=600, height=500, icon_name="mesh_convert_format")
        if _is_headless():
            self.files = [Path("demo_mesh.fbx"), Path("demo_mesh.obj")]
            self.create_widgets()
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            return

        if isinstance(target_path, (list, tuple)):
            selection = [Path(p) for p in target_path]
        else:
            selection = get_selection_from_explorer(target_path)
            if not selection:
                selection = [target_path]
        
        mesh_exts = {'.fbx', '.obj', '.gltf', '.glb', '.usd', '.abc', '.ply', '.stl'}
        self.files = [Path(p) for p in selection if Path(p).suffix.lower() in mesh_exts]
        
        if not self.files:
            messagebox.showinfo("Info", "No mesh files selected.")
            self.destroy()
            return

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # Header
        self.add_header(f"Converting {len(self.files)} Mesh Files")
        
        # Settings Frame
        settings_frame = ctk.CTkFrame(self.main_frame)
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        # Format Selection
        ctk.CTkLabel(settings_frame, text="Output Format:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(20, 5), pady=10)
        self.format_var = ctk.StringVar(value="OBJ")
        formats = ["OBJ", "FBX", "GLTF", "GLB", "USD"]
        self.format_combo = ctk.CTkComboBox(settings_frame, variable=self.format_var, values=formats, width=100,
                                            fg_color=THEME_DROPDOWN_FG, button_color=THEME_DROPDOWN_BTN, button_hover_color=THEME_DROPDOWN_HOVER, border_color=THEME_DROPDOWN_BTN)
        self.format_combo.pack(side="left", padx=5)
        
        # Save to new folder
        self.var_new_folder = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(settings_frame, text="Save to new folder", variable=self.var_new_folder).pack(side="left", padx=20)
        
        # Progress
        self.progress = ctk.CTkProgressBar(self.main_frame)
        self.progress.pack(fill="x", padx=40, pady=(20, 5))
        self.progress.set(0)
        
        self.lbl_status = ctk.CTkLabel(self.main_frame, text="Ready", text_color="gray")
        self.lbl_status.pack(pady=(0, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        self.btn_run = ctk.CTkButton(btn_frame, text="Start Conversion", command=self.start_conversion)
        self.btn_run.pack(side="right", padx=5)
        
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", border_width=1, border_color="gray", command=self.destroy).pack(side="right", padx=5)

    def start_conversion(self):
        self.btn_run.configure(state="disabled", text="Converting...")
        threading.Thread(target=self.run_conversion, daemon=True).start()

    def run_conversion(self):
        output_fmt = self.format_var.get()
        blender = get_blender()
        script = _get_blender_script("convert_mesh.py")
        
        success_count = 0
        errors = []
        total = len(self.files)
        
        for i, path in enumerate(self.files):
            self.after(0, lambda i=i, total=total, name=path.name: 
                         self.lbl_status.configure(text=f"Processing {i+1}/{total}: {name}"))
            self.after(0, lambda v=i/total: self.progress.set(v))
            
            try:
                # Determine output path
                if self.var_new_folder.get():
                    out_dir = path.parent / "Converted_Mesh"
                    out_dir.mkdir(exist_ok=True)
                    output_path = out_dir / path.with_suffix(f".{output_fmt.lower()}").name
                else:
                    output_path = path.with_suffix(f".{output_fmt.lower()}")
                    if output_path == path:
                        output_path = path.with_name(f"{path.stem}_converted.{output_fmt.lower()}")
                
                cmd = [blender, "-b", "-P", str(script), "--", str(path), str(output_path)]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                success_count += 1
                
            except subprocess.CalledProcessError as e:
                errors.append(f"{path.name}: {e.stderr[:100] if e.stderr else str(e)}")
            except Exception as e:
                errors.append(f"{path.name}: {str(e)}")
        
        self.after(0, lambda: self.progress.set(1.0))
        self.after(0, lambda: self.lbl_status.configure(text="Done"))
        self.after(0, lambda: self.btn_run.configure(state="normal", text="Start Conversion"))
        
        if errors:
            msg = f"Converted {success_count}/{total} files.\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                msg += "\n..."
            messagebox.showwarning("Completed with Errors", msg)
        else:
            messagebox.showinfo("Success", f"Successfully converted {success_count} mesh file(s).")
            self.destroy()

    def on_closing(self):
        self.destroy()

class OptimizeMeshGUI(BaseWindow):
    def __init__(self, target_path):
        super().__init__(title="ContextUp Mesh Optimizer", width=500, height=400, icon_name="mesh_optimizer")
        if _is_headless():
            self.files = [Path("demo_mesh.fbx"), Path("demo_mesh.obj")]
            self.create_widgets()
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            return

        if isinstance(target_path, (list, tuple)):
            selection = [Path(p) for p in target_path]
        else:
            selection = get_selection_from_explorer(target_path)
            if not selection:
                selection = [target_path]
        
        mesh_exts = {'.fbx', '.obj', '.gltf', '.ply', '.stl'}
        self.files = [Path(p) for p in selection if Path(p).suffix.lower() in mesh_exts]
        
        if not self.files:
            messagebox.showinfo("Info", "No mesh files selected.")
            self.destroy()
            return

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        self.add_header(f"Optimizing {len(self.files)} Mesh Files")
        
        # Settings
        settings_frame = ctk.CTkFrame(self.main_frame)
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(settings_frame, text="Reduction Ratio:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.ratio_var = ctk.DoubleVar(value=0.5)
        self.lbl_ratio = ctk.CTkLabel(settings_frame, text="50%")
        self.lbl_ratio.pack(anchor="w", padx=20)
        
        slider = ctk.CTkSlider(settings_frame, from_=0.1, to=1.0, variable=self.ratio_var, command=self.update_ratio_label)
        slider.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(settings_frame, text="0.1 = 90% reduction (Low Poly)\n1.0 = No reduction", text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20, pady=(0, 10))
        
        # Progress
        self.progress = ctk.CTkProgressBar(self.main_frame)
        self.progress.pack(fill="x", padx=40, pady=(20, 5))
        self.progress.set(0)
        
        self.lbl_status = ctk.CTkLabel(self.main_frame, text="Ready", text_color="gray")
        self.lbl_status.pack(pady=(0, 10))
        
        # Buttons
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        self.btn_run = ctk.CTkButton(btn_frame, text="Start Optimization", command=self.start_optimization)
        self.btn_run.pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", border_width=1, border_color="gray", command=self.destroy).pack(side="right", padx=5)

    def update_ratio_label(self, value):
        self.lbl_ratio.configure(text=f"{int(value * 100)}%")

    def start_optimization(self):
        self.btn_run.configure(state="disabled", text="Optimizing...")
        threading.Thread(target=self.run_optimization, daemon=True).start()

    def run_optimization(self):
        ratio = self.ratio_var.get()
        blender = get_blender()
        script = _get_blender_script("optimize_mesh.py")
        
        success_count = 0
        errors = []
        total = len(self.files)
        
        for i, path in enumerate(self.files):
            self.after(0, lambda i=i, total=total, name=path.name: 
                         self.lbl_status.configure(text=f"Processing {i+1}/{total}: {name}"))
            self.after(0, lambda v=i/total: self.progress.set(v))
            
            try:
                output_path = path.with_name(f"{path.stem}_optimized{path.suffix}")
                cmd = [blender, "-b", "-P", str(script), "--", str(path), str(output_path), str(ratio)]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                success_count += 1
            except subprocess.CalledProcessError as e:
                errors.append(f"{path.name}: {e.stderr[:100] if e.stderr else str(e)}")
            except Exception as e:
                errors.append(f"{path.name}: {str(e)}")
        
        self.after(0, lambda: self.progress.set(1.0))
        self.after(0, lambda: self.lbl_status.configure(text="Done"))
        self.after(0, lambda: self.btn_run.configure(state="normal", text="Start Optimization"))
        
        if errors:
            msg = f"Optimized {success_count}/{total} files.\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                msg += "\n..."
            messagebox.showwarning("Completed with Errors", msg)
        else:
            messagebox.showinfo("Success", f"Successfully optimized {success_count} mesh file(s).")
            self.destroy()

    def on_closing(self):
        self.destroy()

def convert_mesh(target_path: str, selection=None):
    """Convert mesh between formats."""
    try:
        if not _is_headless():
            get_blender()  # Early check
        app = ConvertMeshGUI(selection if selection else target_path)
        app.mainloop()
    except FileNotFoundError:
        _show_blender_install_guide()
    except Exception as e:
        messagebox.showerror("Error", f"Failed: {e}")

def optimize_mesh(target_path: str, selection=None):
    """Optimize mesh using decimation."""
    try:
        if not _is_headless():
            get_blender()  # Early check
        app = OptimizeMeshGUI(selection if selection else target_path)
        app.mainloop()
    except FileNotFoundError:
        _show_blender_install_guide()
    except Exception as e:
        messagebox.showerror("Error", f"Failed: {e}")

def extract_textures(target_path: str):
    """Extract textures from FBX."""
    try:
        path = Path(target_path)
        
        if path.suffix.lower() != '.fbx':
            messagebox.showinfo("Info", "This tool only works with FBX files.")
            return
        
        output_folder = path.parent / f"{path.stem}_textures"
        
        blender = get_blender()
        script = _get_blender_script("extract_textures.py")
        
        cmd = [blender, "-b", "-P", str(script), "--", str(path), str(output_folder)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        messagebox.showinfo("Success", f"Textures extracted to:\n{output_folder.name}")
        
    except FileNotFoundError:
        _show_blender_install_guide()
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Blender failed: {e.stderr[:200] if e.stderr else str(e)}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        cmd = sys.argv[1]
        anchor = sys.argv[2]
        from utils.batch_runner import collect_batch_context
        batch_id = "mesh_convert" if cmd == "convert" else "mesh_optimize"
        if collect_batch_context(batch_id, anchor, timeout=0.2) is None:
            sys.exit(0)

        paths = [Path(p) for p in sys.argv[2:] if Path(p).exists()]
        if not paths: sys.exit(0)
        
        if cmd == "convert":
            convert_mesh(paths[0], selection=paths)
        elif cmd == "optimize":
            optimize_mesh(paths[0], selection=paths)
    else:
        # For testing
        # convert_mesh(None)
        pass
