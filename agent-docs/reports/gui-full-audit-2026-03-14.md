# GUI Full Audit - 2026-03-14

## Scope
- Basis: latest desktop GUI capture set under `Diagnostics/gui_captures/`
- Method: first-screen review from a UX designer perspective plus targeted code review of current Flet shells and app entrypoints
- Included: 29 Python GUI apps that currently produce a desktop window in capture runs
- Excluded: native or non-Python launchers such as `leave_manager_C`, and non-GUI context tools such as `extract_textures`, `normalize_volume`, `create_proxy`, `extract_audio`, `interpolate_30fps`, `remove_audio`

## Scoring rubric
- `9-10`: production-ready first impression, clear task flow, low UX risk
- `7-8`: usable and coherent, but needs fit-and-finish or stronger guidance
- `5-6`: works, but important friction or visual debt remains
- `0-4`: unstable, misleading, or high risk for user error

## Executive summary
- Strongest current app: `ai/qwen3_tts`
- Strongest category overall: `image`
- Largest remaining cross-app issue: action density at the bottom of form-heavy tools, leading to vertical crowding and weak task hierarchy
- Largest code issue: many apps still own their own local state and validation logic instead of sharing more of the new Flet shell primitives
- Highest-value next step: unify `empty state`, `status area`, `output location`, and `primary action` patterns across `audio`, `document`, and `3d`

## Category scores
| Category | Apps | Avg UX |
| --- | ---: | ---: |
| `image` | 9 | 7.7 |
| `ai` | 5 | 7.4 |
| `document` | 4 | 7.1 |
| `audio` | 3 | 6.9 |
| `3d` | 4 | 6.5 |
| `ai_lite` | 2 | 6.6 |
| `video` | 1 | 6.8 |
| `utilities` | 1 | 7.0 |

## 3D
### `auto_lod` - UX 6.8/10
- Function detail: mesh input selection, LOD generation settings, dependency-aware execution shell
- UX review: structure is readable now, but the app still feels like a technical form rather than a guided asset pipeline
- Code improvement: move dependency probing and environment summaries into a shared diagnostics card helper instead of assembling it in the view
- Feature improvement proposal: add a `preset by target engine` option for Unreal, Unity, and generic glTF output

### `blender_bake_gui` - UX 6.4/10
- Function detail: remesh, bake, and output configuration for texture baking workflows
- UX review: improved from the old error shell, but advanced options visually compete with the primary run action
- Code improvement: split bake configuration state from view code so form defaults and validation are testable
- Feature improvement proposal: add quick presets for `PBR game asset`, `preview bake`, and `high-quality archive`

### `cad_to_obj` - UX 6.3/10
- Function detail: CAD conversion workflow with dependency messaging and conversion settings
- UX review: usable, but the first screen explains the process weakly and does not reduce uncertainty around unsupported inputs
- Code improvement: centralize file validation and extension capability hints in the shared service layer
- Feature improvement proposal: show expected output scale/orientation choices before conversion

### `mesh_convert` - UX 6.6/10
- Function detail: generic mesh conversion shell with file input, target format, and export state
- UX review: more stable than before, but still visually sparse and slightly too generic for the number of format edge cases it hides
- Code improvement: share format capability matrices with `cad_to_obj` and `auto_lod` to avoid duplicated logic
- Feature improvement proposal: add `preview detected mesh stats` before conversion starts

## AI
### `demucs_stems` - UX 7.1/10
- Function detail: audio file queue, stem separation settings, log view, output action
- UX review: clear and serviceable; the new shell makes the workflow understandable on first launch
- Code improvement: move subprocess lifecycle and cancellation messaging into the shared AI runner widgets
- Feature improvement proposal: add preset targets like `vocals only`, `karaoke`, and `full stems`

### `esrgan_upscale` - UX 7.0/10
- Function detail: image queue, scale/model settings, output location, status/logging
- UX review: much better than the broken scroll state, but the preview/value proposition is still weak for an image enhancement tool
- Code improvement: extract file-list and output-summary cards into reusable image/AI shell components
- Feature improvement proposal: add before/after preview tiles and estimated output size

### `qwen3_tts` - UX 8.7/10
- Function detail: conversation bubble authoring, profile/tone controls, generation queue, output folder actions
- UX review: strongest app in the set; the chat metaphor and profile flow map well to the model capability
- Code improvement: reduce remaining view-state coupling between bubble editing, profile editing, and generation progress overlays
- Feature improvement proposal: add saved scene templates and reusable voice clone prompt packs

