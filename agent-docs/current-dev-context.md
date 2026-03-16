# Current Dev Context

## 목적

다음 기능 개발 전에 다시 긴 배경 설명을 반복하지 않도록, 현재 저장소 상태와 바로 이어서 작업할 기준점을 요약한다.

Flet 작업은 이 문서만 단독으로 읽지 말고, 먼저 `agent-docs/flet-migration-guidelines.md`를 읽은 뒤 이 문서를 본다.

반복되는 Flet 포팅 실수를 줄이려면 `agent-docs/templates/flet-porting-template.md`도 같이 본다.

## 현재 상태 요약

- Python GUI 공통 규격 정리가 진행된 상태다.
- Qt 공용 규격은 `dev-tools/runtime/Shared/contexthub/ui/qt/` 기준으로 승격되었다.
- Qt 공용 규칙은 이제 `comfyui`뿐 아니라 `video/video_convert`까지 실제 적용 사례가 생겼다.
- shared Qt manual dialog는 markdown viewer 기준으로 재디자인되었고, 표/목록/코드블록/링크 스타일을 포함한다.
- `creative_studio_advanced`, `creative_studio_z`는 최근 compact form 규칙에 맞게 `QGroupBox title` 기반 파라미터 카드에서 내부 eyebrow 라벨 구조로 정리되었다.
- shared `ExportRunPanel`은 최근 `collapsed action bar / expanded detail panel` 규격으로 정리되었다.
- `prompt_master`, `rigreader_vectorizer`, `doc_scan`는 최근 세션에서 직접 수정되었다.
- `ai` 카테고리 일부는 모델 카드 잘림과 하단 액션 버튼 미노출 문제를 수정했다.
- `ai/qwen3_tts` 초안 앱이 추가되었고, 실제 RTX 생성 검증까지 끝난 상태다.
- 공유 런타임 변경분은 로컬 미러뿐 아니라 원본 `C:\Users\HG\Documents\Contexthub\Runtimes\Shared`에도 반영했다.

## 이미 반영된 핵심 규칙

### 1. GUI 규격

- Python GUI는 가능하면 `BaseWindow`를 사용한다.
- Qt 공용 shell/panel은 `dev-tools/runtime/Shared/contexthub/ui/qt/`를 우선 사용한다.
- Qt 범용 규칙은 `agent-docs/qt-shared-runtime-guidelines.md`를 함께 본다.
- locale 로딩은 `CTX_APP_ROOT` 기준 체인을 따른다.
- 푸터 액션 버튼과 진행 바는 가능하면 `footer_frame`에 둔다.
- 공통 버튼/카드 색상은 `gui_lib.py` 상수를 우선한다.

### 2. AI 실행 환경

- `ai` 카테고리는 Conda 우선 실행 규칙을 가진다.
- 기본 모드: `AI_ENV_MODE=prefer_conda`
- 기본 env 이름: `AI_CONDA_ENV_NAME=contexthub-ai`
- 직접 지정 가능: `AI_CONDA_EXE`, `AI_CONDA_ENV_PATH`
- Conda 또는 env가 없으면 경고 후 기존 Python으로 fallback 한다.

### 3. 로컬 테스트

- 공유 런타임 테스트 기준 경로: `dev-tools/runtime/Shared`
- Qt shared shell/panel 기준 경로: `dev-tools/runtime/Shared/contexthub/ui/qt/`
- GUI 실행 도구: `dev-tools/run-app-local.ps1`
- GUI 캡처 도구: `dev-tools/capture-python-gui-apps.ps1`
- Qt 캡처는 앱별 fixture target과 상세 stderr/stdout tail 로그를 남기도록 보강되었다.
- Qt 캡처는 category env의 `PySide6` import 실패 시 fallback python까지 시도하고, dependency dialog와 실제 앱 창을 구분해 기록한다.
- 진단 산출물: `Diagnostics/gui_captures`, `Diagnostics/gui_capture_log.md`

## 최근에 해결된 대표 이슈

