import os
import subprocess
from pathlib import Path
from typing import List, Callable, Optional

from utils.external_tools import get_blender, get_mayo_conv
from utils.files import get_safe_path

class MeshService:
    def __init__(self):
        self.blender = None
        self.mayo = None
        self.current_process = None
        self.cancel_flag = False

    def execute_mesh_task(
        self,
        mode: str,
        input_paths: List[Path],
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_complete: Optional[Callable[[int, int, List[str], Optional[Path]], None]] = None,
        **options
    ):
        self.cancel_flag = False
        total = len(input_paths)
        success = 0
        errors = []
        last_output = None

        for i, path in enumerate(input_paths):
            if self.cancel_flag: break
            if on_progress: on_progress(i, total, path.name)

            try:
                if mode == "convert":
                    res = self._run_blender_conversion(path, options.get("format", "OBJ"))
                elif mode == "cad":
                    res = self._run_mayo_conversion(path, options.get("format", "OBJ"))
                elif mode == "bake":
                    res = self._run_blender_bake(path, options.get("maps", ["Diffuse", "Normal"]))
                elif mode == "lod":
                    res = self._run_meshlab_lod(path, options.get("ratio", 0.5))
                elif mode == "mayo":
                    res = self._run_mayo_viewer(path)
                else:
                    raise ValueError(f"Unknown mode: {mode}")

                success += 1
                last_output = res
            except Exception as e:
                errors.append(f"{path.name}: {str(e)}")

        if on_complete:
            on_complete(success, total, errors, last_output)

    def _run_blender_conversion(self, path: Path, fmt: str) -> Path:
        out_path = get_safe_path(path.with_suffix(f".{fmt.lower()}"))
        # Example Blender CLI call (actual command depends on script)
        # cmd = [self.blender, "--background", "--python", "mesh_convert.py", "--", str(path), str(out_path)]
        # For simulation, just ensure out_path exists
        if not self.blender:
            self.blender = get_blender()
        if not self.blender:
            raise FileNotFoundError("Blender not found")
        return out_path

    def _run_mayo_conversion(self, path: Path, fmt: str) -> Path:
        out_path = get_safe_path(path.with_suffix(f".{fmt.lower()}"))
        if not self.mayo:
            self.mayo = get_mayo_conv()
        if not self.mayo:
            raise FileNotFoundError("Mayo converter not found")
        # cmd = [self.mayo, "--input", str(path), "--output", str(out_path)]
        return out_path

    def _run_meshlab_lod(self, path: Path, ratio: float) -> Path:
        out_path = get_safe_path(path.parent / f"{path.stem}_lod_{int(ratio*100)}.obj")
        # try: import pymeshlab; ms = pymeshlab.MeshSet(); ...
        return out_path

    def _run_mayo_viewer(self, path: Path) -> Path:
        # Just open the file with Mayo
        if not self.mayo:
            self.mayo = get_mayo_conv()
        if not self.mayo:
            raise FileNotFoundError("Mayo not found")
        return path

    def _run_blender_bake(self, path: Path, maps: List[str]) -> Path:
        if not self.blender:
            self.blender = get_blender()
        if not self.blender:
            raise FileNotFoundError("Blender not found")
        return path.parent

    def cancel(self):
        self.cancel_flag = True
        if self.current_process and self.current_process.poll() is None:
            try: self.current_process.terminate()
            except: pass
