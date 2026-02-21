import sys
import subprocess
import shutil
import json
import logging
import threading
import os
from pathlib import Path
from tkinter import messagebox

from core.settings import load_settings
from utils import external_tools

logger = logging.getLogger("manager.core.packages")

class PackageManager:
    _installed_cache = {}  # Class-level cache
    
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir) if not isinstance(root_dir, Path) else root_dir
        self.req_path = self.root_dir / "requirements.txt"
        
    def _resolve_python(self):
        """Resolve Python interpreter - prioritize embedded Python."""
        # Check embedded Python first
        embedded = self.root_dir / "tools" / "python" / "python.exe"
        if embedded.exists():
            return str(embedded)
        
        # Then check settings
        try:
            settings = load_settings()
            pth = settings.get("PYTHON_PATH")
            if pth and Path(pth).exists():
                return str(pth)
        except: pass
        
        return sys.executable
        
    def get_installed_packages(self) -> dict:
        """Return dict of {package_name: version} using pip list --json (with caching)."""
        if PackageManager._installed_cache:
            return PackageManager._installed_cache
            
        try:
            # Use pip list --format=json for reliable detection
            python_exe = self._resolve_python()
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.check_output(
                [python_exe, "-m", "pip", "list", "--format=json"], 
                text=True, 
                startupinfo=startupinfo
            )
            packages = json.loads(result)
            PackageManager._installed_cache = {pkg['name'].lower(): pkg['version'] for pkg in packages}
            return PackageManager._installed_cache
        except Exception as e:
            logger.error(f"Failed to list packages: {e}")
            return {}

    @classmethod
    def refresh_package_cache(cls):
        """Clear the package cache to force a reload on next check."""
        cls._installed_cache = {}

    def check_dependencies(self, item: dict, installed_packages: dict) -> tuple[bool, list]:
        """Check if item's dependencies are met."""
        deps = item.get('dependencies', [])
        if not deps: return True, []
        
        missing = [d for d in deps if d.lower() not in installed_packages]
        
        # Check External Tools
        tools = item.get('external_tools', [])
        if tools:
            _, missing_tools = self.check_external_tools(tools)
            missing.extend(missing_tools)

        return len(missing) == 0, missing

    def check_external_tools(self, tools: list) -> tuple[bool, list]:
        """Check if external tools (ffmpeg, blender, etc) are available."""
        missing = []
        for tool in tools:
            tool_lower = tool.lower()
            found = False
            
            # 1. Try Specific Helper
            try:
                if tool_lower == 'ffmpeg':
                    if external_tools.get_ffmpeg(): found = True
                elif tool_lower == 'blender':
                    if external_tools.get_blender(): found = True
                elif tool_lower == 'mayo':
                    # Mayo Viewer or Conv? Usually just checking availability
                    # But config doesn't specify. Assuming Viewer or Conv is fine.
                    # Let's check get_mayo_viewer
                    try: 
                        if external_tools.get_mayo_viewer(): found = True
                    except:
                        if external_tools.get_mayo_conv(): found = True
                elif tool_lower == 'rife-ncnn-vulkan':
                    try:
                        if external_tools.get_rife(): found = True
                    except: pass
                elif tool_lower == 'realesrgan-ncnn-vulkan':
                    if external_tools.get_realesrgan(): found = True
                elif tool_lower == 'comfyui':
                    if external_tools.get_comfyui(): found = True
                else:
                    # Generic check in PATH
                    if shutil.which(tool): found = True
            except FileNotFoundError:
                found = False # Explicit helper failed
            except Exception:
                found = False
            
            # 2. Double check PATH if specific helper failed but might be globally installed?
            # Actually helpers usually check PATH as fallback.
            
            if not found:
                 # Fallback: check if shutil.which finds it (e.g. ffmpeg in path but settings empty)
                 if shutil.which(tool): found = True
                 
            if not found:
                missing.append(tool)
                
        return len(missing) == 0, missing

    def install_packages(self, deps: list, dep_metadata: dict, progress_callback=None, completion_callback=None):
        """
        Install list of packages in a background thread.
        Callback signature: progress(current_dependency_name, fraction_complete)
        """
        def run():
            python_exe = self._resolve_python()
            total = len(deps)
            success = True
            
            for i, dep in enumerate(deps):
                meta = dep_metadata.get(dep, {})
                pip_name = meta.get('pip_name', dep)
                install_args = meta.get('install_args', [])
                
                if progress_callback:
                    progress_callback(dep, i/total)
                
                try:
                    cmd = [python_exe, "-m", "pip", "install", pip_name] + install_args
                    subprocess.check_call(cmd)
                except Exception as e:
                    logger.error(f"Failed to install {dep}: {e}")
                    success = False
                    break
                    
                
            # Invalidate cache after installation
            PackageManager.refresh_package_cache()
            
            if progress_callback:
                progress_callback("Done", 1.0)
                
            if completion_callback:
                completion_callback(success)

        threading.Thread(target=run, daemon=True).start()

    def uninstall_packages(self, deps: list, dep_metadata: dict, progress_callback=None, completion_callback=None):
        """
        Uninstall list of packages in a background thread.
        Callback signature: progress(current_dependency_name, fraction_complete)
        """
        def run():
            python_exe = self._resolve_python()
            total = len(deps)
            success = True

            for i, dep in enumerate(deps):
                meta = dep_metadata.get(dep, {})
                pip_name = meta.get('pip_name', dep)

                if progress_callback:
                    progress_callback(dep, i / total if total else 1.0)

                try:
                    cmd = [python_exe, "-m", "pip", "uninstall", "-y", pip_name]
                    subprocess.check_call(cmd)
                except Exception as e:
                    logger.error(f"Failed to uninstall {dep}: {e}")
                    success = False
                    break

            PackageManager.refresh_package_cache()

            if progress_callback:
                progress_callback("Done", 1.0)

            if completion_callback:
                completion_callback(success)

        threading.Thread(target=run, daemon=True).start()

    def update_system_libs(self, on_complete=None):
        """Run pip install -r requirements.txt using system python."""
        def run():
            try:
                python_exe = self._resolve_python()
                subprocess.check_call([python_exe, "-m", "pip", "install", "-U", "-r", str(self.req_path)])
                PackageManager.refresh_package_cache()
                if on_complete: on_complete(True, "System libraries updated!")
            except Exception as e:
                logger.error(f"System Update failed: {e}")
                if on_complete: on_complete(False, str(e))
                
        threading.Thread(target=run, daemon=True).start()

    def check_tray_dependencies(self, python_path: str) -> dict:
        """
        Check if required tray libs are installed in the given python environment.
        Returns: {'missing': [], 'valid': bool}
        """
        required = ['pystray', 'pillow', 'pywin32']
        start_flags = 0
        if os.name == 'nt':
            start_flags = subprocess.STARTF_USESHOWWINDOW # Hide window
            
        try:
            # Use pip freeze or list to check
            cmd = [str(python_path), "-m", "pip", "list", "--format=json"]
            result = subprocess.check_output(cmd, text=True, creationflags=0x08000000)
            installed = [p['name'].lower() for p in json.loads(result)]
            
            missing = [r for r in required if r not in installed]
            # Pillow is 'pillow' in pip list usually, but import is PIL
            # pywin32 might show as pywin32
            
            return {'missing': missing, 'valid': len(missing) == 0}
        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            return {'missing': ['Check Failed'], 'valid': False}
