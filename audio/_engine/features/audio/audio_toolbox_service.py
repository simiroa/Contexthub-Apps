from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

from contexthub.utils.external_tools import get_ffmpeg
from contexthub.utils.files import get_safe_path
from features.audio.audio_convert.service import AudioConvertService
from features.audio.audio_toolbox_ffmpeg_ops import (
    build_trimmed_input,
    run_ffmpeg_compress,
    run_ffmpeg_enhance,
)
from features.audio.audio_toolbox_state import (
    AudioToolboxState,
    pick_supported_audio,
)
from features.audio.audio_toolbox_tasks import (
    TASK_COMPRESS_AUDIO,
    TASK_CONVERT_AUDIO,
    TASK_ENHANCE_AUDIO,
    TASK_EXTRACT_BGM,
    TASK_EXTRACT_VOICE,
    TASK_NORMALIZE_VOLUME,
)
from features.audio.normalize_service import AudioNormalizeService


ServiceUpdate = Callable[..., None]


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def _human_error(exc: Exception) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


def _resolve_console_script(base_name: str) -> str | None:
    exe = Path(sys.executable)
    candidates = []
    if os.name == "nt":
        candidates.extend(
            [
                exe.with_name(f"{base_name}.exe"),
                exe.with_name(f"{base_name}.cmd"),
                exe.with_name(f"{base_name}.bat"),
                exe.parent / "Scripts" / f"{base_name}.exe",
                exe.parent / "Scripts" / f"{base_name}.cmd",
                exe.parent / "Scripts" / f"{base_name}.bat",
            ]
        )
    candidates.append(exe.with_name(base_name))
    candidates.append(exe.parent / "Scripts" / base_name)
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which(base_name)


def _output_dir_for(path: Path, output_mode: str, custom_output_dir: Path | None, folder_name: str) -> Path:
    if output_mode == "custom_folder" and custom_output_dir is not None:
        custom_output_dir.mkdir(parents=True, exist_ok=True)
        return custom_output_dir
    if output_mode == "source_folder":
        return path.parent
    folder = path.parent / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _stem_name(task_type: str) -> str:
    return "Vocals" if task_type == TASK_EXTRACT_VOICE else "Instrumental"


def _legacy_suffix(task_type: str) -> str:
    if task_type == TASK_EXTRACT_VOICE:
        return "_voice"
    if task_type == TASK_EXTRACT_BGM:
        return "_bgm"
    raise ValueError(f"Unsupported task type: {task_type}")


