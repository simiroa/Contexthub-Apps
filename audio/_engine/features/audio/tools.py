from pathlib import Path


def convert_format(target_path: str):
    from features.audio.audio_convert.flet_app import start_app
    targets = [str(target_path)] if isinstance(target_path, (str, Path)) else [str(p) for p in target_path]
    start_app(targets)


def optimize_volume(target_path: str):
    from features.audio.normalize_flet_app import start_app
    targets = [str(target_path)] if isinstance(target_path, (str, Path)) else [str(p) for p in target_path]
    start_app(targets)


def extract_voice(target_path: str):
    from features.audio.separate_flet_app import start_app
    targets = [str(target_path)] if isinstance(target_path, (str, Path)) else [str(p) for p in target_path]
    start_app(
        targets,
        title="Extract Voice",
        description="Separate voice-focused stems from music or mixed source audio.",
        initial_mode="Vocals vs Backing (2)",
    )


def extract_bgm(target_path: str):
    from features.audio.separate_flet_app import start_app
    targets = [str(target_path)] if isinstance(target_path, (str, Path)) else [str(p) for p in target_path]
    start_app(
        targets,
        title="Extract BGM",
        description="Separate background music from vocal-led source audio.",
        initial_mode="Vocals vs Backing (2)",
    )
