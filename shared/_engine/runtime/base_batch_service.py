"""Reusable mixins for batch-processing services.

We don't impose a single base class (services already vary between
``__init__(self)`` and ``__init__(self, state, on_update)`` shapes).
Instead this module exposes orthogonal mixins so services can opt into
the pieces they need:

* :class:`BatchInputMixin` — ``add_inputs`` / ``remove_input_at`` /
  ``clear_inputs`` against ``self.state.files``.
* :class:`ParameterValuesMixin` — ``update_parameter`` against
  ``self.state.parameter_values``.
* :class:`OutputOptionsMixin` — ``update_output_options`` /
  ``resolve_output_dir`` / ``reveal_output_dir`` against
  ``self.state.output_options``.
* :class:`WorkflowRegistryMixin` — declarative ``_workflow_names`` /
  ``_ui_definition`` + getter API.

All mixins assume ``self.state`` is a dataclass derived from
:class:`shared._engine.runtime.base_batch_state.BaseBatchState` (or
that exposes the same field names).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any


class BatchInputMixin:
    """``state.files`` management."""

    state: Any  # set by host service

    def add_inputs(self, paths: list[str | Path]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            if path in self.state.files:
                continue
            self.state.files.append(path)
        self._after_inputs_changed()

    def remove_input_at(self, index: int) -> None:
        if 0 <= index < len(self.state.files):
            self.state.files.pop(index)
            self._after_inputs_changed()

    def clear_inputs(self) -> None:
        self.state.files.clear()
        self._after_inputs_changed()

    def _after_inputs_changed(self) -> None:
        """Override to notify UI (e.g. call ``self.on_update()``)."""
        on_update = getattr(self, "on_update", None)
        if on_update is not None:
            try:
                on_update()
            except Exception:
                pass


class ParameterValuesMixin:
    """``state.parameter_values`` dict management."""

    state: Any

    def update_parameter(self, key: str, value: Any) -> None:
        self.state.parameter_values[key] = value


class OutputOptionsMixin:
    """``state.output_options`` + per-app output dir resolution."""

    state: Any

    def update_output_options(
        self,
        output_dir: str | Path | None,
        file_prefix: str,
        open_folder_after_run: bool,
        export_session_json: bool,
    ) -> None:
        opts = self.state.output_options
        if isinstance(output_dir, str):
            output_dir = Path(output_dir.strip()) if output_dir.strip() else None
        opts.output_dir = output_dir
        opts.file_prefix = file_prefix.strip() or opts.file_prefix or "output"
        opts.open_folder_after_run = open_folder_after_run
        opts.export_session_json = export_session_json

    def resolve_output_dir(self) -> Path | None:
        if self.state.output_options.output_dir:
            return self.state.output_options.output_dir
        if not self.state.files:
            return None
        return self.state.files[0].parent

    def reveal_output_dir(self) -> None:
        target = self.resolve_output_dir()
        if target and target.exists() and os.name == "nt":
            try:
                os.startfile(target)  # type: ignore[attr-defined]
            except Exception:
                pass


class SessionExportMixin:
    """Write a JSON dump of ``self.state`` next to the outputs."""

    state: Any

    def export_session(self, filename: str = "session.json") -> Path:
        target = self._session_dir()
        target.mkdir(parents=True, exist_ok=True)
        out_path = target / filename
        out_path.write_text(
            json.dumps(asdict(self.state), default=str, indent=2),
            encoding="utf-8",
        )
        return out_path

    def _session_dir(self) -> Path:
        resolve = getattr(self, "resolve_output_dir", None)
        if resolve:
            try:
                target = resolve()
                if target:
                    return target
            except Exception:
                pass
        return Path.cwd()


class WorkflowRegistryMixin:
    """Declarative ``_workflow_names`` + ``_ui_definition``.

    Subclasses set these as instance or class attributes; the mixin
    provides the canonical getter API and seeds ``parameter_values``
    from defaults.
    """

    state: Any
    _workflow_names: list[str]
    _ui_definition: list[dict[str, Any]]

    def get_workflow_names(self) -> list[str]:
        return list(self._workflow_names)

    def select_workflow(self, name: str) -> None:
        self.state.workflow_name = name

    def get_ui_definition(self) -> list[dict[str, Any]]:
        return list(self._ui_definition)

    def seed_parameter_defaults(self) -> None:
        """Populate ``state.parameter_values`` from each entry's default."""
        for item in self._ui_definition:
            default = item.get("default")
            if default is None:
                continue
            key = item.get("key")
            if key and key not in self.state.parameter_values:
                self.state.parameter_values[key] = default


__all__ = [
    "BatchInputMixin",
    "ParameterValuesMixin",
    "OutputOptionsMixin",
    "SessionExportMixin",
    "WorkflowRegistryMixin",
]
