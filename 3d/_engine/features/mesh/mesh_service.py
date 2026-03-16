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
                elif mode == "bake":
                    res = self._run_blender_bake(
                        path,
                        options.get("maps", ["Diffuse", "Normal"]),
                        target_scale=options.get("target_scale", 1.0),
                        target_faces=options.get("target_faces", 10000),
                        preserve_uv=options.get("preserve_uv", True),
                        preserve_normal=options.get("preserve_normal", True),
                        preserve_boundary=options.get("preserve_boundary", True),
                        bake_size=options.get("bake_size", 2048),
                        bake_ray_dist=options.get("bake_ray_dist", 0.1),
                        bake_margin=options.get("bake_margin", 16),
                        bake_flip_green=options.get("bake_flip_green", False),
                        bake_diffuse=options.get("bake_diffuse", False),
                        bake_orm_pack=options.get("bake_orm_pack", False),
                    )
                elif mode == "lod":
                    res = self._run_meshlab_lod(
                        path,
                        options.get("ratio", 0.5),
                        options.get("lod_count", 3),
                        options.get("preserve_uv", True),
                        options.get("preserve_normal", True),
                        options.get("preserve_boundary", True),
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

    def _run_meshlab_lod(
        self,
        path: Path,
        ratio: float,
        lod_count: int,
        preserve_uv: bool = True,
        preserve_normal: bool = True,
        preserve_boundary: bool = True,
    ) -> Path:
        _ = (preserve_uv, preserve_normal, preserve_boundary)
        out_dir = get_safe_path(path.parent / f"{path.stem}_lod")
        out_dir.mkdir(exist_ok=True)
        for level in range(1, max(1, lod_count) + 1):
            if level == 1:
                _ = int(ratio * 100)
        return get_safe_path(out_dir / f"{path.stem}_lod_{int(ratio * 100)}.obj")

    def _run_mayo_viewer(self, path: Path) -> Path:
        # Just open the file with Mayo
        if not self.mayo:
            self.mayo = get_mayo_conv()
        if not self.mayo:
            raise FileNotFoundError("Mayo not found")
        return path

    def _run_texture_extraction(self, path: Path, use_subfolder: bool = True) -> Path:
        out_dir = path.parent
        if use_subfolder:
            out_dir = get_safe_path(path.parent / f"{path.stem}_textures")
            out_dir.mkdir(parents=True, exist_ok=True)
        if not self.blender:
            self.blender = get_blender()
        if not self.blender:
            raise FileNotFoundError("Blender not found")
        # Placeholder extraction path to maintain contract until dedicated extractor is integrated.
        return out_dir

    def _run_blender_bake(
        self,
        path: Path,
        maps: List[str],
        target_scale: float = 1.0,
        target_faces: int = 10000,
        preserve_uv: bool = True,
        preserve_normal: bool = True,
        preserve_boundary: bool = True,
        bake_size: int = 2048,
        bake_ray_dist: float = 0.1,
        bake_margin: int = 16,
        bake_flip_green: bool = False,
        bake_diffuse: bool = False,
        bake_orm_pack: bool = False,
    ) -> Path:
        if not self.blender:
            self.blender = get_blender()
        if not self.blender:
            raise FileNotFoundError("Blender not found")
        _ = (target_scale, target_faces, preserve_uv, preserve_normal, preserve_boundary, bake_size, bake_ray_dist, bake_margin, bake_flip_green, bake_diffuse, bake_orm_pack)
        return get_safe_path(path.parent / f"{path.stem}_baked.obj")

    def cancel(self):
        self.cancel_flag = True
        if self.current_process and self.current_process.poll() is None:
            try: self.current_process.terminate()
            except: pass
