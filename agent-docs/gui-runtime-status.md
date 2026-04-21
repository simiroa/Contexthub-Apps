# GUI Runtime Status

## Scope

This document tracks the current Qt GUI cleanup state in `Contexthub-Apps`.
It is a working inventory, not a final release checklist.

Use it together with:

- `qt-app-builder-contexthub` 스킬 문서
- `agent-docs/gui-cleanup-backlog.md`
- `Diagnostics/gui_capture_log.md`
- `Diagnostics/gui_captures/`

## Template Buckets

`ui.template`가 manifest에 있으면 이를 우선 사용한다.
없을 때만 shared runtime과 캡처 결과로 추론한다.

### Full GUI

Apps that use the shared Qt shell plus dense panels, previews, and long-form parameter blocks.

Manifested apps:

- `audio_toolbox`
- `doc_scan`
- `merge_to_exr`
- `image_resizer`
- `rigreader_vectorizer`
- `video_convert`
- `image_compare`
- `creative_studio_advanced`
- `creative_studio_z`
- `marigold_pbr`

### Compact GUI

Apps with no multi-input list, only one main preview-or-list surface, and a small set of immediately understandable options.

Manifested apps:

- `blur_gray32_exr`
- `doc_convert`
- `pdf_merge`
- `simple_normal_roughness`
- `split_exr`
- `auto_lod`

### Mini GUI

Small confirm-shell windows with very few options and selection-summary style input.

Manifested apps:

- `cad_to_obj`
- `comfyui_dashboard`
- `extract_audio`
- `extract_bgm`
- `extract_textures`
- `extract_voice`
- `image_convert`
- `interpolate_30fps`
- `mesh_convert`
- `normalize_volume`
- `normal_flip_green`
- `open_with_mayo`
- `pdf_split`
- `remove_audio`

### Special GUI

Apps that are still Qt-based but should be treated as their own interaction class.

Manifested apps:

- `ai_text_lab`
- `qwen3_tts`
- `subtitle_qc`
- `texture_packer_orm`
- `youtube_downloader`
- `versus_up`
- `whisper_subtitle`

### Out of Scope

These are not part of the generic Qt template pass.

- native apps such as `leave_manager_C`
- categories not included in the standard capture sweep, such as `audio` and `comfyui`, when they need their own review pass

## Low-Risk Cleanup Order

1. Keep the shared runtime compatibility layer stable.
2. Preserve `ConfirmDialog`, `HeaderSurface.manual_btn`, `PreviewListPanel.set_comparative_mode`, `AssetWorkspacePanel`, `ExportFoldoutPanel`, and the common palette/metrics fields until no caller depends on them.
3. Verify the low-risk full/compact apps first.
4. Move only the proven mini/special apps after the common template contract is stable.
5. Mirror any shared-runtime changes to `Contexthub\Runtimes\Shared`.

## Current Risks

- Some apps still call legacy shared-runtime names that need aliases.
- Some apps use `field_bg`, `surface_subtle`, or `preview_min_height` directly, so removing those names too early will break them.
- `special` apps should not be forced into a single generic template before their panel model is understood.
- `audio` is still a separate subtree for operational review, even though its manifest templates are now explicit.
- `ui.template` should be filled on the apps we consider structurally special so the bucket is declared in manifest, not inferred from file names.
- `audio/normalize_volume` currently fails because `AudioMiniWindow.__init__()` still expects a `subtitle` argument.
- `image/image_compare` currently fails because `mode_combo` is referenced before it is created.

## Theme Drift

현재 색상 편차는 shared theme 파일이 여러 개라서라기보다, Qt runtime에서 색 출처가 분산돼 있기 때문에 생긴다.

- category별 `theme_contextup.json`은 현재 동일하다.
- Qt 앱의 `ui.shared_theme`는 현재 모두 `contexthub` 공용 계약으로 맞추는 것이 기준이다.
- 과거 `creative_studio_*`, `comfyui_dashboard`처럼 다른 `shared_theme` 이름을 쓰던 앱도 실제 구현은 `contexthub.ui.qt.shell`을 사용하고 있었다.
- 하지만 shared shell의 `ShellPalette`와 실제 `build_shell_stylesheet()` 사이에 하드코딩 색이 섞여 있었다.
- `qwen3_tts`, `whisper_subtitle`, `ai_text_lab`, `video_convert`, `versus_up` 같은 앱은 app-local `setStyleSheet()`가 많아 shared 색을 다시 덮는다.

따라서 색상 정리는 JSON 병합보다 먼저, shared runtime stylesheet 정리와 app-local override 축소 순으로 가는 편이 안전하다.

## Current Decision

현재 유지보수 기준은 다음처럼 고정한다.

- Qt 앱의 공용 테마 계약은 `contexthub` 하나로 고정한다.
- 앱은 컴포넌트 구조를 다르게 가져갈 수 있지만, raw color stylesheet를 새로 늘리지 않는다.
- 다음 정리 패스는 개별 앱 색 수정이 아니라 shared shell role/tone API 도입 후, 상위 offender 앱을 그 API로 옮기는 방식으로 진행한다.
- shared runtime은 작은 모듈로 분해한 상태를 유지하되, 기존 앱이 의존하는 compatibility alias는 캡처 재검증 전까지 유지한다.

## Validation

공통 계약 검사는 아래 스크립트를 기준으로 한다.

- `python dev-tools/check-gui-theme-contract.py`

2026-03-29 기준 초기 베이스라인은 다음과 같다.

- manifest 계약 오류: 0
- raw color drift 경고: 73

이 경고 수는 이후 앱 정리 패스에서 줄여 나가는 추적 지표로 본다.

## Working Rule

If an app can keep working with a narrow compatibility alias, prefer the alias first.
Only remove a shared name after the corresponding apps have been recaptured and verified.

## Surface Gap Audit

카드 사이에 다른 색이 비치는 문제는 아래 순서로 확인한다.

1. 캡처에서 줄이 보이는 위치가 `card`와 `card` 사이인지, `card` 내부 preview/inset인지 먼저 구분한다.
2. 해당 앱에서 `QScrollArea`, `setWidget(...)`, `viewport()`, `setContentsMargins(...)`, `setSpacing(...)`를 찾는다.
3. 스크롤 body나 viewport가 비는 구조면 `surfaceRole="content"` 적용 여부를 본다.
4. 큰 면적 preview/inset이 `field_bg`를 직접 쓰면 `subtle` 또는 별도 preview role로 바꾼다.
5. spacing을 임시로 `0`으로 줄였을 때 줄이 사라지면 background role 누락 문제로 본다.
6. spacing이 `0`이어도 색 차가 남으면 `card_bg`, `content_bg`, `surface_subtle`, `field_bg` 토큰 대비 문제로 본다.

현재 `content` role 우선 적용 대상 패턴은 다음과 같다.

- `QScrollArea` + `setWidget(scroll_body)`
- `QScrollArea.viewport()`가 빈 영역을 노출하는 리스트/갤러리
- 카드 안쪽에 body container를 두고 section spacing으로 여백을 만드는 compact/special 앱
