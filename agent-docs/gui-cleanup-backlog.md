# GUI Cleanup Backlog

## Scope

이 문서는 2026-03-29 기준 GUI 테스트 메모를 공통 작업과 앱별 작업으로 나눠 정리한 실행용 백로그다.
규칙 문서는 `agent-docs/gui-runtime-contract.md`, 현재 분류 상태는 `agent-docs/gui-runtime-status.md`, 캡처 근거는 `Diagnostics/gui_design_report_2026-03-14.md`와 `Diagnostics/gui_capture_log.md`를 따른다.

## Common Work

| Priority | Topic | Direction | Notes |
| --- | --- | --- | --- |
| P0 | Shared palette consolidation | shared runtime palette와 실제 stylesheet 색 출처를 일치시킨다. | 현재 `ShellPalette`와 `build_shell_stylesheet()` 사이에 하드코딩 값이 섞여 있다. |
| P0 | Theme contract enforcement | Qt 앱의 `ui.shared_theme`를 `contexthub`로 고정하고 raw color stylesheet를 줄인다. | manifest 계약과 runtime enforcement를 같이 가져가야 한다. |
| P0 | Header cleanup | 부제목, 상태 배지, 보조 버튼을 앱 목적 기준으로 압축한다. | 불필요한 설명과 모델 체크 버튼은 헤더에서 빼는 방향. |
| P0 | Action button rule | 앱별 액션 버튼은 단일 CTA 또는 좌우 2분할까지만 허용한다. | 저장 옵션은 실행과 분리하고, 하단 액션 바를 단순화한다. |
| P1 | Card depth reduction | 카드 한 겹을 걷어내고 내용에 집중한다. | 빈 프리뷰와 과한 외곽 카드가 앱을 미완성처럼 보이게 만든다. |
| P1 | Empty-state downsizing | 큰 빈 패널 대신 짧은 안내, 드롭존, 결과 예측으로 바꾼다. | `full` 앱 전반 공통 문제. |
| P1 | Export/output panel simplification | 출력 경로, 파일명, 후속 액션을 짧은 규칙으로 통일한다. | `ExportFoldoutPanel` 표준으로 정리하고 `ExportRunPanel`은 compat로 둔다. |
| P1 | Width/grid normalization | 긴 창 폭, 어색한 그리드, 버튼 위치 편차를 줄인다. | `video_convert`, `image_compare`, `texture_packer_orm` 우선. |
| P2 | Icon style unification | 앱 아이콘의 톤과 시각 문법을 통일한다. | 배포 완성도 체감에 영향이 크다. |
| P2 | Tooltip-first guidance | 장황한 설명문을 제거하고 툴팁 중심으로 옮긴다. | `Blur to Gray EXT` 계열부터 적용. |
| P2 | Error/dependency onboarding | 기술 오류를 그대로 노출하지 않고 복구 가능한 상태 화면으로 바꾼다. | 3D 의존성 앱과 초기화 실패 앱에 공통 적용. |

## App Backlog

| App | Bucket | Priority | Direction |
| --- | --- | --- | --- |
| `pdf_split` | mini | P1 | 범위 입력과 출력 규칙 예시를 보강한다. |
| `qwen3_tts` | special | P0 | 채팅형 UX를 유지하되 사실상 전면 재설계 대상으로 본다. |
| `remove_audio` | mini | Hold | 현 상태 유지 가능. |
| `resize_power_of_2` | full | Keep | 현재 표준 UI 후보로 유지하고 공통 기준 샘플로 삼는다. |
| `rigreader_vectorizer` | full | P0 | 입력 리스트 대신 채널 리스트 중심으로 재작성하고 병렬 배치 UX를 넣는다. |
| `simple_normal_roughness` | compact | P0 | 단일 input + 실시간 preview 중심의 compact 흐름으로 단순화한다. |
| `split_exr` | compact | P1 | `split_channel` 방향으로 정리하고 채널 이름 preset을 넣는다. |
| `texture_packer_orm` | special | P1 | 단순 full 대신 특수 상호작용형 도구로 보고 그리드 중심 UX를 재정리한다. |
| `versus_up` | special | P0 | 좌측 히스토리를 팝업 분리하고 상단 표, 하단 비교 자료 구조로 재편한다. |
| `video_convert` | full | P0 | 남은 부제목 제거, queue 액션 상단 이동, 폭 축소, 출력 UI 기준화. |
| `whisper_subtitle` | special | P1 | 실사용 검증 후 구조 재판단. 현재는 구색 위주라 재정의 필요. |
| `youtube_downloader` | special | P1 | 다운로더 특화 상호작용형 앱으로 보고 compact 대신 special 축에서 정리한다. |
| `ai_text_lab` | special | P1 | 실 기능과 연결을 다시 맞추고 실행 중 단축키 점유형 `clipup` 흐름을 검토한다. |
| `auto_lod` | compact | P1 | 버튼 정리, 실행 영역 정리, 텍스트 압축이 필요하다. |
| `blur_gray32_exr` | compact | P1 | 앱 이름 재검토, 프리뷰를 추가한 compact 흐름으로 재구성하고 장문 설명을 툴팁 중심으로 전환한다. |
| `cad_to_obj` | mini | Hold | 현재는 큰 구조 변경보다 유지 판단. |
| `comfyui_dashboard` | mini | Hold | 현 상태 유지 가능. |
| `creative_studio_advanced` | full | P2 | 헤더 정리. |
| `creative_studio_z` | full | P2 | 헤더 정리, `Recent Files` 의미 재정의. |
| `doc_convert` | compact | P1 | preview를 줄이고 1단 흐름으로 단순화한다. |
| `doc_scan` | full | P0 | page 추가와 OCR이 중요하고 액션 버튼 구조를 정리해야 한다. |
| `extract_audio` | mini | P0 | 출력 포맷과 간단 보정 옵션을 넣고 오디오 도구 허브 역할로 키운다. |
| `extract_bgm` | mini | P0 | `extract_audio` 옵션으로 흡수한다. |
| `extract_voice` | mini | P0 | `extract_audio` 옵션으로 흡수한다. |
| `extract_textures` | mini | P1 | 입력 파일 수 대신 탐지된 texture map 수를 보여주고 0개면 실행을 비활성화한다. |
| `image_compare` | full | P1 | 그리드 정렬 위주로 개선한다. |
| `image_convert` | mini | P0 | 너무 무거워서 축소가 필요하다. 포맷 변환 중심의 mini confirm/tool shell로 단순화한다. |
| `interpolate_30fps` | mini | Hold | 현 상태 유지 가능. |
| `marigold_pbr` | full | P1 | export 통일과 헤더 모델 체크 표현 정리가 필요하다. |
| `merge_to_exr` | full | P1 | 캡처 문제와 채널 매핑 구조 정리가 필요하다. |
| `mesh_convert` | mini | P1 | `image_convert`처럼 더 단순한 mini confirm/tool shell 흐름으로 재정리한다. |
| `normal_flip_green` | mini | Hold | 현 상태 유지 가능. |
| `normalize_volume` | mini | P1 | 독립 앱보다 오디오 도구군 편입 방향을 우선 검토한다. |
| `open_with_mayo` | mini | Hold | 현 상태 유지 가능. |
| `pdf_merge` | compact | P1 | 캡처 잘림 보정과 export UI 단순화가 필요하다. |

