from pathlib import Path


def convert_format(target_path: str):
    from features.audio.audio_convert.audio_convert_qt_app import start_app

    targets = [str(target_path)] if isinstance(target_path, (str, Path)) else [str(p) for p in target_path]
    app_root = Path(__file__).resolve().parents[3] / "audio_convert"
    start_app(targets, app_root)


def optimize_volume(target_path: str):
    from features.audio.normalize_volume_console import run_normalize_volume_console

    targets = [str(target_path)] if isinstance(target_path, (str, Path)) else [str(p) for p in target_path]
    run_normalize_volume_console([Path(path) for path in targets])


def extract_voice(target_path: str):
    from features.audio.separate_console import run_separate_console

    targets = [str(target_path)] if isinstance(target_path, (str, Path)) else [str(p) for p in target_path]
    run_separate_console([Path(path) for path in targets], stem_kind="voice")


def extract_bgm(target_path: str):
    from features.audio.separate_console import run_separate_console

    targets = [str(target_path)] if isinstance(target_path, (str, Path)) else [str(p) for p in target_path]
    run_separate_console([Path(path) for path in targets], stem_kind="bgm")