- `prompt_master`: 구형 창 구조, i18n 누락, 서브 UI 하드코딩 문자열 정리
- `rigreader_vectorizer`: 번역 키 누출, 창 폭 부족, 출력 폴더 행 정리
- `doc_scan`: `ctk.CTk` 직접 상속에서 `BaseWindow` 기반으로 전환
- `marigold_pbr`: 모델 카드 잘림 완화
- `esrgan_upscale`, `rmbg_background`, `whisper_subtitle`: 하단 버튼/진행 바 첫 화면 노출
- `image` Flet 포팅 회귀 정리:
  - `image_compare`, `image_convert`, `resize_power_of_2`, `split_exr` 부팅 회복
  - `simple_normal_roughness`, `texture_packer_orm`, `merge_to_exr`, `normal_flip_green`, `rigreader_vectorizer` 호환 수정
  - 공통 원인: Flet 0.82 API 계약 불일치(`on_select`, `FilePicker`, `Image(src=bytes)`, `ElevatedButton` content 등)
  - 최근 공통화: `window_profile` 기반 창 크기, `action_bar()` 기반 하단 실행 영역, 버튼 최소폭 규칙 추가
  - 현재 상태: 다수 앱은 부팅 + 기본 기능 스모크 완료, 일부는 환경 의존성(`cv2`, `vtracer`) 프리체크 안내 추가

## 새 AI 앱 상태

- `qwen3_tts`
  - 위치: `ai/qwen3_tts`, `ai/_engine/features/ai/standalone/qwen3_tts*.py`
  - 상태: 패키징 통과, GUI 캡처 통과, RTX 실생성 통과
  - 최근 구조: `qwen3_tts_service.py`, `qwen3_tts_state.py`, `qwen3_tts_flet_app.py` 로 Flet 기준 계층 분리
  - 현재 진입 정책: `main.py`는 legacy GUI fallback 없이 Flet 전용 진입
  - 최근 공유화: `dev-tools/runtime/Shared/contexthub/ui/flet/` 아래에 Flet 공용 `tokens.py`, `theme.py`, `window.py`, `dialogs.py`, `layout.py` 추가
  - 최근 문서 보강: `agent-docs/templates/flet-porting-template.md` 추가
  - 최근 공통화: `wide_canvas` 창 프로필, `action_bar()` 기반 하단 액션 구조, shared runtime 경로 주입
  - 입력 방식: quick launcher + 텍스트/오디오 컨텍스트 메뉴 프리필
  - 추론 방식: `qwen-tts` 직접 호출, `Preset Voice`(`custom_voice`) / `Clone from Audio`(`voice_clone`) / `Design New Voice`(`voice_design`) 및 배치 jobs 지원
  - 검증 결과: `contexthub-ai` Python 3.12 Conda env에서 `qwen-tts` 설치 후 RTX 3080 Ti 기준 실제 WAV 생성 성공
  - 생성 샘플: `Diagnostics/generated/qwen3_tts_test.wav`
  - 주의: 현재 검증된 경로는 CPU가 아니라 CUDA 경로다
  - 기본 모델 정책: `0.6B`는 노출하지 않고 `1.7B`를 기본/고정 모델로 사용
  - 현재 UI 방향: 상단 모델 상태 바, 중앙 채팅 버블, 하단 입력 바, 생성 오버레이 중심 UX
  - 최근 UI 문구 정리: 개발자 설명 문구 제거, `Preset Voice / Clone from Audio / Design New Voice` 라벨로 사용자 노출 통일
  - 최근 UX 보강: 둥근 대화 버블, 좌측 컬러 프로필 마커, 기본 설정/고급 설정 분리, 선택된 버블의 `Detail Tray`, `Edit Text` 인라인 편집, `More` 기반 보조 액션 정리, 생성 결과의 waveform `Result Card`, 우측 프로필 패널의 모드별 필드 분기, clone 참조 상태 진단, clone 결과의 참조 정보 표시, 가벼운 playhead 기반 재생 표시
  - 프로필 저장: `ai/_engine/resources/ai_models/qwen3_tts/profiles.json`
  - 현재 제약: 톤 프리셋은 `Clone from Audio`에 직접 적용되지 않고, 진행률은 작업 완료 단위 기준
  - 스트레스 테스트: `Preset Voice`, `Clone from Audio`, `Design New Voice`, 혼합 배치 생성까지 RTX 기준 통과
  - 최근 런타임 보강: batch JSON은 `utf-8-sig`로 읽어 BOM 허용, clone 입력 오류는 모델 로드 전에 즉시 검증
  - 출력 정책: 같은 파일명이 있으면 `_2`, `_3` 접미사로 새 파일을 만들어 기존 산출물을 보존
  - 런타임 의존성: `flet 0.82.2`가 `C:\Users\HG\Documents\HG_context_v2\ContextUp\tools\python\python.exe` 와 `C:\Users\HG\miniconda3\envs\contexthub-ai\python.exe` 에 설치됨

