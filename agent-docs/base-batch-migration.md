# Migrating a batch service to the shared base classes

This is the runbook for porting existing `*_service.py` + `*_state.py`
pairs to the foundations added in
`shared/_engine/runtime/base_batch_state.py` and
`shared/_engine/runtime/base_batch_service.py`. Apply this incrementally
— one service per commit. Do not attempt a flag-day migration.

## TL;DR

Mixins live at `shared/_engine/runtime/base_batch_service.py`:

* `BatchInputMixin` — `add_inputs` / `remove_input_at` / `clear_inputs`.
* `ParameterValuesMixin` — `update_parameter`.
* `OutputOptionsMixin` — `update_output_options` / `resolve_output_dir`
  / `reveal_output_dir`.
* `SessionExportMixin` — `export_session(filename)`.
* `WorkflowRegistryMixin` — `get_workflow_names` / `select_workflow` /
  `get_ui_definition` / `seed_parameter_defaults`.

State base at `shared/_engine/runtime/base_batch_state.py`:

* `OutputOptions` dataclass (output_dir/file_prefix/open_folder_after_run/export_session_json).
* `BaseBatchState` dataclass (files, is_processing, progress_value,
  status_text, completed_count, total_count, cancel_flag, errors,
  custom_output_dir, output_options, parameter_values).

## State migration

```python
# BEFORE
@dataclass
class MyState:
    files: list[Path] = field(default_factory=list)
    is_processing: bool = False
    progress_value: float = 0.0
    status_text: str = "Ready"
    completed_count: int = 0
    total_count: int = 0
    cancel_flag: bool = False
    output_options: OutputOptions = field(default_factory=OutputOptions)
    parameter_values: dict = field(default_factory=dict)
    # app-specific:
    workflow_name: str = "..."
    preview_path: Path | None = None

# AFTER
from shared._engine.runtime.base_batch_state import BaseBatchState

@dataclass
class MyState(BaseBatchState):
    workflow_name: str = "..."
    preview_path: Path | None = None
```

Python dataclass inheritance requires the parent's default-valued fields
to remain in MRO order. Since every BaseBatchState field has a default,
subclasses simply add their own defaulted fields. No field-order
gymnastics needed.

If the app's `OutputOptions` had per-app defaults (e.g. `file_prefix =
"resized"`), subclass it:

```python
from shared._engine.runtime.base_batch_state import OutputOptions

@dataclass
class MyOutputOptions(OutputOptions):
    file_prefix: str = "resized"

@dataclass
class MyState(BaseBatchState):
    output_options: MyOutputOptions = field(default_factory=MyOutputOptions)
```

## Service migration

```python
# BEFORE
class MyService:
    def __init__(self):
        self.state = MyState()
        self._workflow_names = [...]
        self._ui_definition = [...]
        for item in self._ui_definition:
            if item["default"] is not None:
                self.state.parameter_values[item["key"]] = item["default"]

    def get_workflow_names(self): ...
    def select_workflow(self, name): ...
    def get_ui_definition(self): ...
    def add_inputs(self, paths): ...           # canonical
    def remove_input_at(self, index): ...      # canonical
    def clear_inputs(self): ...                # canonical
    def update_parameter(self, k, v): ...
    def update_output_options(self, ...): ...
    def resolve_output_dir(self): ...
    def reveal_output_dir(self): ...

# AFTER
from shared._engine.runtime.base_batch_service import (
    BatchInputMixin, ParameterValuesMixin, OutputOptionsMixin,
    WorkflowRegistryMixin,
)

class MyService(
    BatchInputMixin,
    ParameterValuesMixin,
    OutputOptionsMixin,
    WorkflowRegistryMixin,
):
    _workflow_names = [...]
    _ui_definition = [...]

    def __init__(self):
        self.state = MyState()
        self.seed_parameter_defaults()
```

That's it for the canonical methods; ~30–60 lines of boilerplate
disappear per service.

## Custom behaviour around inputs

Services that track `preview_path` (image_resizer, image_convert) need
to extend the mixin instead of replacing it. Override the
`_after_inputs_changed` hook:

```python
class MyService(BatchInputMixin, ...):
    def _after_inputs_changed(self) -> None:
        super()._after_inputs_changed()
        if self.state.files and self.state.preview_path is None:
            self.state.preview_path = self.state.files[0]
```

Or override `add_inputs` entirely to add per-file validation (e.g.
image_resizer's pixel-budget check). Just call the rest of the mixins
unchanged.

## What about ServiceBridge / threading?

`ServiceBridge` already lives at
`shared/_engine/runtime/service_bridge.py` (from Phase 1). For batch
services that emit cross-thread updates, instantiate the bridge and
pass `self.service_bridge.emit_update` as the `on_update` callback —
the `BatchInputMixin._after_inputs_changed` hook will pick it up via
`self.on_update`.

## What's intentionally NOT moved into the base

* `_process_parallel` (ThreadPoolExecutor batch runner) — currently
  only in `video_convert_service.py` and `image_convert_service.py`.
  Once a third service adopts it, we'll extract a
  `BaseParallelExecutor` mixin. See audit notes.
* `_run_single_job` shape — currently three conventions across the
  repo (`dict`, `tuple`, raise). Pick one when extracting
  `BaseParallelExecutor`.

## Checklist for each migration

1. Subclass `BaseBatchState`. Move any fields named identically to base
   fields out of the local definition.
2. Add the mixins to the service class.
3. Delete the canonical methods (`get_workflow_names`,
   `select_workflow`, `get_ui_definition`, `add_inputs`,
   `remove_input_at`, `clear_inputs`, `update_parameter`,
   `update_output_options`, `resolve_output_dir`, `reveal_output_dir`)
   one by one if their body matches the mixin.
4. Replace the seed loop with `self.seed_parameter_defaults()`.
5. Run `python -m py_compile <service>.py` and `<state>.py`.
6. If the app has a smoke test (`test_locally.bat`), run it.
7. Commit one service at a time so reverts are clean.
