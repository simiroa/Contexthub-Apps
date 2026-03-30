from __future__ import annotations

TASK_EXTRACT_VOICE = "extract_voice"
TASK_EXTRACT_BGM = "extract_bgm"
TASK_NORMALIZE_VOLUME = "normalize_volume"
TASK_CONVERT_AUDIO = "convert_audio"
TASK_COMPRESS_AUDIO = "compress_audio"
TASK_ENHANCE_AUDIO = "enhance_audio"

TASK_LABELS = {
    TASK_EXTRACT_VOICE: "Extract Voice",
    TASK_EXTRACT_BGM: "Extract BGM",
    TASK_NORMALIZE_VOLUME: "Normalize Volume",
    TASK_CONVERT_AUDIO: "Convert Audio",
    TASK_COMPRESS_AUDIO: "Compress Audio",
    TASK_ENHANCE_AUDIO: "Enhance Audio",
}

SEPARATOR_MODELS = [
    "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    "UVR_MDXNET_KARA_2.onnx",
    "htdemucs_ft.yaml",
]
SEPARATOR_OUTPUT_FORMATS = ["wav", "flac", "mp3", "m4a"]
SEPARATOR_STEM_MODES = ["Selected stem only", "All model stems"]

CONVERT_OUTPUT_FORMATS = ["MP3", "WAV", "FLAC", "M4A", "OGG", "AAC"]
CONVERT_QUALITIES = ["High", "Medium", "Low"]

COMPRESS_OUTPUT_FORMATS = ["M4A", "MP3", "AAC", "OGG"]
COMPRESS_LEVELS = ["Quality", "Balanced", "Small"]

ENHANCE_PROFILES = ["Speech Clean", "Clarity", "Presence"]
ENHANCE_OUTPUT_FORMATS = ["WAV", "FLAC", "M4A", "MP3"]

TASK_STACK_INDEX = {
    TASK_EXTRACT_VOICE: 0,
    TASK_EXTRACT_BGM: 0,
    TASK_NORMALIZE_VOLUME: 1,
    TASK_CONVERT_AUDIO: 2,
    TASK_COMPRESS_AUDIO: 3,
    TASK_ENHANCE_AUDIO: 4,
}


def export_formats_for_task(task_type: str) -> list[str]:
    if task_type in {TASK_EXTRACT_VOICE, TASK_EXTRACT_BGM}:
        return SEPARATOR_OUTPUT_FORMATS
    if task_type == TASK_CONVERT_AUDIO:
        return CONVERT_OUTPUT_FORMATS
    if task_type == TASK_COMPRESS_AUDIO:
        return COMPRESS_OUTPUT_FORMATS
    if task_type == TASK_ENHANCE_AUDIO:
        return ENHANCE_OUTPUT_FORMATS
    return []
