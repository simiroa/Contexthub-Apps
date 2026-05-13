"""Thin shim — canonical implementation lives in
``shared._engine.utils.headless_inputs``. Kept here so existing
``from utils.headless_inputs import ...`` call sites in each category's
``main.py`` continue to work unchanged.
"""
from shared._engine.utils.headless_inputs import (  # noqa: F401
    AUDIO_IDS,
    DIR_IDS,
    DOC_IDS,
    IMAGE_IDS,
    MESH_IDS,
    SEQUENCE_IDS,
    VIDEO_IDS,
    get_headless_targets,
)

__all__ = [
    "AUDIO_IDS",
    "DIR_IDS",
    "DOC_IDS",
    "IMAGE_IDS",
    "MESH_IDS",
    "SEQUENCE_IDS",
    "VIDEO_IDS",
    "get_headless_targets",
]
