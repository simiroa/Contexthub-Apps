import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from utils import paths

PROFILE_FILE = paths.QWEN_TTS_DIR / "profiles.json"
SUPPORTED_SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]
SUPPORTED_LANGUAGES = ["Auto", "Chinese", "English", "Japanese", "Korean", "German", "French", "Russian", "Portuguese", "Spanish", "Italian"]
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"}
TONE_PRESETS = {
    "natural": "Speak naturally with clear pacing and a calm, confident tone.",
    "warm": "Use a warm, friendly tone with gentle emphasis and smooth phrasing.",
    "energetic": "Deliver the line with bright energy, crisp emphasis, and upbeat pacing.",
    "precise": "Use precise diction, short pauses, and a clean professional delivery.",
}


def default_profiles():
    return [
        {"id": "narrator", "name": "Narrator", "mode": "custom_voice", "speaker": "Vivian", "instruct": TONE_PRESETS["natural"], "ref_audio": "", "ref_text": "", "x_vector_only": False},
        {"id": "warm_host", "name": "Warm Host", "mode": "custom_voice", "speaker": "Serena", "instruct": TONE_PRESETS["warm"], "ref_audio": "", "ref_text": "", "x_vector_only": False},
        {"id": "voice_design", "name": "Designed Voice", "mode": "voice_design", "speaker": "Vivian", "instruct": "A clear, modern Korean female voice in her late twenties with soft warmth, clean diction, and steady confidence.", "ref_audio": "", "ref_text": "", "x_vector_only": False},
    ]


def load_profiles():
    if PROFILE_FILE.exists():
        try:
            data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
            if data:
                return data
        except Exception:
            pass
    profiles = default_profiles()
    save_profiles(profiles)
    return profiles


def save_profiles(profiles):
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_FILE.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")


def profile_names(profiles):
    return [profile["name"] for profile in profiles]


def profile_by_name(profiles, name):
    return next((profile for profile in profiles if profile["name"] == name), profiles[0])


def ensure_unique_profile_name(profiles, name, profile_id=None):
    return not any(profile["name"] == name and profile["id"] != profile_id for profile in profiles)


def clone_quality_status(profile):
    if profile.get("mode") != "voice_clone":
        return None
    ref_audio = (profile.get("ref_audio") or "").strip()
    ref_text = (profile.get("ref_text") or "").strip()
    if not ref_audio:
        return ("missing", "Missing reference audio")
    audio_path = Path(ref_audio)
    if not audio_path.exists():
        return ("missing", "Reference file not found")
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            duration = wav_file.getnframes() / max(1, wav_file.getframerate())
    except Exception:
        return ("warning", "Reference loaded, duration unknown")
    if duration < 2.5:
        return ("warning", "Reference is short")
    if not ref_text:
        return ("warning", "Transcript missing")
    return ("good", "Reference ready")


def prefill_messages(target_path, profiles, sample_text):
    messages = []
    selected_profile = profiles[0]["name"]
    imported_profile = None
    if target_path and target_path.exists():
        if target_path.suffix.lower() in {".txt", ".md"}:
            try:
                sample_text = target_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
        elif target_path.suffix.lower() in AUDIO_EXTENSIONS:
            imported_profile = {"id": "clone_import", "name": "Imported Clone", "mode": "voice_clone", "speaker": "Vivian", "instruct": "", "ref_audio": str(target_path), "ref_text": "", "x_vector_only": False}
            profiles.append(imported_profile)
            selected_profile = imported_profile["name"]

    messages.append({"id": "msg_1", "role": "Narrator", "profile": selected_profile, "tone": "natural", "text": sample_text.strip(), "status": "ready", "output": ""})
    second_profile = profiles[1]["name"] if len(profiles) > 1 else selected_profile
    messages.append({"id": "msg_2", "role": "Host", "profile": second_profile, "tone": "warm", "text": "This second line shows how another profile can answer in the same batch.", "status": "ready", "output": ""})
    return messages, profiles


def _load_settings():
    try:
        from contexthub.core.settings import load_settings

        return load_settings()
    except Exception:
        return {}


def _find_conda_exe(settings):
    candidates = [
        settings.get("AI_CONDA_EXE"),
        os.environ.get("CTX_AI_CONDA_EXE"),
        os.environ.get("CONDA_EXE"),
        shutil.which("conda"),
        shutil.which("conda.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def _resolve_conda_python(settings):
    env_path = settings.get("AI_CONDA_ENV_PATH") or os.environ.get("CTX_AI_CONDA_ENV_PATH")
    if env_path:
        candidate = Path(env_path) / "python.exe"
        return candidate if candidate.exists() else None

    conda_exe = _find_conda_exe(settings)
    if not conda_exe:
        return None

    env_name = settings.get("AI_CONDA_ENV_NAME") or os.environ.get("CTX_AI_CONDA_ENV_NAME") or "contexthub-ai"
    try:
        result = subprocess.run(
            [str(conda_exe), "info", "--base"],
            capture_output=True,
            text=True,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        base_path = Path((result.stdout or "").strip())
        candidate = base_path / "envs" / env_name / "python.exe"
        return candidate if candidate.exists() else None
    except Exception:
        return None


def resolve_backend_python():
    settings = _load_settings()
    if settings.get("AI_ENV_MODE", "prefer_conda") != "disabled":
        conda_python = _resolve_conda_python(settings)
        if conda_python:
            return conda_python

    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        embedded = parent / "tools" / "python" / "python.exe"
        if embedded.exists():
            return embedded
    return Path(sys.executable)


def build_job(message, profiles, device, language):
    profile = profile_by_name(profiles, message["profile"])
    if profile["mode"] == "voice_clone" and not profile["ref_audio"]:
        raise ValueError("Voice Clone profiles need a reference audio file.")
    if profile["mode"] == "voice_design" and not (profile.get("instruct") or "").strip():
        raise ValueError("Voice Design profiles need a voice description.")
    instruct = profile["instruct"]
    if profile["mode"] != "voice_clone" and message["tone"] in TONE_PRESETS:
        instruct = f"{instruct}\n{TONE_PRESETS[message['tone']]}".strip()
    return {
        "mode": profile["mode"],
        "size": "1.7B",
        "device": device,
        "text": message["text"],
        "language": language,
        "speaker": profile["speaker"],
        "instruct": instruct,
        "ref_audio": profile["ref_audio"],
        "ref_text": profile["ref_text"],
        "x_vector_only": bool(profile["x_vector_only"]),
    }


def run_jobs_sync(jobs, output_dir, device, on_line=None):
    backend_python = resolve_backend_python()
    script_path = Path(__file__).with_name("qwen3_tts.py")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as handle:
        json.dump({"jobs": jobs}, handle, ensure_ascii=False, indent=2)
        jobs_file = handle.name

    command = [str(backend_python), str(script_path), "--size", "1.7B", "--device", device, "--jobs-file", jobs_file, "--output-dir", str(output_dir)]
    lines = []
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=0x08000000 if sys.platform == "win32" else 0,
            cwd=str(script_path.parent.parent.parent.parent),
        )
        if process.stdout:
            for raw in process.stdout:
                line = raw.rstrip()
                lines.append(line)
                if on_line:
                    on_line(line)
        process.wait()
        payload = None
        for line in lines:
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    payload = json.loads(line)
                except Exception:
                    pass
        return process.returncode == 0, payload, "\n".join(lines)
    finally:
        try:
            Path(jobs_file).unlink(missing_ok=True)
        except Exception:
            pass