### `rmbg_background` - UX 7.0/10
- Function detail: image selection, background removal settings, output path, logs
- UX review: coherent after the Flet rewrite, but still feels like a form around a black-box process
- Code improvement: share image task cards and output naming helpers with `esrgan_upscale`
- Feature improvement proposal: add transparent preview checkerboard and edge refinement presets

### `whisper_subtitle` - UX 7.3/10
- Function detail: media selection, transcription settings, output formats, logs
- UX review: task flow is clear and sensible; information density is decent without being overwhelming
- Code improvement: extract job progress serialization and output summary logic out of the page function
- Feature improvement proposal: add subtitle style presets and speaker-split option when supported

## AI Lite
### `ai_text_lab` - UX 6.5/10
- Function detail: text generation lab shell with provider-aware fallback and prompt/result areas
- UX review: stable enough now, but still reads like a developer console rather than a writer-facing tool
- Code improvement: isolate provider capability detection and unavailable-feature messaging into a dedicated service adapter
- Feature improvement proposal: add reusable prompt blocks for translate, summarize, rewrite, and compare

### `versus_up` - UX 6.7/10
- Function detail: side-by-side comparison workflow and decision support shell
- UX review: understandable, but the large neutral blocks still under-communicate what the user gets after running the tool
- Code improvement: reduce view-specific placeholder logic and formalize the comparison state model
- Feature improvement proposal: add scoring rationale chips and exportable decision summary

## Audio
### `audio_convert` - UX 6.9/10
- Function detail: audio file queue, target format and codec configuration, run action, logs
- UX review: stable and readable, but still vertically heavy for a converter that should feel quick
- Code improvement: move format/codec rules into a service model and keep the UI layer declarative
- Feature improvement proposal: add a compact mode with `files + target format + convert` only

### `extract_bgm` - UX 6.9/10
- Function detail: music/background stem extraction with settings and output shell
- UX review: no longer broken, but the distinction from `extract_voice` is too subtle in the first screen
- Code improvement: parameterize the shared separation shell more strongly so labels and descriptions stay consistent
- Feature improvement proposal: show a one-line `keeps music / suppresses speech` promise in the summary card

### `extract_voice` - UX 6.9/10
- Function detail: dialogue/voice extraction with settings and output shell
- UX review: functionally clear, but the shell still needs a stronger identity difference from `extract_bgm`
- Code improvement: same shared-shell cleanup as `extract_bgm`, plus stronger naming for target outputs
- Feature improvement proposal: add `podcast cleanup` and `dialogue isolate` presets

## Document
### `doc_convert` - UX 7.0/10
- Function detail: document format conversion with file queue, target format, and output action
- UX review: clear enough, but the app still lacks strong feedback around unsupported combinations
- Code improvement: centralize format compatibility and warning text in a single service map
- Feature improvement proposal: show `source -> target` compatibility badges per file

### `doc_scan` - UX 7.2/10
- Function detail: page list, page preview, rotate, simple document filters, PNG/PDF export
- UX review: good recovery result; for the current scope it now behaves like a practical lightweight scanner
- Code improvement: keep compatibility wrappers for old Flet APIs isolated so the main page code stays clean
- Feature improvement proposal: add page reorder and crop/edge detection when performance budget allows

### `pdf_merge` - UX 7.1/10
- Function detail: PDF file ordering and merge output flow
- UX review: straightforward and low-friction; one of the easier apps to understand immediately
- Code improvement: share list reorder and output target widgets with `pdf_split`
- Feature improvement proposal: add `open merged file` and `open folder` post-run actions in the status bar

### `pdf_split` - UX 7.0/10
- Function detail: page range splitting, output settings, and result export
- UX review: usable, but it asks for ranges without enough visual help for non-technical users
- Code improvement: parse and validate page ranges in a dedicated utility with surfaced friendly errors
- Feature improvement proposal: add quick buttons for `every page`, `custom ranges`, and `extract first/last N`

## Image
### `image_compare` - UX 7.4/10
- Function detail: two-image comparison shell with compare mode controls and preview area
- UX review: much more coherent than before, but it still depends heavily on the preview actually loading to justify the layout
- Code improvement: isolate image preview loading failures into a typed state rather than status text mutations
- Feature improvement proposal: add difference heatmap and swipe compare mode

