import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np

current_dir = Path(__file__).resolve().parent
engine_dir = current_dir.parents[2]
if str(engine_dir) not in sys.path:
    sys.path.insert(0, str(engine_dir))

from utils import paths  # noqa: F401


def _write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 1:
        audio = audio[:, None]
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(pcm.shape[1])
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def _ensure_unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _resolve_model_id(mode: str, size: str) -> str:
    if mode == "custom_voice":
        return f"Qwen/Qwen3-TTS-12Hz-{size}-CustomVoice"
    if mode == "voice_design":
        return f"Qwen/Qwen3-TTS-12Hz-{size}-VoiceDesign"
    return f"Qwen/Qwen3-TTS-12Hz-{size}-Base"


def _build_model_kwargs(device: str):
    import torch

    resolved = device
    if device == "auto":
        resolved = "cuda:0" if torch.cuda.is_available() else "cpu"

    kwargs = {"device_map": resolved}
    if resolved.startswith("cuda"):
        kwargs["dtype"] = torch.bfloat16 if getattr(torch.cuda, "is_bf16_supported", lambda: False)() else torch.float16
        try:
            import flash_attn  # noqa: F401

            kwargs["attn_implementation"] = "flash_attention_2"
        except Exception:
            pass
    else:
        kwargs["dtype"] = torch.float32
    return kwargs


def _load_model_cache():
    try:
        from qwen_tts import Qwen3TTSModel
    except Exception as exc:
        print(f"[ERROR] Missing runtime dependency: {exc}", flush=True)
        raise

    cache = {}

    def _get(mode: str, size: str, device: str):
        key = (mode, size, device)
        if key not in cache:
            model_id = _resolve_model_id(mode, size)
            kwargs = _build_model_kwargs(device)
            print(f"[INFO] Loading model {model_id}", flush=True)
            cache[key] = Qwen3TTSModel.from_pretrained(model_id, **kwargs)
        return cache[key]

    return _get


def _generate_single(get_model, job: dict) -> tuple[np.ndarray, int]:
    mode = job["mode"]
    size = job.get("size", "1.7B")
    device = job.get("device", "cuda")

    if mode == "custom_voice":
        model = get_model(mode, size, device)
        wavs, sample_rate = model.generate_custom_voice(
            text=job["text"],
            language=job.get("language", "Auto"),
            speaker=job.get("speaker", "Vivian"),
            instruct=job.get("instruct") or None,
        )
        return wavs[0], sample_rate

    if mode == "voice_design":
        model = get_model(mode, size, device)
        wavs, sample_rate = model.generate_voice_design(
            text=job["text"],
            instruct=job.get("instruct") or "",
            language=job.get("language", "Auto"),
        )
        return wavs[0], sample_rate

    ref_audio = job.get("ref_audio")
    if not ref_audio:
        raise ValueError("ref_audio is required for voice_clone mode")
    model = get_model(mode, size, device)

    clone_kwargs = {
        "text": job["text"],
        "language": job.get("language", "Auto"),
        "ref_audio": ref_audio,
    }
    if job.get("ref_text"):
        clone_kwargs["ref_text"] = job["ref_text"]
    if job.get("x_vector_only"):
        clone_kwargs["x_vector_only_mode"] = True
    if job.get("voice_clone_prompt") is not None:
        clone_kwargs["voice_clone_prompt"] = job["voice_clone_prompt"]
    wavs, sample_rate = model.generate_voice_clone(**clone_kwargs)
    return wavs[0], sample_rate


def _prepare_batch_prompts(get_model, jobs: list[dict]) -> None:
    clone_groups = {}
    for index, job in enumerate(jobs):
        if job["mode"] != "voice_clone":
            continue
        key = (
            job.get("size", "1.7B"),
            job.get("device", "cuda"),
            job.get("ref_audio", ""),
            job.get("ref_text", ""),
            bool(job.get("x_vector_only")),
        )
        clone_groups.setdefault(key, []).append((index, job))

    for key, grouped_jobs in clone_groups.items():
        size, device, ref_audio, ref_text, x_vector_only = key
        if not ref_audio:
            continue
        model = get_model("voice_clone", size, device)
        prompt_items = model.create_voice_clone_prompt(
            ref_audio=ref_audio,
            ref_text=ref_text or None,
            x_vector_only_mode=x_vector_only,
        )
        for _, job in grouped_jobs:
            job["voice_clone_prompt"] = prompt_items


