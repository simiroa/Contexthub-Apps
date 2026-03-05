import sys
import os
import traceback
from pathlib import Path
from tkinter import messagebox
import importlib
import subprocess
import runpy

# Add src to path so we can import modules
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.append(str(src_dir))

from core.config import MenuConfig
from core.logger import setup_logger
from core.settings import load_settings
from core.paths import ROOT_DIR, TOOLS_DIR, USERDATA_DIR, LOGS_DIR
from utils import paths
from contexthub.utils.i18n import t

# Setup logging
logger = setup_logger("menu_dispatcher")

def resolve_python():
    """Resolve Python interpreter - prioritize embedded Python."""
    # Always check embedded Python first
    embedded = Path(__file__).parent.parent.parent / "tools" / "python" / "python.exe"
    if embedded.exists():
        return str(embedded)
    
    # Then check settings
    try:
        settings = load_settings()
        python_path = settings.get("PYTHON_PATH")
        if python_path and Path(python_path).exists():
            return python_path
    except Exception:
        pass
    
    # Fallback to sys.executable
    exe = sys.executable
    if exe.endswith("pythonw.exe"):
        exe = exe.replace("pythonw.exe", "python.exe")
    return exe

def resolve_pythonw():
    """Resolve pythonw.exe for GUI apps (no console window)."""
    # Try embedded pythonw first
    embedded_w = Path(__file__).parent.parent.parent / "tools" / "python" / "pythonw.exe"
    if embedded_w.exists():
        return str(embedded_w)
    
    # Try to find pythonw next to current executable
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        pythonw = exe.parent / "pythonw.exe"
        if pythonw.exists():
            return str(pythonw)
    
    # Fallback to python.exe
    return resolve_python()

PYTHON_EXE = resolve_python()
PYTHONW_EXE = resolve_pythonw()

# For GUI subprocess calls, use CREATE_NO_WINDOW flag
CREATE_NO_WINDOW = 0x08000000


def _lazy(module_name, func_name):
    def _call(*args, **kwargs):
        mod = importlib.import_module(module_name)
        func = getattr(mod, func_name)
        return func(*args, **kwargs)
    return _call


def _ai_tab_handler(item_id):
    from features.ai.standalone.gemini_img_tools import gui as gemini_img_tools
    tab_map = {
        "ai_style_change": "Style",
        "ai_pbr_gen": "PBR Gen",
        "ai_maketile": "Tileable",
        "ai_weathering": "Weathering",
        "ai_to_prompt": "Analysis",
        "ai_outpaint": "Outpaint",
        "ai_inpaint": "Inpaint",
    }
    return gemini_img_tools.GeminiImageToolsGUI, tab_map.get(item_id, "Style")


def _open_manager():
    """Robustly open the Manager GUI matching tray_agent logic."""
    try:
        manager_script = src_dir / "manager" / "main.py"
        monitor_cmd = [PYTHON_EXE, str(manager_script)]
        
        # Log launch attempt
        log_path = LOGS_DIR / "manager_crash.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        out_file = open(log_path, "w", encoding="utf-8")
        out_file.write(f"Launching: {monitor_cmd}\n")
        out_file.flush()
        
        # Launch with stdout/stderr redirection
        subprocess.Popen(
            monitor_cmd, 
            close_fds=True, 
            creationflags=0x08000000, 
            stdout=out_file, 
            stderr=out_file
        )
        
        # Note: We are leaking the file handle 'out_file' here in the parent process slightly, 
        # but since this process (menu.py) exits immediately (it's a transient dispatcher), it's fine.
        # The child inherits the handle? No, subprocess copies it.
    except Exception as e:
        messagebox.showerror(t("common.error"), t("menu.open_manager_failed").format(error=e))


