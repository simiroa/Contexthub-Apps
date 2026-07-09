# ComfyUI Dashboard

## 소개
설치된 ComfyUI 서버를 Qt 미니 대시보드에서 관리합니다.

## 사용법

1. **ComfyUI → ComfyUI Dashboard** 실행
2. 대시보드에서:
   - 서버 시작/중지
   - 웹 UI 열기
   - 마지막 로그 줄 확인
   - 로그 콘솔 열기
   - ComfyUI 및 Git 기반 커스텀 노드 업데이트
   - 커스텀 노드 Git URL 설치

## 기본 URL
- `http://127.0.0.1:8190`

## 기능
- **서버 관리**: 시작, 중지, 상태 확인
- **브라우저 열기**: 기본 브라우저로 UI 접속
- **로그 확인**: 서버 콘솔 로그 확인
- **상태 진단**: 포트, PID, 시작 상태, 마지막 로그 표시
- **커스텀 노드 설치**: Git 저장소 URL을 `custom_nodes` 폴더에 clone하고 `requirements.txt`가 있으면 설치
- **업데이트**: ComfyUI git checkout과 Git 기반 커스텀 노드를 `git pull --ff-only`로 업데이트

## 활용 예시
- ComfyUI 워크플로우 직접 편집
- 커스텀 노드 테스트
- 서버 상태 확인 및 복구

## 요구사항
- **ComfyUI**: 설치 완료
- **Git**: 커스텀 노드 설치/업데이트 시 필요
- Manager → Settings에서 경로 설정