class AudioToolboxService:
    def __init__(self, state: AudioToolboxState, on_update: ServiceUpdate | None = None) -> None:
        self.state = state
        self.on_update = on_update
        self.current_process: subprocess.Popen | None = None
        self.cancel_flag = False
        self._separator = None
        self._refresh_environment()

    def _refresh_environment(self) -> None:
        ffmpeg = get_ffmpeg()
        self.state.ffmpeg_available = bool(ffmpeg)
        self.state.audio_separator_available = _module_available("audio_separator.separator")
        self.state.demucs_available = _module_available("demucs")
        self._audio_separator_cli = _resolve_console_script("audio-separator")
        self._ffmpeg_normalize_cli = _resolve_console_script("ffmpeg-normalize")

    def add_inputs(self, paths: list[str | Path]) -> None:
        new_files = pick_supported_audio([Path(item) for item in paths])
        for path in new_files:
            if path in self.state.files:
                continue
            self.state.files.append(path)
        if self.state.selected_index < 0 and self.state.files:
            self.state.selected_index = 0
        self._emit_update()

    def remove_input_at(self, index: int) -> None:
        if 0 <= index < len(self.state.files):
            self.state.files.pop(index)
        if self.state.selected_index >= len(self.state.files):
            self.state.selected_index = len(self.state.files) - 1
        self._emit_update()

    def clear_inputs(self) -> None:
        self.state.files.clear()
        self.state.selected_index = -1
        self._emit_update()

    def set_selected_index(self, index: int) -> None:
        self.state.selected_index = index
        self._emit_update()

    def output_dir_for_preview(self, path: Path | None = None) -> Path | None:
        target = path or (self.state.files[0] if self.state.files else None)
        if target is None:
            return None
        if self.state.task_type in {TASK_EXTRACT_VOICE, TASK_EXTRACT_BGM}:
            return _output_dir_for(target, self.state.output_mode, self.state.custom_output_dir, "Separated_Audio")
        if self.state.task_type == TASK_NORMALIZE_VOLUME:
            return _output_dir_for(target, self.state.output_mode, self.state.custom_output_dir, "Normalized_Audio")
        if self.state.task_type == TASK_COMPRESS_AUDIO:
            return _output_dir_for(target, self.state.output_mode, self.state.custom_output_dir, "Compressed_Audio")
        if self.state.task_type == TASK_ENHANCE_AUDIO:
            return _output_dir_for(target, self.state.output_mode, self.state.custom_output_dir, "Enhanced_Audio")
        return _output_dir_for(target, self.state.output_mode, self.state.custom_output_dir, "Converted_Audio")

    def output_summary(self) -> str:
        folder = self.output_dir_for_preview()
        if not self.state.files or folder is None:
            return "Output path appears after files are queued."
        mode = {
            "source_folder": "Source folder",
            "custom_folder": "Custom folder",
            "task_folder": "Task folder",
        }.get(self.state.output_mode, self.state.output_mode)
        return f"{folder} ({mode})"

    def runtime_summary(self) -> str:
        parts = []
        parts.append("audio-separator ready" if self.state.audio_separator_available else "audio-separator missing")
        parts.append("ffmpeg ready" if self.state.ffmpeg_available else "ffmpeg missing")
        parts.append("demucs ready" if self.state.demucs_available else "demucs missing")
        return " | ".join(parts)

    def reveal_output_dir(self) -> None:
        folder = self.output_dir_for_preview()
        if folder is None:
            return
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(folder)
        except Exception:
            pass

    def start(self) -> None:
        if self.state.is_processing:
            return
        self.cancel_flag = False
        self.state.is_processing = True
        self.state.progress_value = 0.0
        self.state.completed_count = 0
        self.state.total_count = len(self.state.files)
        self.state.error_message = None
        self.state.last_output_path = None
        self.state.status_text = f"{TASK_LABELS.get(self.state.task_type, 'Audio Task')} started."
        self.state.detail_text = ""
        self._emit_update()
        threading.Thread(target=self._run_current_task, daemon=True).start()

    def cancel(self) -> None:
        self.cancel_flag = True
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
            except Exception:
                pass
        self.state.status_text = "Cancelling..."
        self._emit_update()

    def run_console(
        self,
        task_type: str,
        files: list[Path],
        *,
        output_mode: str = "source_folder",
        custom_output_dir: Path | None = None,
        model: str | None = None,
        separator_output_format: str = "wav",
        stem_mode: str = "Selected stem only",
        target_loudness: float = -16.0,
        true_peak: float = -1.5,
        loudness_range: float = 11.0,
        convert_output_format: str = "MP3",
        convert_quality: str = "High",
        copy_metadata: bool = True,
        delete_original: bool = False,
    ) -> int:
        self.state.task_type = task_type
        self.state.files = pick_supported_audio(files)
        self.state.output_mode = output_mode
        self.state.custom_output_dir = custom_output_dir
        if model:
            self.state.model = model
        self.state.separator_output_format = separator_output_format
        self.state.stem_mode = stem_mode
        self.state.target_loudness = target_loudness
        self.state.true_peak = true_peak
        self.state.loudness_range = loudness_range
        self.state.convert_output_format = convert_output_format
        self.state.convert_quality = convert_quality
        self.state.copy_metadata = copy_metadata
        self.state.delete_original = delete_original

        if not self.state.files:
            print("No supported audio files were provided.", flush=True)
            return 1

        print(f"{TASK_LABELS.get(task_type, task_type)} started.", flush=True)
        print(f"Files: {len(self.state.files)}", flush=True)
        print(f"Output: {self.output_summary()}", flush=True)

        try:
            success, total, errors = self._run_current_task_sync()
        except Exception as exc:
            print(f"Failed: {_human_error(exc)}", flush=True)
            return 2

        if self.state.last_output_path is not None:
            print(f"Last output: {self.state.last_output_path}", flush=True)
        print(f"Finished: {success}/{total} succeeded.", flush=True)
        if errors:
            print("Failures:", flush=True)
            for entry in errors:
                print(f"  - {entry}", flush=True)
            return 2
        return 0

    def _run_current_task(self) -> None:
        try:
            success, total, errors = self._run_current_task_sync()
        except Exception as exc:
            self.state.is_processing = False
            self.state.error_message = _human_error(exc)
            self.state.status_text = "Task failed"
            self.state.detail_text = self.state.error_message
            self._emit_update(finished=True, success=0, total=len(self.state.files), errors=[self.state.error_message])
            return

        self.state.is_processing = False
        if self.cancel_flag:
            self.state.status_text = "Cancelled"
        elif errors:
            self.state.status_text = f"Finished with errors: {success}/{total}"
            self.state.detail_text = errors[0]
        else:
            self.state.status_text = f"Complete: {success}/{total}"
            self.state.detail_text = ""
        self._emit_update(finished=True, success=success, total=total, errors=errors)

    def _run_current_task_sync(self) -> tuple[int, int, list[str]]:
        files = list(self.state.files)
        total = len(files)
        success = 0
        errors: list[str] = []
        self.state.total_count = total

        for index, path in enumerate(files, start=1):
            if self.cancel_flag:
                break
            self.state.status_text = f"{TASK_LABELS.get(self.state.task_type, 'Running')} {index}/{total}"
            self.state.detail_text = path.name
            self.state.progress_value = (index - 1) / total if total else 0.0
            self._emit_update()
            try:
                outputs = self._run_single(path)
                success += 1
                if (
                    self.state.task_type == TASK_CONVERT_AUDIO
                    and self.state.delete_original
                    and outputs
                    and 0 <= index - 1 < len(self.state.files)
                ):
                    self.state.files[index - 1] = outputs[-1]
                self.state.completed_count = success
                self.state.progress_value = index / total if total else 1.0
                if outputs:
                    self.state.last_output_path = outputs[-1]
            except Exception as exc:
                errors.append(f"{path.name}: {_human_error(exc)}")
                self.state.completed_count = success
                self._emit_update()

        return success, total, errors

    def _run_single(self, path: Path) -> list[Path]:
        prepared_path = path
        temp_dir = None
        if self.state.trim_enabled:
            prepared_path, temp_dir, self.current_process = build_trimmed_input(
                path,
                self.state.trim_start,
                self.state.trim_end,
            )
        task_type = self.state.task_type
        try:
            if task_type in {TASK_EXTRACT_VOICE, TASK_EXTRACT_BGM}:
                return self._run_separation(path, prepared_path)
            if task_type == TASK_NORMALIZE_VOLUME:
                return [self._run_normalize(path, prepared_path)]
            if task_type == TASK_CONVERT_AUDIO:
                return [self._run_convert(path, prepared_path)]
            if task_type == TASK_COMPRESS_AUDIO:
                return [self._run_compress(path, prepared_path)]
            if task_type == TASK_ENHANCE_AUDIO:
                return [self._run_enhance(path, prepared_path)]
            raise ValueError(f"Unknown task: {task_type}")
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()

    def _run_separation(self, path: Path, input_path: Path) -> list[Path]:
        self.state.active_backend = ""
        if self.state.audio_separator_available and self._audio_separator_cli:
            try:
                outputs = self._run_audio_separator(path, input_path)
                self.state.active_backend = "audio-separator"
                return outputs
            except Exception as exc:
                if not self.state.demucs_available:
                    raise
                self.state.detail_text = f"audio-separator fallback: {_human_error(exc)}"
        if self.state.demucs_available:
            outputs = self._run_demucs_fallback(path, input_path)
            self.state.active_backend = "demucs"
            return outputs
        raise RuntimeError("No separation backend available. Install audio-separator or demucs.")

    def _run_audio_separator(self, path: Path, input_path: Path) -> list[Path]:
        if not self._audio_separator_cli:
            raise RuntimeError("audio-separator CLI not found")
        output_dir = self.output_dir_for_preview(path)
        if output_dir is None:
            raise RuntimeError("No output directory available.")
        output_dir.mkdir(parents=True, exist_ok=True)
        before = {entry.resolve() for entry in output_dir.glob("*")}
        cmd = [
            self._audio_separator_cli,
            str(input_path),
            "--model_filename",
            self.state.model,
            "--output_format",
            self.state.separator_output_format,
            "--output_dir",
            str(output_dir),
        ]
        if self.state.stem_mode != "All model stems":
            cmd.extend(["--single_stem", _stem_name(self.state.task_type)])
        if self.state.chunk_duration > 0:
            cmd.extend(["--chunk_duration", str(self.state.chunk_duration)])

        self.current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        _stdout, stderr = self.current_process.communicate()
        if self.current_process.returncode != 0:
            raise RuntimeError(stderr.strip() or "audio-separator failed")

        after = [entry.resolve() for entry in output_dir.glob("*") if entry.is_file()]
        outputs = [entry for entry in after if entry not in before]
        if not outputs:
            outputs = [entry for entry in after if path.stem.lower() in entry.stem.lower()]
        if not outputs:
            raise RuntimeError("audio-separator produced no output files")

        if self.state.stem_mode == "All model stems":
            return sorted(Path(item) for item in outputs)

        source = Path(outputs[0])
        suffix = _legacy_suffix(self.state.task_type) if self.state.output_mode == "source_folder" else ("_voice" if self.state.task_type == TASK_EXTRACT_VOICE else "_bgm")
        renamed = get_safe_path(output_dir / f"{path.stem}{suffix}.{self.state.separator_output_format}")
        if source.resolve() != renamed.resolve():
            shutil.move(str(source), str(renamed))
        return [renamed]

    def _run_demucs_fallback(self, path: Path, input_path: Path) -> list[Path]:
        output_dir = self.output_dir_for_preview(path)
        if output_dir is None:
            raise RuntimeError("No output directory available.")
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_root = output_dir / "_demucs_tmp"
        model = "htdemucs"
        cmd = [
            sys.executable,
            "-m",
            "demucs",
            "-n",
            model,
            "--two-stems=vocals",
            "-o",
            str(temp_root),
            str(input_path),
        ]
        self.current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        _stdout, stderr = self.current_process.communicate()
        if self.current_process.returncode != 0:
            raise RuntimeError(stderr.strip() or "demucs failed")

        desired_stem = "vocals.wav" if self.state.task_type == TASK_EXTRACT_VOICE else "no_vocals.wav"
        produced = temp_root / model / path.stem / desired_stem
        if not produced.exists():
            raise RuntimeError("Demucs output stem not found")

        suffix = _legacy_suffix(self.state.task_type) if self.state.output_mode == "source_folder" else ("_voice" if self.state.task_type == TASK_EXTRACT_VOICE else "_bgm")
        final_ext = f".{self.state.separator_output_format}"
        final_path = get_safe_path(output_dir / f"{path.stem}{suffix}{final_ext}")
        if produced.suffix.lower() == final_ext.lower():
            shutil.copy2(produced, final_path)
        else:
            ffmpeg = get_ffmpeg()
            transcode_cmd = [ffmpeg, "-i", str(produced), "-y", str(final_path)]
            subprocess.run(transcode_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        return [final_path]

    def _run_normalize(self, path: Path, input_path: Path) -> Path:
        output_dir = self.output_dir_for_preview(path)
        if output_dir is None:
            raise RuntimeError("No output directory available.")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_name = f"{path.stem}_normalized{path.suffix}" if self.state.output_mode == "source_folder" else f"{path.stem}{path.suffix}"
        output_path = get_safe_path(output_dir / output_name)

        if self._ffmpeg_normalize_cli or _module_available("ffmpeg_normalize"):
            cmd = [
                self._ffmpeg_normalize_cli or sys.executable,
                str(input_path),
                "-nt",
                "ebu",
                "-t",
                str(self.state.target_loudness),
                "-lrt",
                str(self.state.loudness_range),
                "-tp",
                str(self.state.true_peak),
                "-o",
                str(output_path),
                "-f",
            ]
            if not self._ffmpeg_normalize_cli:
                cmd = [
                    sys.executable,
                    "-m",
                    "ffmpeg_normalize",
                    *cmd[1:],
                ]
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            _stdout, stderr = self.current_process.communicate()
            if self.current_process.returncode == 0 and output_path.exists():
                return output_path
            fallback_reason = stderr.strip() or "ffmpeg-normalize failed"
            self.state.detail_text = fallback_reason

        normalize_service = AudioNormalizeService()
        original_target = self.state.target_loudness
        original_peak = self.state.true_peak
        original_range = self.state.loudness_range
        result = {"errors": []}

        def on_complete(success: int, _total: int, errors: list[str], _last_output: Path | None) -> None:
            result["success"] = success
            result["errors"] = errors

        normalize_service.normalize_audio(
            [input_path],
            target_loudness=original_target,
            true_peak=original_peak,
            loudness_range=original_range,
            on_complete=on_complete,
        )
        if result.get("errors"):
            raise RuntimeError(result["errors"][0])
        produced = input_path.with_name(f"{input_path.stem}_normalized{input_path.suffix}")
        if not produced.exists():
            raise RuntimeError("Normalization output not found")
        if produced.resolve() != output_path.resolve():
            shutil.move(str(produced), str(output_path))
        return output_path

    def _run_convert(self, path: Path, input_path: Path) -> Path:
        output_dir = self.output_dir_for_preview(path)
        if output_dir is None:
            raise RuntimeError("No output directory available.")
        output_dir.mkdir(parents=True, exist_ok=True)
        fmt = self.state.convert_output_format.lower()
        output_name = f"{path.stem}_conv.{fmt}" if self.state.output_mode == "source_folder" else f"{path.stem}.{fmt}"
        output_path = get_safe_path(output_dir / output_name)

        service = AudioConvertService()
        errors: list[str] = []

        def on_complete(_success: int, _total: int, completion_errors: list[str], _last_output: Path | None) -> None:
            errors.extend(completion_errors)

        service.convert_audio(
            [input_path],
            output_format=self.state.convert_output_format,
            quality=self.state.convert_quality,
            copy_metadata=self.state.copy_metadata,
            save_to_new_folder=False,
            custom_output_dir=output_dir,
            delete_original=False,
            on_complete=on_complete,
        )
        if errors:
            raise RuntimeError(errors[0])
        converted = next(output_dir.glob(f"{path.stem}.{fmt}"), None)
        if converted is None:
            converted = next(output_dir.glob(f"{path.stem}_conv.{fmt}"), None)
        if converted is None and input_path.stem != path.stem:
            converted = next(output_dir.glob(f"{input_path.stem}.{fmt}"), None)
        if converted is None and input_path.stem != path.stem:
            converted = next(output_dir.glob(f"{input_path.stem}_conv.{fmt}"), None)
        if converted is None:
            raise RuntimeError("Converted output not found")
        if converted.resolve() != output_path.resolve():
            shutil.move(str(converted), str(output_path))
        if self.state.delete_original and path.exists():
            try:
                path.unlink()
            except Exception as exc:
                raise RuntimeError(f"Converted, but failed to delete original: {_human_error(exc)}") from exc
        return output_path

    def _run_compress(self, path: Path, input_path: Path) -> Path:
        output_dir = self.output_dir_for_preview(path)
        if output_dir is None:
            raise RuntimeError("No output directory available.")
        output_dir.mkdir(parents=True, exist_ok=True)
        fmt = self.state.compress_output_format.lower()
        output_name = f"{path.stem}_compressed.{fmt}" if self.state.output_mode == "source_folder" else f"{path.stem}.{fmt}"
        output_path = get_safe_path(output_dir / output_name)
        self.current_process = run_ffmpeg_compress(
            input_path,
            output_path,
            fmt,
            self.state.compress_level,
            self.state.copy_metadata,
        )
        return output_path

    def _run_enhance(self, path: Path, input_path: Path) -> Path:
        output_dir = self.output_dir_for_preview(path)
        if output_dir is None:
            raise RuntimeError("No output directory available.")
        output_dir.mkdir(parents=True, exist_ok=True)
        fmt = self.state.enhance_output_format.lower()
        output_name = f"{path.stem}_enhanced.{fmt}" if self.state.output_mode == "source_folder" else f"{path.stem}.{fmt}"
        output_path = get_safe_path(output_dir / output_name)
        self.current_process = run_ffmpeg_enhance(
            input_path,
            output_path,
            self.state.enhance_profile,
            fmt,
            self.state.copy_metadata,
        )
        return output_path

    def _emit_update(self, **payload) -> None:
        if self.on_update is not None:
            self.on_update(**payload)


def run_console_task(
    task_type: str,
    targets: list[Path],
    *,
    backend: str = "audio-separator",
    model: str | None = None,
    separator_output_format: str = "wav",
    stem_mode: str = "Selected stem only",
    target_loudness: float = -16.0,
    true_peak: float = -1.5,
    loudness_range: float = 11.0,
    convert_output_format: str = "MP3",
    convert_quality: str = "High",
    copy_metadata: bool = True,
    delete_original: bool = False,
) -> int:
    service = AudioToolboxService(AudioToolboxState())
    return service.run_console(
        task_type,
        targets,
        model=model,
        separator_output_format=separator_output_format,
        stem_mode=stem_mode,
        target_loudness=target_loudness,
        true_peak=true_peak,
        loudness_range=loudness_range,
        convert_output_format=convert_output_format,
        convert_quality=convert_quality,
        copy_metadata=copy_metadata,
        delete_original=delete_original,
    )
