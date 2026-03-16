# Qwen3 TTS

## 소개
`Qwen3-TTS` 기반 음성 생성 앱입니다. 현재 앱은 Qt 공유 런타임 기반이며, 채팅 앱처럼 대사를 쌓고 선택 생성 또는 대화 전체 일괄 생성을 수행합니다.

## 핵심 흐름
- 좌측 대화 리스트에서 메시지를 선택하거나 새 메시지를 추가
- 하단 작성 영역에서 `Profile`, `Tone`, `Language`, `Device`를 맞춘 뒤 저장
- `Generate This`로 선택 메시지 1건 생성
- `Generate Conversation`으로 현재 대화 전체 배치 생성
- 우측 결과 패널에서 재생, 파일 열기, 폴더 열기, 재생성 수행

## 지원 모드
- `Preset Voice`: 기본 화자와 스타일 지시문 기반 생성
- `Clone from Audio`: 참조 음성(`ref_audio`)과 선택적 전사(`ref_text`) 기반 클론 생성
- `Design New Voice`: 자연어 설명으로 새 목소리 캐릭터 설계

## 프로필 편집
- 우측 `Profile Editor`에서 저장, 수정, 삭제 가능
- `Clone from Audio`는 유효한 참조 오디오 경로가 필요
- `Design New Voice`는 설명 문구가 비어 있으면 저장되지 않음
- 프로필 저장 후 작성 영역과 메시지 생성에 바로 반영

## 타깃 실행
- `.txt`, `.md` 파일로 실행하면 첫 메시지 텍스트가 프리필됨
- 오디오 파일로 실행하면 클론용 프로필이 자동 추가되고 첫 메시지에 연결됨
- 현재는 전달된 타깃 중 첫 번째 경로만 초기 프리필에 사용

## 현재 UX 범위
- Flet 전용 고급 애니메이션과 상세 패널은 제외
- 핵심 채팅형 UX만 유지:
  - 메시지 큐
  - 선택/수정/삭제
  - 단건 생성
  - 일괄 생성
  - 결과 재생/열기
  - 프로필 관리

## 실행 방식
- Quick Launcher에서 단독 실행 가능
- 컨텍스트 메뉴에서 텍스트/오디오 파일 target 전달 가능
- Qt 앱 실행 중 `PySide6`가 없으면 의존성 안내 dialog를 표시

## 환경 메모
- 기본 모델 크기는 `1.7B` 고정
- 권장 환경:
  - Python 3.12
  - `torch`
  - `torchaudio`
  - `qwen-tts`
- `ai` 카테고리 규칙상 `contexthub-ai` Conda env를 우선 사용하며, 없으면 현재 Python으로 fallback