### `image_convert` - UX 7.3/10
- Function detail: batch image conversion with target format and output settings
- UX review: simple and usable, though the form still takes more space than the task complexity warrants
- Code improvement: reuse file and output sections with `audio_convert` and `video_convert` shell patterns
- Feature improvement proposal: add destination naming preview and quick format presets

### `merge_to_exr` - UX 7.6/10
- Function detail: multi-layer/image channel assembly into EXR outputs
- UX review: strong technical clarity; one of the better pro-tool layouts among the image apps
- Code improvement: move layer-row editing into a reusable component and reduce inline control construction
- Feature improvement proposal: add preset channel recipes for common DCC/export conventions

### `normal_flip_green` - UX 7.5/10
- Function detail: batch green-channel inversion for normal maps
- UX review: appropriately simple; the task is narrow and the UI mostly respects that
- Code improvement: shrink view-specific boilerplate and reuse the compact action shell more aggressively
- Feature improvement proposal: add a quick before/after preview and explicit DirectX/OpenGL wording

### `resize_power_of_2` - UX 7.7/10
- Function detail: resize-to-power-of-two workflow with recommendation and method selection
- UX review: one of the clearer utility flows in the repo; recommendation messaging adds real value
- Code improvement: move recommendation logic into service code and keep the view free from calculation branches
- Feature improvement proposal: add texture-target presets for `mobile`, `desktop`, and `cinematic`

### `rigreader_vectorizer` - UX 8.0/10
- Function detail: vectorization pipeline with source list, settings, and output management
- UX review: strongest image-category professional tool; two-panel structure feels intentional
- Code improvement: continue reducing legacy layout assumptions and finish the remaining localization cleanup
- Feature improvement proposal: add result preview tabs for raster, vector, and export summary

### `simple_normal_roughness` - UX 7.5/10
- Function detail: source image to normal/roughness generation shell with preview modes and controls
- UX review: now understandable, though it still needs a stronger relationship between controls and preview output
- Code improvement: split preview state from generation parameter state for easier testing and fewer redraw hacks
- Feature improvement proposal: add live mini-preview thumbnails beside each output mode

### `split_exr` - UX 7.6/10
- Function detail: EXR channel extraction with per-channel mapping and output path flow
- UX review: clear enough for technical users and improved from the earlier clutter
- Code improvement: extract the channel table and naming rules into a dedicated model/view helper
- Feature improvement proposal: add export templates for RGBA, ORM, and custom pass bundles

### `texture_packer_orm` - UX 7.9/10
- Function detail: channel packing for ORM-style texture assembly
- UX review: very solid mental model; slot-based UI suits the task well
- Code improvement: replace remaining icon-only interactions with shared labeled action widgets
- Feature improvement proposal: add preset packs for Unreal, Unity HDRP, and custom map conventions

## Utilities
### `youtube_downloader` - UX 7.0/10
- Function detail: URL input, download mode selection, output path, and run state
- UX review: no longer crashes and the workflow is readable, but trust cues and legality/quality messaging are still light
- Code improvement: separate provider/download capability probing from the page layer and normalize error mapping
- Feature improvement proposal: add quality selector, thumbnail preview, and explicit audio-only mode badges

## Video
### `video_convert` - UX 6.8/10
- Function detail: video format conversion shell with codec/output options and action area
- UX review: recovered from the earlier broken state, but still visually denser than it should be for a converter
- Code improvement: unify codec/output rules with the service layer and simplify the page layout to fewer nested containers
- Feature improvement proposal: add common destination presets such as `editing proxy`, `web mp4`, and `alpha export`

## Cross-app code improvement priorities
1. Expand the shared Flet shell layer so apps stop re-creating summary cards, file lists, output path rows, and status bars.
2. Move validation, compatibility checks, and preset logic out of page functions and into small service/state modules.
3. Add a lightweight compatibility helper for the older bundled Flet runtime to avoid repeated API-specific fixes.
4. Standardize output naming preview and post-run actions across converter-style tools.

## Cross-app product improvement priorities
1. Add clearer empty states that explain the expected input and resulting artifact.
2. Expose output location and resulting filename earlier, before users hit run.
3. Make `preset-first` workflows standard for AI, audio separation, and conversion tools.
4. Introduce one compact window profile for simple one-shot tools so they do not feel oversized.

## Verification notes
- Latest capture result source: `Diagnostics/gui_capture_log.md`
- `document/doc_scan` needed extra runtime compatibility fixes because the bundled Flet version differs from newer API examples
- A capture marked `OK` means `window appeared`; UX evaluation in this report is based on visually inspecting the current capture images, not only the log status