## Merge / Consolidation Candidates

| Priority | Direction | Apps |
| --- | --- | --- |
| P0 | 오디오 분리 앱 통합 | `extract_audio` + `extract_bgm` + `extract_voice` |
| P1 | 오디오 후처리 도구군 정리 | `normalize_volume` 포함한 통합 오디오 툴 검토 |
| P1 | EXR 채널 도구 명칭 정리 | `split_exr`를 `split_channel` 성격으로 재정의 |
| P1 | 변환 앱 슬림화 | `image_convert`, `mesh_convert`, `doc_convert`의 1단 흐름 재구성 |

## Why Colors Drift

현재 색상이 앱마다 틀어지는 직접 원인은 다음과 같다.

1. shared palette와 실제 stylesheet가 완전히 연결돼 있지 않다.
   `dev-tools/runtime/Shared/contexthub/ui/qt/shell.py`의 `ShellPalette`가 있어도 `build_shell_stylesheet()` 내부에 별도 하드코딩 색이 섞여 있었다.

2. 앱별 로컬 stylesheet override가 많다.
   예시는 아래와 같다.
   - `ai/_engine/features/ai/standalone/qwen3_tts_qt_app.py`
   - `ai/_engine/features/ai/whisper_subtitle_qt_app.py`
   - `ai_lite/_engine/features/tools/ai_text_lab_qt_app.py`
   - `video/_engine/features/video/video_convert_qt_app.py`
   - `ai_lite/_engine/features/versus_up/*`

3. `special` 앱은 shared shell 위에 별도 패널 색을 많이 덧씌운다.
   `versus_up`, `whisper_subtitle`, `marigold_pbr`가 대표적이다.

4. 카테고리별 `theme_contextup.json`은 동일하다.
   해시 기준으로 shared와 카테고리별 JSON이 모두 같으므로, 현재 PySide 색 편차의 주원인은 JSON 분기보다 Qt stylesheet 분산에 가깝다.

## Execution Order

1. shared runtime palette와 stylesheet를 먼저 정리한다.
2. `full` 앱 중 표준 샘플로 쓸 앱을 고른다.
   - 우선 후보: `resize_power_of_2`, `video_convert`
3. 긴 창과 빈 상태가 심한 앱을 줄인다.
   - `image_convert`, `doc_convert`, `pdf_merge`, `merge_to_exr`
4. 통합 대상 앱을 줄인다.
   - 오디오 분리 앱군
5. `special` 앱 재설계로 넘어간다.
   - `qwen3_tts`, `versus_up`, `whisper_subtitle`

## Current Common Work Started

- shared shell 기본 팔레트를 더 어둡고 일관된 방향으로 조정했다.
- shared stylesheet에서 카드, subtle panel, 버튼, chip, icon button이 중앙 palette를 우선 사용하도록 정리했다.
- `shared_theme`가 다르게 적혀 있던 `creative_studio_advanced`, `creative_studio_z`, `comfyui_dashboard`는 manifest를 `contexthub` 공용 계약으로 정리했다.
- 다음 공통 작업은 shared shell의 role/tone API 추가와 raw color drift 검사 자동화다.
- 다음 단계는 앱별 하드코딩 stylesheet를 줄여 실제로 shared palette를 받게 만드는 것이다.
