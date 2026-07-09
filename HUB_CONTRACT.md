# Hub ↔ App Contract

This document is the canonical contract between **Contexthub** (the host
launcher, written in C# at `src/ContextHub.Host/`) and the apps in this
repository.

It captures **(a) what hub already guarantees**, **(b) what apps may assume**,
and **(c) the planned extension points** that the apps repo declares but hub
may not yet implement. Both sides should treat this file as the source of
truth and link to it from their READMEs.

> Hub-side implementation today lives in
> `src/ContextHub.Host/Services/ProcessRunner.cs` and `ConfigService.cs`.
> Anything described as "Planned" below is a hub-side TODO.

---

## 1. App launch flow

When the user invokes an app from hub:

1. Hub resolves the app's Python interpreter (override / bundled / system).
2. For `execution.mode == "gui"`, hub prefers `pythonw.exe` (no console window).
3. Hub spawns the app with `CreateNoWindow = true` (non-console modes),
   `UseShellExecute = false`, stdout/stderr redirected.
4. Hub merges the env-var sets described in §2 into the child process.
5. Hub sets the working directory to `manifest.execution.working_directory`
   (resolved relative to the app folder).
6. Hub tracks PID and updates app status (`starting` → `running`).
7. stdout/stderr is buffered and flushed to per-app log files.

---

## 2. Environment variables

### 2.1 Guaranteed (hub always sets)

| Variable          | Value                                                          |
| ----------------- | -------------------------------------------------------------- |
| `CTX_APP_ID`      | App id from `manifest.id`                                      |
| `CTX_APP_ROOT`    | Absolute path to the app folder                                |
| `CTX_ROOT`        | Hub root (`Contexthub/`)                                       |
| `CTX_SHARED_ROOT` | `{CTX_ROOT}/Runtimes/Shared/contexthub` (the python package)   |
| `CTX_THEME`       | User theme                                                     |
| `CTX_LANG`        | User language                                                  |
| `PYTHONPATH`      | `{CTX_ROOT}/Runtimes/Shared` is prepended                      |
| `PATH`            | `{CTX_ROOT}/Externals/*/bin` and tool overrides are prepended  |

### 2.2 Conditional (hub sets when configured)

| Variable                    | When set                                |
| --------------------------- | --------------------------------------- |
| `FFMPEG_PATH`               | `Config.Paths.FfmpegOverride` non-empty |
| `GIT_PATH`                  | `Config.Paths.GitOverride` non-empty    |
| `PYTHON_PATH`               | `Config.Paths.PythonOverride` non-empty |
| `<TOOL>_PATH`               | Each `Config.Paths.ToolOverrides` entry |
| `manifest.execution.env_vars[*]` | Per-app declared env vars         |

### 2.3 Planned (apps may read; hub will inject in a future version)

These names are reserved. Apps may read them now (default to a sensible
fallback) and hub will populate them later without breaking apps.

| Variable             | Purpose                                                   |
| -------------------- | --------------------------------------------------------- |
| `CTX_APP_DATA_DIR`   | Per-app userdata dir (`{CTX_ROOT}/userdata/{app_id}/`)    |
| `CTX_LOG_DIR`        | Per-app log dir (`{CTX_ROOT}/Logs/{app_id}/`)             |
| `CTX_CACHE_DIR`      | Per-app cache dir (`{CTX_ROOT}/cache/{app_id}/`)          |
| `CTX_HUB_VERSION`    | Hub version string                                        |
| `CTX_ENGINE_VERSION` | Engine (shared runtime) version string                    |
| `CTX_DEV_MODE`       | `"1"` if launched from source repo (no hub)               |
| `CTX_RUNTIME_ROOT`   | `{CTX_ROOT}/Runtimes` (the runtime dir parent of Shared)  |

### 2.4 Dev / capture / headless

These exist for development and the GUI-capture tooling. Hub does not set
them in production launches.

| Variable               | Source                       | Used by                                 |
| ---------------------- | ---------------------------- | --------------------------------------- |
| `CTX_CAPTURE_MODE`     | GUI capture launcher         | Apps suppress popups, optimize for screenshot |
| `CTX_HEADLESS`         | Capture / CI                 | Apps run minimal-UI flow                |
| `CTX_DEV_RUNTIME_ROOT` | Local dev runtime mirror     | `runtime_bootstrap` dev fallback        |
| `CTX_SHARED_RUNTIME_ROOT` | Force-inject shared runtime root | `runtime_bootstrap` override        |
| `CTX_STARTUP_TRACE`    | `1` to log startup timings    | App `main.py` prints `[startup] …` lines |
| `CTX_ALLOW_MULTIPLE_INSTANCES` | `1` to disable single-instance | `runtime_bootstrap` (legacy path) |
| `CTX_DISABLE_SINGLE_INSTANCE`  | Alias of above                 | `runtime_bootstrap` (legacy path) |

---

## 3. App responsibilities

An app shipped in this repo MUST:

1. **Have a `manifest.json` v1.2+** at the app folder root (see §4).
2. **Have a `manual.md`** (packaging fails without it).
3. **Have an `icon.png`** (preferred) or `icon.ico` at the folder root.
4. **Have the declared `execution.entry_point` file in the app folder**.
   Refactors may move implementation into `_engine` or `shared`, but the
   app-level entry point remains the hub-facing adapter.
5. **Read `CTX_APP_ROOT` for resource paths**, not the script's `__file__`
   parent (capture mode relies on this).
6. **Read `CTX_SHARED_ROOT` (or rely on `PYTHONPATH`)** to import
   `contexthub.*` packages. Do not probe filesystem for the shared runtime
   when these are set.
7. **Not write outside `CTX_APP_DATA_DIR`** (when set). Until hub provides
   it, apps may use `%LOCALAPPDATA%/Contexthub/{app_id}/` as a transitional
   fallback.
8. **Respect `CTX_CAPTURE_MODE` / `CTX_HEADLESS`** by suppressing modal
   popups and auto-confirm dialogs when these are set.
9. **Emit `[ctx] window_ready` to stdout** after `window.show()` returns,
   so hub can dismiss splash and mark the app `running`. (Planned hub
   support; line is harmless without it.)

An app SHOULD:

- Use `shared/_engine/runtime/splash.py` for a self-painted splash in dev /
  legacy launch (hub will eventually own this).
- Avoid single-instance logic in app code — `runtime_bootstrap` handles it
  today via a file lock; this will move to hub.
- Use `contexthub.utils.external_tools.get_ffmpeg()` etc., which already
  prefer the `*_PATH` env vars hub injects.

---

## 4. Manifest schema

Current `schema_version` shipped by all apps: **`"1.2"`**.

### 4.1 Required fields (v1.2 — unchanged)

```jsonc
{
  "schema_version": "1.2",
  "id": "image_resizer",
  "name": "Image Resizer",
  "description": "...",
  "version": "1.0.0",
  "runtime": {
    "category": "image",
    "python_version": "3.11",
    "required_binaries": []
  },
  "execution": {
    "entry_point": "main.py",
    "mode": "gui",                // "gui" | "console" | "background"
    "working_directory": "./",
    "single_instance": false,
    "env_vars": {}
  },
  "triggers": { "...": "..." },
  "ui": { "framework": "pyside6", "shared_theme": "contexthub" }
}
```

### 4.2 New v2 fields (forward-compatible; hub may ignore today)

These are being added across all apps as placeholders so hub can start
reading them without a flag day. Empty defaults are valid.

```jsonc
{
  "compatibility": {
    "engine_min": "1.0.0",      // min shared runtime version
    "engine_max": null,         // null = no upper bound
    "hub_min": "1.0.0",         // min hub version
    "os": ["windows"]           // supported OS list
  },
  "dependencies": {
    "external_binaries": [],    // e.g. ["ffmpeg", "git"]
    "python_packages": [],      // declared imports (informational)
    "models": []                // e.g. ["RealESRGAN-x4plus"]
  },
  "lifecycle": {
    "ready_signal": "stdout:[ctx] window_ready",
    "graceful_shutdown_timeout_ms": 3000
  },
  "permissions": {
    "filesystem": "user-files", // "user-files" | "app-data-only" | "any"
    "network": "none"           // "none" | "local" | "any"
  }
}
```

`schema_version` will bump to `"2.0"` once these are required, not just
present. For now they are optional — hub treats missing fields as
unconstrained.

---

## 5. Lifecycle signals (stdout convention)

Apps may emit single-line markers to stdout. Hub parses them; absence is
not an error.

| Line                            | Meaning                                            |
| ------------------------------- | -------------------------------------------------- |
| `[ctx] window_ready`            | First window has been shown; hub may dismiss splash. |
| `[ctx] progress {percent}`      | Progress for long-running batch (0–100).           |
| `[ctx] status {text}`           | Free-form status for hub UI.                       |
| `[ctx] error {message}`         | Recoverable error (logged, hub may surface).       |
| `[startup] {label} t+{ms}ms`    | Startup trace (only when `CTX_STARTUP_TRACE=1`).   |

---

## 6. Packaging contract

`package_apps.py` zips each leaf app folder. It does **not** include
`_engine/`, `shared/`, or `runtime_bootstrap.py`. Therefore:

- A zipped app cannot run standalone. Hub must provide the shared runtime
  and engine.
- Engine API stability matters: a change to `contexthub.ui.qt.shell` can
  break shipped apps if engine and apps drift apart. `compatibility.engine_min`
  is the planned guard.
- Per-app immutable release tags (`{app_id}-v{version}`) are planned in
  addition to the rolling `marketplace-assets` tag so rollback is possible.

---

## 7. Versioning

- **App version** (`manifest.version`): semver. Bump on any behavioral
  change. CI will eventually fail builds where source changed but version
  did not.
- **Engine version** (shared runtime): semver. Owned by hub repo. Apps
  declare `compatibility.engine_min`.
- **Hub version**: semver. Apps may declare `compatibility.hub_min`.
- **Schema version** (`manifest.schema_version`): bumped only when fields
  become required. Adding optional fields does not bump it.

---

## 8. Open questions / hub-side TODOs

Tracked so the hub team can pick these up.

- [ ] Inject `CTX_APP_DATA_DIR`, `CTX_LOG_DIR`, `CTX_CACHE_DIR`, `CTX_HUB_VERSION`, `CTX_ENGINE_VERSION`, `CTX_RUNTIME_ROOT`.
- [ ] Take over single-instance: detect existing app PID for the same `CTX_APP_ID`, focus its main window instead of spawning.
- [ ] Paint splash at click time; dismiss on `[ctx] window_ready`.
- [ ] Validate `manifest.compatibility` against current engine/hub before launch.
- [ ] Validate `manifest.dependencies.external_binaries` (warn + prompt to install).
- [ ] Parse `[ctx] progress/status/error` lines and surface in hub UI.
- [ ] Per-app immutable release tags in addition to `marketplace-assets`.
- [ ] Optional: pre-warmed Python interpreter pool with PySide6 + `contexthub` preloaded.