def build_handler_map():
    """
    Build the handler map (id -> callable or sentinel).
    Exposed for testing to ensure config/menu dispatch stays in sync.
    """
    # Helper for GUI subprocess (no console window)
    def gui_popen(args):
        if os.environ.get("CTX_CAPTURE_MODE") == "1" or os.environ.get("CTX_HEADLESS") == "1":
            script_path = args[1] if len(args) > 1 else None
            if script_path and Path(script_path).exists():
                old_argv = sys.argv
                try:
                    sys.argv = args[1:]
                    runpy.run_path(str(script_path), run_name="__main__")
                finally:
                    sys.argv = old_argv
                return None
        return subprocess.Popen(args, creationflags=CREATE_NO_WINDOW)
    
    return {
        # === Image ===
        "image_convert": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "image" / "convert_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "merge_to_exr": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "image" / "merge_exr.py"), *([str(i) for i in s] if s else [str(p)])]),
        "resize_power_of_2": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "image" / "resize_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "split_exr": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "image" / "split_image.py"), *([str(i) for i in s] if s else [str(p)])]),
        "texture_packer_orm": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "image" / "packer_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "normal_flip_green": _lazy("features.image.normal", "flip_normal_green"),
        "simple_normal_roughness": _lazy("features.image.normal", "generate_simple_normal_roughness"),
        "image_compare": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "image" / "compare_gui.py"), *( [str(i) for i in s] if s else [str(p)] )]),
        "image_metadata": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "image" / "metadata_gui.py"), str(p)]),
        "rigreader_vectorizer": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "image" / "vectorizer" / "vectorizer_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "noise_master": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "tools" / "noise_master" / "main.py")]),

        # === AI ===
        "whisper_subtitle": _lazy("features.ai.subtitle", "generate_subtitles"),
        "esrgan_upscale": _lazy("features.ai.standalone.upscale", "upscale_image"),
        "rmbg_background": _lazy("features.ai.tools", "remove_background"),
        "marigold_pbr": _lazy("features.ai.marigold_gui", "run_marigold_gui"),
        "prompt_master": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "prompt_master" / "main.py")]),
        "gemini_image_tool": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "ai" / "standalone" / "gemini_img_tools.py"), *([str(i) for i in s] if s else [str(p)])]),
        "demucs_stems": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "audio" / "separate_gui.py"), *([str(i) for i in s] if s else [str(p)])]),

        # === Video ===
        "video_convert": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "video" / "convert_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "extract_audio": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "video" / "audio_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "interpolate_30fps": _lazy("features.video.tools", "frame_interp_30fps"),
        "create_proxy": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "video" / "convert_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "remove_audio": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "video" / "audio_gui.py"), *([str(i) for i in s] if s else [str(p)])]),

        # === Sequence ===
        "sequence_arrange": _lazy("features.sequence.tools", "arrange_sequences"),
        "sequence_find_missing": _lazy("features.sequence.tools", "find_missing_frames"),
        "sequence_to_video": _lazy("features.sequence.tools", "seq_to_video"),
        "sequence_analyze": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "sequence" / "analyze_gui.py"), str(p)]),
        "sequence_renumber": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "system" / "rename.py"), "renumber", *([str(i) for i in s] if s else [str(p)])]),

        # === Audio ===
        "audio_convert": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "audio" / "convert_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "extract_bgm": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "audio" / "separate_gui.py"), *([str(i) for i in s] if s else [str(p)]), "--mode", "bgm"]),
        "extract_voice": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "audio" / "separate_gui.py"), *([str(i) for i in s] if s else [str(p)]), "--mode", "voice"]),
        "normalize_volume": _lazy("features.audio.tools", "optimize_volume"),

        # === System ===
        "clean_empty_folders": _lazy("utils.system_tools", "clean_empty_dirs"),
        "move_to_new_folder": lambda p, s=None: _lazy("utils.system_tools", "move_to_new_folder")(p, selection=s),
        "unwrap_folder": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "system" / "unwrap_folder_gui.py"), str(p)]),
        "finder": _lazy("features.finder", "open_finder"),
        "create_symlink": _lazy("utils.system_tools", "create_symlink"),
        "manager": lambda p, s=None: _open_manager(),

        # === 3D ===
        "auto_lod": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "mesh" / "lod_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "cad_to_obj": _lazy("features.mesh.mayo", "convert_cad"),
        "mesh_convert": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "mesh" / "blender.py"), "convert", *([str(i) for i in s] if s else [str(p)])]),
        "open_with_mayo": _lazy("features.mesh.mayo", "open_with_mayo"),
        "extract_textures": _lazy("features.mesh.blender", "extract_textures"),
        "blender_bake_gui": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "mesh" / "bake_gui.py"), *([str(i) for i in s] if s else [str(p)])]),

        # === Clipboard ===
        # copy_my_info: Launches the Info Manager GUI for editing.
        # The context menu handles copying dynamically via sys_copy_content.py.
        "copy_my_info": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "scripts" / "sys_info_manager.py")]),
        "analyze_error": _lazy("utils.system_clipboard", "analyze_error"),
        "open_from_clipboard": lambda p, s=None: _lazy("utils.system_open_from_clipboard", "open_path_from_clipboard")(),
        "save_clipboard_image": _lazy("utils.system_tools", "save_clipboard_image"),
        "clipboard_to_new_folder": _lazy("utils.system_tools", "clipboard_to_new_folder"),
        "copy_unc_path": _lazy("utils.system_tools", "copy_unc_path"),

        # === Document ===
        "doc_convert": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "document" / "convert_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "pdf_merge": lambda p, s=None: _lazy("utils.system_tools", "pdf_merge")(p, selection=s),
        "pdf_split": lambda p, s=None: _lazy("utils.system_tools", "pdf_split")(p, selection=s),

        # === Rename ===
        "batch_rename": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "system" / "rename.py"), "rename", *([str(i) for i in s] if s else [str(p)])]),

        # === Tools ===
        "youtube_downloader": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "video" / "downloader_gui.py")]),
        "vacance": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "leave_manager" / "gui.py")]),
        "leave_manager": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "leave_manager" / "gui.py")]),
        "ai_text_lab": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "tools" / "ai_text_lab.py")]),
        "context_flow": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "tools" / "context_flow" / "gui.py")]),

        # === ComfyUI ===
        "seedvr2_upscaler": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "comfyui" / "seedvr2_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
        "z_image_turbo": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "comfyui" / "z_image_turbo_gui.py"), *([str(i) for i in s] if s else [str(p)])]),
    }


