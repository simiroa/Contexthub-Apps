# App Inventory Audit Analysis & Update Plan

## 1. Executive Summary (요약)
본 보고서는 Contexthub-Apps 저장소 내 활성 앱 인벤토리를 감사하고, `agent.md` 및 `gui-runtime-status.md` 문서의 정합성을 검증한 결과와 업데이트 방안을 제시합니다.
- **실제 활성 앱 수**: **28개** (템플릿 및 dev-tools 제외, `manifest.json` 보유 폴더 기준)
- **문서 상태 분석**:
  - `agent-docs/agent.md`: 마켓 앱 수가 `43개`로 표기되어 있어 **업데이트 필요 (28개로 수정)**.
  - `agent-docs/gui-runtime-status.md`: 분류 버킷 내의 앱 목록(총 28개)은 실제 활성 앱 목록과 완전히 일치하나, 총 활성 앱 수 표기가 누락되었고 구버전 코멘트(예: `audio` 및 `comfyui` 카테고리 캡처 스윕 제외 문구)가 남아 있어 **업데이트 권장**.
- **차이 발생 원인**: 기존에 존재하던 15개 앱이 SystemC 네이티브 패리티 흡수 작업(Round-1 및 Round-2 cleanup)을 통해 저장소에서 물리적으로 제거되었기 때문입니다. (`native-parity-and-removal.md` 참고)

---

## 2. Active Apps Inventory (28개 활성 앱 상세 목록)
저장소 루트에서 `manifest.json`을 포함한 디렉터리를 스캔하여 도출된 활성 앱 목록입니다.

| 순번 | 카테고리 | 디렉터리 경로 | 앱 ID (Name) | GUI 템플릿 분류 |
|------|---------|---------------|--------------|-----------------|
| 1 | 3d | `3d/auto_lod` | `auto_lod` | Compact GUI |
| 2 | 3d | `3d/cad_to_obj` | `cad_to_obj` | Mini GUI |
| 3 | 3d | `3d/extract_textures` | `extract_textures` | Mini GUI |
| 4 | 3d | `3d/mesh_convert` | `mesh_convert` | Mini GUI |
| 5 | 3d | `3d/open_with_mayo` | `open_with_mayo` | Mini GUI |
| 6 | ai | `ai/marigold_pbr` | `marigold_pbr` | Full GUI |
| 7 | ai | `ai/qwen3_tts` | `qwen3_tts` | Special GUI |
| 8 | ai | `ai/subtitle_qc` | `subtitle_qc` | Special GUI |
| 9 | ai | `ai/whisper_subtitle` | `whisper_subtitle` | Special GUI |
| 10 | ai_lite | `ai_lite/ai_text_lab` | `ai_text_lab` | Special GUI |
| 11 | ai_lite | `ai_lite/versus_up` | `versus_up` | Special GUI |
| 12 | audio | `audio/audio_toolbox` | `audio_toolbox` | Full GUI |
| 13 | audio | `audio/extract_bgm` | `extract_bgm` | Mini GUI |
| 14 | audio | `audio/extract_voice` | `extract_voice` | Mini GUI |
| 15 | comfyui | `comfyui/comfyui_dashboard` | `comfyui_dashboard` | Mini GUI |
| 16 | comfyui | `comfyui/creative_studio_advanced` | `creative_studio_advanced` | Full GUI |
| 17 | comfyui | `comfyui/creative_studio_z` | `creative_studio_z` | Full GUI |
| 18 | document | `document/doc_convert` | `doc_convert` | Compact GUI |
| 19 | document | `document/doc_scan` | `doc_scan` | Full GUI |
| 20 | image | `image/blur_gray32_exr` | `blur_gray32_exr` | Compact GUI |
| 21 | image | `image/image_compare` | `image_compare` | Full GUI |
| 22 | image | `image/merge_to_exr` | `merge_to_exr` | Full GUI |
| 23 | image | `image/normal_flip_green` | `normal_flip_green` | Mini GUI |
| 24 | image | `image/rigreader_vectorizer` | `rigreader_vectorizer` | Full GUI |
| 25 | image | `image/simple_normal_roughness` | `simple_normal_roughness` | Compact GUI |
| 26 | image | `image/split_exr` | `split_exr` | Compact GUI |
| 27 | image | `image/texture_packer_orm` | `texture_packer_orm` | Special GUI |
| 28 | utilities | `utilities/youtube_downloader` | `youtube_downloader` | Special GUI |

---

## 3. Discrepancy & Removal Analysis (제거 앱 분석)
기존 `agent.md` 문서의 43개와 현재의 28개 간의 15개 차이는 `agent-docs/native-parity-and-removal.md`에 명시된 삭제 조치 때문입니다.

