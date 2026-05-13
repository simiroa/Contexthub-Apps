"""Shared dataclasses for batch-processing services.

Across this repo, ~18 ``*_state.py`` files reinvented the same
progress / cancellation block (`is_processing`, `progress_value`,
`status_text`, `completed_count`, `total_count`, `cancel_flag`) and 18
services repeated the same ``OutputOptions`` shape with slight default
drift. Consolidate them here so every batch service speaks the same
language.

New services should subclass `BaseBatchState` (using
``@dataclass(kw_only=False)`` semantics — see Python 3.10+ inheritance
rules) and add their own service-specific fields. Existing services
that already define an `output_options` field can switch from a local
``OutputOptions`` to the one defined here.

Note on field-default semantics
-------------------------------

Dataclass inheritance requires that fields with defaults follow fields
without defaults. Every field on `BaseBatchState` has a default, so
subclasses can add either required (no-default) fields followed by
default-valued ones, or simply add more defaulted fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OutputOptions:
    """Per-app output configuration.

    Subclasses with different defaults should subclass this dataclass
    rather than redefining the shape — see e.g.
    ``image_convert_state.OutputOptions``.
    """

    output_dir: Path | None = None
    file_prefix: str = "output"
    open_folder_after_run: bool = True
    export_session_json: bool = True


@dataclass
class BaseBatchState:
    """Common progress + cancellation fields for batch services."""

    files: list[Path] = field(default_factory=list)
    is_processing: bool = False
    progress_value: float = 0.0
    status_text: str = "Ready"
    completed_count: int = 0
    total_count: int = 0
    cancel_flag: bool = False
    errors: list[str] = field(default_factory=list)
    custom_output_dir: Path | None = None
    output_options: OutputOptions = field(default_factory=OutputOptions)
    parameter_values: dict[str, Any] = field(default_factory=dict)


__all__ = ["OutputOptions", "BaseBatchState"]
