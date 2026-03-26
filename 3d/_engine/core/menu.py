import sys
import os
import traceback
from pathlib import Path
import importlib
import subprocess
import runpy

# Add src to path so we can import modules
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.append(str(src_dir))

repo_root = current_dir.parent.parent.parent

def _app_main(category, app_id):
    return repo_root / category / app_id / 'main.py'

from core.config import MenuConfig
from core.logger import setup_logger
from core.settings import load_settings
from core.paths import ROOT_DIR, TOOLS_DIR, USERDATA_DIR, LOGS_DIR

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
        logger.error(f"Failed to launch Manager: {e}")


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
        "image_convert": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("image", "image_convert")), *([str(i) for i in s] if s else [str(p)])]),
        "merge_to_exr": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("image", "merge_to_exr")), *([str(i) for i in s] if s else [str(p)])]),
        "resize_power_of_2": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("image", "resize_power_of_2")), *([str(i) for i in s] if s else [str(p)])]),
        "split_exr": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("image", "split_exr")), *([str(i) for i in s] if s else [str(p)])]),
        "texture_packer_orm": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("image", "texture_packer_orm")), *([str(i) for i in s] if s else [str(p)])]),
        "normal_flip_green": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("image", "normal_flip_green")), *([str(i) for i in s] if s else [str(p)])]),
        "simple_normal_roughness": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("image", "simple_normal_roughness")), *([str(i) for i in s] if s else [str(p)])]),
        "image_compare": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("image", "image_compare")), *([str(i) for i in s] if s else [str(p)])]),
        "rigreader_vectorizer": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("image", "rigreader_vectorizer")), *([str(i) for i in s] if s else [str(p)])]),
        "noise_master": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "tools" / "noise_master" / "main.py")]),

        # === AI ===
        "whisper_subtitle": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("ai", "whisper_subtitle")), *([str(i) for i in s] if s else [str(p)])]),
        "esrgan_upscale": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("ai", "esrgan_upscale")), *([str(i) for i in s] if s else [str(p)])]),
        "rmbg_background": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("ai", "rmbg_background")), *([str(i) for i in s] if s else [str(p)])]),
        "marigold_pbr": _lazy("features.ai.marigold_gui", "run_marigold_gui"),
        "gemini_image_tool": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "ai" / "standalone" / "gemini_img_tools.py"), *([str(i) for i in s] if s else [str(p)])]),
        "demucs_stems": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("ai", "demucs_stems")), *([str(i) for i in s] if s else [str(p)])]),

        # === Video ===
        "video_convert": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("video", "video_convert")), *([str(i) for i in s] if s else [str(p)])]),
        "extract_audio": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("video", "extract_audio")), *([str(i) for i in s] if s else [str(p)])]),
        "interpolate_30fps": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("video", "interpolate_30fps")), *([str(i) for i in s] if s else [str(p)])]),
        "remove_audio": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("video", "remove_audio")), *([str(i) for i in s] if s else [str(p)])]),

        # === Sequence ===
        "sequence_arrange": _lazy("features.sequence.tools", "arrange_sequences"),
        "sequence_find_missing": _lazy("features.sequence.tools", "find_missing_frames"),
        "sequence_to_video": _lazy("features.sequence.tools", "seq_to_video"),
        "sequence_analyze": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "sequence" / "analyze_gui.py"), str(p)]),
        "sequence_renumber": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "system" / "rename.py"), "renumber", *([str(i) for i in s] if s else [str(p)])]),

        # === Audio ===
        "audio_convert": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("audio", "audio_convert")), *([str(i) for i in s] if s else [str(p)])]),
        "extract_bgm": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("audio", "extract_bgm")), *([str(i) for i in s] if s else [str(p)])]),
        "extract_voice": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("audio", "extract_voice")), *([str(i) for i in s] if s else [str(p)])]),
        "normalize_volume": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("audio", "normalize_volume")), *([str(i) for i in s] if s else [str(p)])]),

        # === System ===
        "unwrap_folder": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "system" / "unwrap_folder_gui.py"), str(p)]),
        "finder": _lazy("features.finder", "open_finder"),
        "manager": lambda p, s=None: _open_manager(),

        # === 3D ===
        "auto_lod": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("3d", "auto_lod")), *([str(i) for i in s] if s else [str(p)])]),
        "cad_to_obj": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("3d", "cad_to_obj")), *([str(i) for i in s] if s else [str(p)])]),
        "mesh_convert": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("3d", "mesh_convert")), *([str(i) for i in s] if s else [str(p)])]),
        "open_with_mayo": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("3d", "open_with_mayo")), *([str(i) for i in s] if s else [str(p)])]),
        "extract_textures": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("3d", "extract_textures")), *([str(i) for i in s] if s else [str(p)])]),
        "blender_bake_gui": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("3d", "blender_bake_gui")), *([str(i) for i in s] if s else [str(p)])]),

        # === Clipboard ===
        # copy_my_info: Launches the Info Manager GUI for editing.
        # The context menu handles copying dynamically via sys_copy_content.py.
        "copy_my_info": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "scripts" / "sys_info_manager.py")]),
        "analyze_error": _lazy("utils.system_clipboard", "analyze_error"),
        "open_from_clipboard": lambda p, s=None: _lazy("utils.system_open_from_clipboard", "open_path_from_clipboard")(),

        # === Document ===
        "doc_convert": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("document", "doc_convert")), *([str(i) for i in s] if s else [str(p)])]),
        "pdf_merge": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("document", "pdf_merge")), *([str(i) for i in s] if s else [str(p)])]),
        "pdf_split": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("document", "pdf_split")), *([str(i) for i in s] if s else [str(p)])]),

        # === Rename ===
        "batch_rename": lambda p, s=None: gui_popen([PYTHONW_EXE, str(src_dir / "features" / "system" / "rename.py"), "rename", *([str(i) for i in s] if s else [str(p)])]),

        # === Tools ===
        "youtube_downloader": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("utilities", "youtube_downloader"))]),
        "vacance": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("utilities", "leave_manager"))]),
        "leave_manager": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("utilities", "leave_manager"))]),
        "ai_text_lab": lambda p, s=None: gui_popen([PYTHONW_EXE, str(_app_main("ai_lite", "ai_text_lab"))]),
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
        logger.error(f'Context menu error: {e}')


if __name__ == "__main__":
    try:
        main()
    except (PermissionError, OSError) as e:
        logger.error(f"Top-level error: {e}")