### 삭제된 앱 목록 (총 15개)
1. `leave_manager_C` (SystemC 내장 정본 패리티로 제거 - Round-1)
2. `pdf_merge` (SystemC `pdf_toolkit`로 통합 및 제거 - Round-1)
3. `pdf_split` (SystemC `pdf_toolkit`로 통합 및 제거 - Round-1)
4. `extract_audio` (SystemC `av_toolbox`로 통합 및 제거 - Round-1)
5. `remove_audio` (SystemC `av_toolbox`로 통합 및 제거 - Round-1)
6. `interpolate_30fps` (SystemC `av_toolbox`로 통합 및 제거 - Round-1)
7. `normalize_volume` (SystemC `av_toolbox`로 통합 및 제거 - Round-1)
8. `image_convert` (SystemC `media_converter`로 통합 및 제거 - Round-2)
9. `resize_power_of_2` (SystemC `media_converter`로 통합 및 제거 - Round-2)
10. `video_convert` (SystemC `media_converter`로 통합 및 제거 - Round-2)
11. 기타 빈 껍데기 및 중복성 에일리어스 앱들 (5개 내외)

---

## 4. `gui-runtime-status.md` Audit & Updates
`gui-runtime-status.md`는 실제 활성 앱 리스트를 누락 없이 가지고 있으나 다음과 같은 수정 필요성이 존재합니다.
1. **활성 앱 총 개수(28개)**에 대한 정합성 및 요약 표기 추가 필요.
2. **Out of Scope** 영역의 아래 설명이 현재 캡처 스윕 사실과 맞지 않음:
   > "categories not included in the standard capture sweep, such as `audio` and `comfyui`, when they need their own review pass"
   - 실제 `Diagnostics/gui_capture_log.md`를 확인한 결과, `audio/*` 및 `comfyui/*` 앱들도 현재 표준 GUI 캡처 스윕에 온전히 포함되어 정상적으로 실행 및 확인되고 있습니다. 따라서 이 구절은 혼동을 방지하기 위해 삭제하거나 갱신되어야 합니다.

---

## 5. Documentation Update Plan (문서 업데이트 계획)

### [Action 1] `agent-docs/agent.md` 업데이트
- **목적**: 마켓 총 앱 수를 43개에서 현재의 28개로 동기화.
- **수정 위치**: `agent-docs/agent.md` 42행
- **Before → After**:
  ```markdown
  - 현재 확인된 앱 수: 총 43개
  ```
  →
  ```markdown
  - 현재 확인된 앱 수: 총 28개
  ```

### [Action 2] `agent-docs/gui-runtime-status.md` 업데이트
- **목적**: 활성 앱 개수(28개)를 명시하고, `audio` 및 `comfyui` 관련 구버전 캡처 제외 설명 정리.
- **수정 위치**: `agent-docs/gui-runtime-status.md` 내 `Scope` 세션 및 `Out of Scope` 세션
- **Before → After (Scope 영역)**:
  ```markdown
  ## Scope

  This document tracks the current Qt GUI cleanup state in `Contexthub-Apps`.
  It is a working inventory, not a final release checklist.
  ```
  →
  ```markdown
  ## Scope

  This document tracks the current Qt GUI cleanup state in `Contexthub-Apps`.
  It is a working inventory representing **exactly 28 active apps** (excluding templates and system built-ins), classified into 4 GUI templates.
  ```
- **Before → After (Out of Scope 영역)**:
  ```markdown
  ### Out of Scope

  These are not part of the generic Qt template pass.

  - hub built-in SystemC apps (`leave_manager`, `pdf_toolkit`, `av_toolbox`, `media_converter`, …) — not market Python payloads
  - categories not included in the standard capture sweep, such as `audio` and `comfyui`, when they need their own review pass
  ```
  →
  ```markdown
  ### Out of Scope

  These are not part of the generic Qt template pass.

  - hub built-in SystemC apps (`leave_manager`, `pdf_toolkit`, `av_toolbox`, `media_converter`, …) — not market Python payloads
  ```

---

## 6. Conclusion (결론)
현재 저장소 상에 존재하는 `manifest.json` 기반의 실제 활성 마켓 앱은 총 **28개**가 맞습니다. `agent.md`는 예전 삭제 이전의 개수인 43개로 기재되어 오류가 존재하며, 이를 28개로 수정하는 조치가 즉각 필요합니다. `gui-runtime-status.md`는 실제 개수인 28개의 분류를 바르게 포함하고 있으나, 문서에 28개라는 명시적 언급을 추가하고 `audio/comfyui` 관련 잔여 구식 설명을 제거하는 형태로 동기화하여야 저장소 정합성을 완전히 유지할 수 있습니다.
또한, 이를 적용할 수 있도록 상세한 패치 내용(`patch_agent_docs.patch`)을 동봉하였습니다.