## 다음 기능 개발 전에 확인할 것

1. 대상 앱이 래퍼형 `main.py`인지, `_engine` 직접 구현인지 확인
2. 같은 카테고리 `_engine/features`와 `_engine/utils`를 같이 읽기
3. GUI가 있다면 기존 `BaseWindow` 패턴을 유지할지 먼저 판단
4. `ai` 기능이면 Conda env 기준 패키지/모델 전략부터 정하기
5. 수정 후 `capture-python-gui-apps.ps1` 또는 최소 수동 실행으로 회귀 확인
6. 공유 런타임을 바꿨다면 원본 허브 경로 반영 여부까지 확인

## AI 런타임 검증 메모

- 권장 기본 env는 `contexthub-ai`다
- 현재 검증된 `contexthub-ai` 구성
  - Python 3.12
  - `torch 2.10.0+cu126`
  - `torchaudio 2.10.0+cu126`
  - `torch.cuda.is_available() == True`
  - GPU: `NVIDIA GeForce RTX 3080 Ti`
- `qwen3_tts`는 이 env에서 RTX 실생성이 확인되었다
- 추가 스트레스 테스트 리포트: `Diagnostics/qwen3-tts-stress-report-2026-03-13.md`

## AI 포팅 메모

- `qwen3_tts`부터 shared Flet 규격 적용을 시작했다.
- `esrgan_upscale`, `rmbg_background`, `whisper_subtitle`, `demucs_stems`의 wrapper `main.py`도 shared runtime 경로를 주입하도록 맞췄다.
- 아직 `esrgan_upscale`, `rmbg_background`, `whisper_subtitle`, `demucs_stems` 본체 UI는 `customtkinter` 기반이다.
- 최근 1차 UX 조정:
  - `demucs_stems`: 초기 창 확대, 상태 라벨 추가, 하단 액션 가시성 회복
  - `esrgan_upscale`: 파일 리스트 높이 축소, 안내 문구 추가, 하단 액션 여백 정리
  - `rmbg_background`: 초기 창 확대, 파일 리스트 높이 축소, 출력 안내 추가
  - `whisper_subtitle`: 초기 창 확대, 파일/로그 영역 높이 축소로 첫 화면 정보 밀도 개선
- 다음 우선순위는 `esrgan_upscale` -> `rmbg_background` -> `whisper_subtitle` 순이 적절하다.

## 바로 참고할 문서

- 구조/코드 위치: `agent-docs/architecture.md`
- 새 앱 개발: `agent-docs/new-app-guidelines.md`
- GUI 문제 유형: `agent-docs/gui-issue-playbook.md`
- 최신 GUI 수정 기록: `Diagnostics/gui-issues-2026-03-13.md`
- 최신 GUI 캡처 기준: `Diagnostics/gui-capture-report-2026-03-13.md`
- 이미지 기능 스모크: `Diagnostics/image_feature_smoke.py`
- 이미지 스모크 결과: `Diagnostics/generated/image_feature_smoke/smoke_report.json`
