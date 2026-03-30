from pathlib import Path
from typing import Callable, List, Optional

import subprocess

from utils.external_tools import get_blender, get_mayo_conv, get_mayo_viewer
from utils.files import get_safe_path

class MeshService:
    def __init__(self):
        self.blender = None
        self.mayo = None
        self.current_process = None
        self.cancel_flag = False

    def get_dependency_status(self, mode: str) -> dict[str, str | bool | None]:
        try:
            if mode in {"convert", "extract"}:
                path = self.blender or get_blender()
                self.blender = path
                return {
                    "available": True,
                    "title": "Blender Ready",
                    "detail": str(path),
                    "path": str(path),
                }
            if mode == "cad":
                path = self.mayo or get_mayo_conv()
                self.mayo = path
                return {
                    "available": True,
                    "title": "Mayo Converter Ready",
                    "detail": str(path),
                    "path": str(path),
                }
            if mode == "mayo":
                path = get_mayo_viewer()
                return {
                    "available": True,
                    "title": "Mayo Ready",
                    "detail": str(path),
                    "path": str(path),
                }
            return {
                "available": True,
                "title": "Ready",
                "detail": "",
                "path": None,
            }
        except Exception as exc:
            return {
                "available": False,
                "title": "Dependency Missing",
                "detail": str(exc),
                "path": None,
            }

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
            if on_progress:
                on_progress(i + 1, total, path.name)

            try:
                if mode == "convert":
                    res = self._run_blender_conversion(
                        path,
                        options.get("format", "OBJ"),
                        options.get("convert_to_subfolder", options.get("use_subfolder", False)),
                    )
                elif mode == "cad":
                    res = self._run_mayo_conversion(
                        path,
                        options.get("format", "OBJ"),
                        options.get("convert_to_subfolder", options.get("use_subfolder", False)),
                    )
                elif mode == "mayo":
                    res = self._run_mayo_viewer(path)
                elif mode == "extract":
                    res = self._run_texture_extraction(
                        path,
                        options.get("convert_to_subfolder", options.get("use_subfolder", True)),
                    )
                else:
                    raise ValueError(f"Unknown mode: {mode}")

                success += 1
                last_output = res
            except Exception as e:
                errors.append(f"{path.name}: {str(e)}")

        if on_complete:
            on_complete(success, total, errors, last_output)

    def _run_blender_conversion(self, path: Path, fmt: str, use_subfolder: bool = False) -> Path:
        out_dir = path.parent
        if use_subfolder:
            out_dir = get_safe_path(path.parent / "Converted_Mesh")
            out_dir.mkdir(exist_ok=True)
        out_path = get_safe_path(out_dir / path.with_suffix(f".{fmt.lower()}").name)
        # Example Blender CLI call (actual command depends on script)
        # cmd = [self.blender, "--background", "--python", "mesh_convert.py", "--", str(path), str(out_path)]
        # For simulation, just ensure out_path exists
        if not self.blender:
            self.blender = get_blender()
        if not self.blender:
            raise FileNotFoundError("Blender not found")
        return out_path

    def _run_mayo_conversion(self, path: Path, fmt: str, use_subfolder: bool = False) -> Path:
        out_dir = path.parent
        if use_subfolder:
            out_dir = get_safe_path(path.parent / "Converted_Mesh")
            out_dir.mkdir(exist_ok=True)
        out_path = get_safe_path(out_dir / path.with_suffix(f".{fmt.lower()}").name)
        if not self.mayo:
            self.mayo = get_mayo_conv()
        if not self.mayo:
            raise FileNotFoundError("Mayo converter not found")
        # cmd = [self.mayo, "--input", str(path), "--output", str(out_path)]
        return out_path

    def _run_mayo_viewer(self, path: Path) -> Path:
        viewer = get_mayo_viewer()
        if not viewer:
            raise FileNotFoundError("Mayo Viewer not found")
        subprocess.Popen([viewer, str(path)])
        return path

    def _run_texture_extraction(self, path: Path, use_subfolder: bool = True) -> Path:
        out_dir = path.parent
        if use_subfolder:
            out_dir = path.parent / "textures"
            out_dir.mkdir(parents=True, exist_ok=True)
        if not self.blender:
            self.blender = get_blender()
        if not self.blender:
            raise FileNotFoundError("Blender not found")
        # Placeholder extraction path to maintain contract until dedicated extractor is integrated.
        return out_dir

    def cancel(self):
        self.cancel_flag = True
        if self.current_process and self.current_process.poll() is None:
            try: self.current_process.terminate()
            except: pass
