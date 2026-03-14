# Qwen3 TTS

## 소개
Qwen3-TTS 기반으로 텍스트를 음성으로 생성하거나, 참조 오디오를 기반으로 보이스 클론을 수행합니다.

## 현재 최소 기능
- Preset Voice 모드
- Clone from Audio 모드
- Design New Voice 모드
- 언어, 디바이스 선택
- WAV 파일 저장

## 현재 UX 방향
- 현재 앱은 `Flet` 기준으로 재구성되며, `qwen3_tts_flet_app.py`, `qwen3_tts_service.py`, `qwen3_tts_state.py`로 UI/서비스/상태를 분리한다
- 창 크기, 표면 색상, spacing, radius, progress dialog는 공유 런타임 `contexthub/ui/flet/` 토큰과 헬퍼를 우선 사용한다
- 상단 모델 상태 바, 중앙 채팅 버블, 하단 입력 바로 구성
- 싱글/대화 구분 없이 버블 개수에 따라 사실상 단건/일괄 흐름을 처리
- 버블 클릭 시 삭제, 이것만 생성, 현재 프로필 적용, 출력 재생 가능
- 선택된 버블 안에서 프로필과 톤을 바로 바꾸고, 해당 프로필 편집기로 직접 이동할 수 있다
- 선택된 버블은 `Detail Tray` 형태의 하위 패널을 열고, 생성이 끝난 버블은 `Result Card`에서 waveform, 재생, 파일 열기, 재생성을 제공한다
- `Detail Tray`의 액션은 `Generate This` 중심으로 단순화하고, 덜 중요한 조작은 `More` 패널로 접어 시선을 정리한다
- 선택된 버블의 텍스트는 `Edit Text`로 바로 수정할 수 있어, 하단 입력창으로 내려가지 않고도 대사를 다듬을 수 있다
- 프로필 관리는 우측 패널에서 저장/수정/삭제 가능
- 우측 프로필 패널은 모드별로 필요한 필드만 보여서 `Preset Voice`, `Clone from Audio`, `Design New Voice`를 더 직관적으로 구분한다
- clone 결과 카드는 생성 타입과 참조 오디오 정보를 같이 보여줘 결과의 출처를 바로 이해할 수 있다
- clone 프로필과 clone 결과 카드에는 참조 음성 상태를 진단해서 `ready / short / transcript missing / file missing` 수준으로 보여준다
- 프로필 관리는 우측 패널에서 이어서 편집할 수 있어, 대화 흐름을 끊지 않는다
- 모델은 기본적으로 `1.7B` 기준으로 고정해 복잡도를 줄임
- 하단 입력 바에서는 `Profile`, `Tone`만 기본 노출하고, `More`를 열었을 때 `Language`, `Device`, `Clone Setup`이 나타난다
- 버블은 좌측 원형 프로필 색상과 더 둥근 카드 형태로 보여, 누가 말하는지 빠르게 구분할 수 있다
- 생성 중에는 오버레이 안내와 완료 상태를 표시하고, 완료 후 폴더 바로가기를 제공
- 동일 파일명이 이미 존재하면 자동으로 `_2`, `_3` 식의 새 이름으로 저장해 기존 결과를 덮어쓰지 않는다
- 재생 중인 결과는 waveform 하이라이트와 시간 표시로 현재 상태를 보여준다
- 재생 파형은 가벼운 playhead만 사용해 상태감을 높이되, 과한 애니메이션으로 성능을 떨어뜨리지는 않도록 유지한다
- 후속 회귀 테스트로 `Preset Voice`와 `Clone from Audio` 생성이 다시 성공했다
- 추가 후속 회귀로 `Clone from Audio`가 다시 성공했고, 샘플은 `Diagnostics/generated/qwen3_followup2/clone_followup2.wav` 에 기록됐다

## 현재 제약
- Tone 프리셋은 `Preset Voice` / `Design New Voice`에 직접 반영된다.
- `Clone from Audio`는 공식 API 특성상 참조 음성 기반이라, 톤 프리셋이 같은 방식으로 직접 적용되지는 않는다.
- 진행률은 내부 토큰 단위가 아니라 작업 완료 단위 기준으로 표시한다.
- 긴 단일 생성은 중간 세부 퍼센트 없이 현재 작업 상태만 보여준다.

## 모드 설명
- `Preset Voice`: Qwen이 제공하는 기본 화자와 스타일 지시문을 조합해 빠르게 생성
- `Clone from Audio`: 참조 음성(`ref_audio`)과 선택적 전사(`ref_text`)를 기반으로 새 문장을 같은 화자 느낌으로 생성
- `Design New Voice`: 자연어 설명으로 새로운 목소리 캐릭터를 설계해 생성

## 스트레스 테스트 결과
- `Preset Voice`, `Clone from Audio`, `Design New Voice` 단건 생성 성공
- 혼합 배치 생성 성공
- `Clone from Audio`의 잘못된 입력은 이제 모델 로드 전에 즉시 에러로 중단
- 결과 샘플과 리스크 기록은 `Diagnostics/qwen3-tts-stress-report-2026-03-13.md`를 참고

## 실행 방식
- Quick Launcher에서 단독 실행 가능
- `.txt`, `.md` 파일 우클릭 시 텍스트 프리필
- 오디오 파일 우클릭 시 Voice Clone 참조 오디오 프리필

## 주의
- Qwen3-TTS 공식은 Python 3.12의 새 Conda 환경을 권장합니다.
- 현재 앱은 legacy GUI fallback 없이 Flet UI만 사용합니다.
- `flet 0.82.2`는 실제 런타임 Python과 `contexthub-ai` Conda env에 설치되어 있습니다.
- 첫 실행 시 Flet 데스크톱 런타임인 `flet-desktop 0.82.2`가 자동 설치될 수 있으며, 이는 정상입니다.
- 현재 앱은 최소 기능 GUI와 추론 경로가 구성되어 있으며, `contexthub-ai` Conda 환경에서 RTX 기준 실생성 검증을 마쳤습니다.
- 권장 환경 예시:
  - Python 3.12
  - `torch 2.10.0+cu126`
  - `torchaudio 2.10.0+cu126`
  - `qwen-tts`
- `custom_voice` 최소 생성 샘플은 `Diagnostics/generated/qwen3_tts_test.wav` 에 기록되어 있습니다.
- 추가 스트레스 샘플은 `Diagnostics/generated/qwen3_stress/` 아래에 기록되어 있습니다.
- SoX 경고가 표시될 수 있지만, 현재 최소 생성 검증 자체는 성공했습니다.
