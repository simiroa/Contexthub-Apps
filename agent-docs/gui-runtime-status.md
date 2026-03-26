# GUI Runtime Status

## Scope

This document tracks the current Qt GUI cleanup state in `Contexthub-Apps`.
It is a working inventory, not a final release checklist.

Use it together with:

- `agent-docs/gui-runtime-contract.md`
- `Diagnostics/gui_capture_log.md`
- `Diagnostics/gui_captures/`

## Template Buckets

`ui.template`가 manifest에 있으면 이를 우선 사용한다.
없을 때만 shared runtime과 캡처 결과로 추론한다.

### Full GUI

Apps that use the shared Qt shell plus dense panels, previews, and long-form parameter blocks.

Manifested apps:

- `doc_convert`
- `doc_scan`
- `pdf_merge`
- `image_compare`
- `image_convert`
- `merge_to_exr`
- `normal_flip_green`
- `resize_power_of_2`
- `rigreader_vectorizer`
- `simple_normal_roughness`
- `split_exr`
- `texture_packer_orm`
- `video_convert`

### Compact GUI

Apps that mainly confirm inputs, show a small status surface, and then hand off to console/back-end processing.

Manifested apps:

- `extract_audio`
- `extract_bgm`
- `extract_voice`
- `interpolate_30fps`
- `normalize_volume`
- `pdf_split`
- `qwen3_tts`
- `remove_audio`
- `youtube_downloader`

### Mini GUI

Small single-purpose windows or light controls.

Manifested apps:

- `ai_text_lab`

### Special GUI

Apps that are still Qt-based but should be treated as their own interaction class.

Manifested apps:

- `creative_studio_advanced`
- `creative_studio_z`
- `marigold_pbr`
- `versus_up`
- `whisper_subtitle`

### Out of Scope

These are not part of the generic Qt template pass.

- native apps such as `leave_manager_C`
- categories not included in the standard capture sweep, such as `audio` and `comfyui`, when they need their own review pass

## Low-Risk Cleanup Order

1. Keep the shared runtime compatibility layer stable.
2. Preserve `ConfirmDialog`, `HeaderSurface.manual_btn`, `PreviewListPanel.set_comparative_mode`, and the common palette/metrics fields until no caller depends on them.
3. Verify the low-risk full/compact apps first.
4. Move only the proven mini/special apps after the common template contract is stable.
5. Mirror any shared-runtime changes to `Contexthub\Runtimes\Shared`.

## Current Risks

- Some apps still call legacy shared-runtime names that need aliases.
- Some apps use `field_bg`, `surface_subtle`, or `preview_min_height` directly, so removing those names too early will break them.
- `special` apps should not be forced into a single generic template before their panel model is understood.
- `audio` is still a separate subtree for operational review, even though its manifest templates are now explicit.
- `ui.template` should be filled on the apps we consider structurally special so the bucket is declared in manifest, not inferred from file names.

## Working Rule

If an app can keep working with a narrow compatibility alias, prefer the alias first.
Only remove a shared name after the corresponding apps have been recaptured and verified.
