import os
import subprocess
import wave
from pathlib import Path


IMAGE_IDS = {
    "image_convert",
    "merge_to_exr",
    "resize_power_of_2",
    "split_exr",
    "texture_packer_orm",
    "image_compare",
    "image_metadata",
    "rigreader_vectorizer",
    "normal_flip_green",
    "simple_normal_roughness",
    "rmbg_background",
    "esrgan_upscale",
    "marigold_pbr",
    "gemini_image_tool",
}

AUDIO_IDS = {
    "audio_convert",
    "extract_bgm",
    "extract_voice",
    "normalize_volume",
    "demucs_stems",
}

VIDEO_IDS = {
    "video_convert",
    "create_proxy",
    "remove_audio",
    "interpolate_30fps",
    "extract_audio",
    "sequence_to_video",
}

DOC_IDS = {
    "doc_convert",
    "pdf_merge",
    "pdf_split",
}

SEQUENCE_IDS = {
    "sequence_analyze",
    "sequence_arrange",
    "sequence_find_missing",
    "sequence_renumber",
    "sequence_to_video",
}

MESH_IDS = {
    "auto_lod",
    "mesh_convert",
    "blender_bake_gui",
    "cad_to_obj",
    "extract_textures",
    "open_with_mayo",
}

DIR_IDS = {
    "batch_rename",
    "clean_empty_folders",
    "create_symlink",
    "move_to_new_folder",
    "unwrap_folder",
}


def _headless_root(legacy_root: Path) -> Path:
    override = os.environ.get("CTX_OUTPUT_ROOT")
    if override:
        root = Path(override)
    else:
        root = legacy_root / "manuals" / "headless_inputs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_png(path: Path) -> None:
    if path.exists():
        return
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc``\x00"
        b"\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    path.write_bytes(png_bytes)


def _write_pdf(path: Path) -> None:
    if path.exists():
        return
    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    content = b"BT /F1 12 Tf 72 100 Td (ContextHub) Tj ET"
    objects.append(
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content)
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{idx} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(pdf)
    pdf += b"xref\n0 %d\n" % (len(objects) + 1)
    pdf += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    pdf += b"startxref\n%d\n%%EOF\n" % xref_offset
    path.write_bytes(pdf)


def _write_wav(path: Path) -> None:
    if path.exists():
        return
    framerate = 44100
    duration = 1.0
    frames = int(framerate * duration)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(b"\x00\x00" * frames)


def _write_video(path: Path, png_path: Path) -> None:
    if path.exists():
        return
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-loop",
        "1",
        "-i",
        str(png_path),
        "-t",
        "1",
        "-vf",
        "scale=320:240",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except Exception:
        # If ffmpeg is unavailable, leave it missing.
        pass


def _write_sequence_dir(path: Path, png_path: Path) -> None:
    if path.exists():
        return
    path.mkdir(parents=True, exist_ok=True)
    for idx in range(1, 6):
        frame = path / f"frame_{idx:04d}.png"
        if not frame.exists():
            frame.write_bytes(png_path.read_bytes())


def _write_obj(path: Path) -> None:
    if path.exists():
        return
    obj_data = (
        "# ContextHub dummy mesh\n"
        "o DummyMesh\n"
        "v 0.0 0.0 0.0\n"
        "v 1.0 0.0 0.0\n"
        "v 0.0 1.0 0.0\n"
        "f 1 2 3\n"
    )
    path.write_text(obj_data, encoding="utf-8")


def _find_mesh() -> Path | None:
    candidates = [
        Path("Runtimes/Envs/3d/Lib/site-packages/pymeshlab/tests/sample_meshes/bunny.obj"),
        Path("Runtimes/Envs/3d/Lib/site-packages/pymeshlab/tests/sample_meshes/cow.obj"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def get_headless_targets(legacy_id: str, legacy_scope: str, legacy_root: Path) -> list[str]:
    if legacy_scope in {"background", "tray_only"}:
        return []

    headless_root = _headless_root(legacy_root)
    png_path = headless_root / "sample.png"
    _write_png(png_path)

    if legacy_id in IMAGE_IDS:
        return [str(png_path)]

    if legacy_id in AUDIO_IDS:
        wav_path = headless_root / "sample.wav"
        _write_wav(wav_path)
        return [str(wav_path)]

    if legacy_id in VIDEO_IDS:
        mp4_path = headless_root / "sample.mp4"
        _write_video(mp4_path, png_path)
        return [str(mp4_path)] if mp4_path.exists() else []

    if legacy_id in DOC_IDS:
        pdf_path = headless_root / "sample.pdf"
        _write_pdf(pdf_path)
        return [str(pdf_path)]

    if legacy_id in SEQUENCE_IDS:
        seq_dir = headless_root / "sequence_frames"
        _write_sequence_dir(seq_dir, png_path)
        return [str(seq_dir)]

    if legacy_id in MESH_IDS:
        mesh = _find_mesh()
        if mesh:
            return [str(mesh)]
        dummy_mesh = headless_root / "sample.obj"
        _write_obj(dummy_mesh)
        return [str(dummy_mesh)]

    if legacy_id in DIR_IDS or legacy_scope == "directory":
        dummy_dir = headless_root / "dummy_dir"
        dummy_dir.mkdir(parents=True, exist_ok=True)
        return [str(dummy_dir)]

    if legacy_scope == "items":
        return [str(png_path), str(png_path)]

    if legacy_scope == "file":
        return [str(png_path)]

    return []