def _run_batch(get_model, batch_path: Path, output_dir: Path, device: str, size: str) -> int:
    payload = json.loads(batch_path.read_text(encoding="utf-8-sig"))
    jobs = payload.get("jobs", [])
    if not jobs:
        print("[ERROR] jobs file is empty", flush=True)
        return 1

    normalized_jobs = []
    for idx, job in enumerate(jobs, start=1):
        item = {
            "mode": job.get("mode", "custom_voice"),
            "size": job.get("size", size),
            "device": job.get("device", device),
            "text": (job.get("text") or "").strip(),
            "language": job.get("language", "Auto"),
            "speaker": job.get("speaker", "Vivian"),
            "instruct": job.get("instruct", ""),
            "ref_audio": job.get("ref_audio", ""),
            "ref_text": job.get("ref_text", ""),
            "x_vector_only": bool(job.get("x_vector_only", False)),
            "file_name": job.get("file_name") or f"{idx:03d}.wav",
        }
        if not item["text"]:
            raise ValueError(f"Job {idx} is missing text")
        normalized_jobs.append(item)

    _prepare_batch_prompts(get_model, normalized_jobs)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    total = len(normalized_jobs)
    for idx, job in enumerate(normalized_jobs, start=1):
        print(f"[INFO] Generating job {idx}/{total}: {job['file_name']}", flush=True)
        audio, sample_rate = _generate_single(get_model, job)
        output_path = _ensure_unique_output_path(output_dir / job["file_name"])
        _write_wav(output_path, audio, sample_rate)
        outputs.append(
            {
                "index": idx,
                "mode": job["mode"],
                "output": str(output_path),
            }
        )

    print(json.dumps({"status": "ok", "outputs": outputs}, ensure_ascii=False), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["custom_voice", "voice_clone", "voice_design"], default="custom_voice")
    parser.add_argument("--size", choices=["1.7B"], default="1.7B")
    parser.add_argument("--text", default="")
    parser.add_argument("--language", default="Auto")
    parser.add_argument("--speaker", default="Vivian")
    parser.add_argument("--instruct", default="")
    parser.add_argument("--ref-audio", default="")
    parser.add_argument("--ref-text", default="")
    parser.add_argument("--x-vector-only", action="store_true")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="cuda")
    parser.add_argument("--output", default="")
    parser.add_argument("--jobs-file", default="")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    try:
        get_model = _load_model_cache()
    except Exception:
        return 1

    if args.jobs_file:
        batch_path = Path(args.jobs_file)
        output_dir = Path(args.output_dir) if args.output_dir else batch_path.parent
        return _run_batch(get_model, batch_path, output_dir, args.device, args.size)

    if not args.text.strip():
        print("[ERROR] text is required", flush=True)
        return 1
    if not args.output:
        print("[ERROR] output is required", flush=True)
        return 1

    job = {
        "mode": args.mode,
        "size": args.size,
        "device": args.device,
        "text": args.text.strip(),
        "language": args.language,
        "speaker": args.speaker,
        "instruct": args.instruct,
        "ref_audio": args.ref_audio,
        "ref_text": args.ref_text,
        "x_vector_only": args.x_vector_only,
    }

    try:
        audio, sample_rate = _generate_single(get_model, job)
    except Exception as exc:
        print(f"[ERROR] {exc}", flush=True)
        return 1

    output_path = _ensure_unique_output_path(Path(args.output))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_wav(output_path, audio, sample_rate)
    print(json.dumps({"status": "ok", "output": str(output_path)}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