def main():
    try:
        if len(sys.argv) < 3:
            logger.error(f"Insufficient arguments: {sys.argv}")
            return

        item_id = sys.argv[1]
        target_path = sys.argv[2]

        logger.info(f"Invoked: {item_id} on {target_path}")

        # Batch Execution Logic (Debouncing)
        try:
            logger.debug("Checking batch context...")
            from utils.batch_runner import collect_batch_context

            batch_selection = collect_batch_context(item_id, target_path)

            if batch_selection is None:
                logger.info(f"Skipping {target_path} (follower process)")
                sys.exit(0)

            logger.info(f"Leader process for {len(batch_selection)} items: {batch_selection}")

        except Exception as e:
            logger.warning(f"Batch check failed: {e}")
            batch_selection = [Path(target_path)]

        # Load config to find the script handler
        logger.debug("Loading config...")
        config = MenuConfig()
        item_config = config.get_item_by_id(item_id)

        # Custom command in config takes priority
        if item_config and item_config.get('command'):
            cmd_template = item_config['command']
            logger.info(f"Executing custom command: {cmd_template}")
            cmd = cmd_template.replace("%1", str(target_path)).replace("%V", str(target_path))
            subprocess.Popen(cmd, shell=True)
            return

        handlers = build_handler_map()
        handler = handlers.get(item_id)


        if handler == "ai_tab":
            gui_cls, tab = _ai_tab_handler(item_id)
            gui_cls(target_path, start_tab=tab).mainloop()
        elif handler:
            # Some handlers expect batch_selection
            try:
                handler(target_path, batch_selection)
            except TypeError:
                handler(target_path)
        else:
            logger.warning(f"Unknown item_id: {item_id}")

        logger.debug("Dispatch complete.")

    except Exception as e:
        error_msg = f"Error executing {sys.argv}: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(t("menu.context_error_title"), t("menu.an_error_occurred").format(error=e))
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except (PermissionError, OSError) as e:
        # Check for Access Denied (WinError 5)
        is_access_denied = isinstance(e, PermissionError) or (isinstance(e, OSError) and getattr(e, 'winerror', 0) == 5)
        
        if is_access_denied:
            import ctypes
            import tkinter as tk
            from tkinter import messagebox
            
            # Hide Main Window
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            
            if messagebox.askyesno(t("menu.access_denied_title"), t("menu.access_denied_prompt")):
                # Relaunch with RunAs
                try:
                    params = " ".join([f'"{arg}"' for arg in sys.argv])
                    # sys.executable is python.exe. We need to pass the script and args.
                    # But sys.argv[0] is the script path usually.
                    # Reconstruct command line somewhat reliably.
                    
                    script = sys.argv[0]
                    args = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
                    
                    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", PYTHON_EXE, f'"{script}" {args}', None, 1)
                    if ret <= 32:
                        messagebox.showerror(t("common.error"), t("menu.elevation_failed"))
                except Exception as ex:
                    messagebox.showerror(t("common.error"), t("menu.elevation_failed_with_error").format(error=ex))
            else:
                pass # User cancelled
        else:
            # Re-raise other errors to be caught optionally or logged
            # But since we are at top level, maybe we should just log and show error?
            # main() already has a catch-all for generic exceptions, so this block is likely
            # catching things that bubbled up or were re-raised.
            logger.error(f"Top-level error: {e}")

