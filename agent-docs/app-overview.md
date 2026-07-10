# App Overview

## 저장소 성격

이 저장소는 Contexthub용 미니앱 마켓 소스 저장소다. 각 앱은 특정 입력 파일이나 작업 흐름에 대응하는 소형 도구이며, 대체로 GUI 기반 Python 앱으로 구성된다.

## 카테고리별 역할

- `3d`: 메시 변환, 텍스처 추출, CAD/OBJ 변환, LOD 같은 3D 자산 처리 도구
- `ai`: 배경 제거, 업스케일, 음성 분리, 자막 생성 등 무거운 AI 기반 도구
- `ai_lite`: 텍스트 유틸리티처럼 상대적으로 가벼운 AI 도구
- `audio`: AI 보컬/BGM 분리 및 오디오 툴박스 (정규화·트랙 조작은 SystemC `av_toolbox`)
- `comfyui`: ComfyUI 연동 또는 관련 워크플로용 도구
- `document`: 문서 변환/스캔 (PDF merge/split 은 SystemC `pdf_toolkit`)
- `image`: EXR 채널/ORM/노멀 등 VFX·텍스처 전용 (범용 변환·Po2 는 SystemC `media_converter`)
- `utilities`: 일반 생산성 (leave_manager 는 허브 빌트인)
- `video`: 마켓 페이로드 없음 — 변환/AV 유틸은 SystemC `media_converter` / `av_toolbox`

네이티브 흡수·제거 매트릭스는 `agent-docs/native-parity-and-removal.md` 를 본다.

## 앱의 공통 목적

각 앱은 Contexthub에서 다음 중 하나로 동작한다.

- GUI 앱으로 직접 실행
- 파일 확장자 기반 컨텍스트 메뉴 도구
- 별도 입력 없이 백그라운드/단독 실행되는 도구

## 공통 구성 파일

대부분의 앱 폴더는 다음 파일을 가진다.

- `manifest.json`: 앱 ID, 버전, 트리거, 실행 방식
- `main.py`: 실제 진입점
- `manual.md`: 허브에서 참조되는 사용 문서
- `icon.png` 또는 `icon.ico`: 마켓 표시 아이콘
- `requirements.txt`: 앱별 추가 의존성

## 앱 목적을 파악할 때 우선 확인할 항목

- `manifest.json`의 `triggers.context_menu.extensions`
- `manifest.json`의 `execution.mode`, `working_directory`
- `main.py`가 `_engine`의 기능 스크립트를 `runpy`로 위임하는지 여부
- `manual.md`에 기록된 사용자 대상 기능 설명
