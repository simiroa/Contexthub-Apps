# ComfyUI Creative Studio (Advanced)

## 소개
Qt 기반의 고급 ComfyUI 작업 셸입니다. 좌측 입력 자산과 프리뷰, 우측 파라미터, 우하단 고정 실행 영역으로 구성되며 이후 ComfyUI GUI 규격의 기준점으로 사용합니다.

## 주요 기능
- 상단 앱 헤더, 설명, 런타임 상태 배지
- 좌측 입력 프리뷰와 입력 목록 관리
- 우측 워크플로 프리셋 선택과 동적 파라미터 편집
- 우하단 출력 폴더, 세션 export, 실행 버튼 고정
- ComfyUI WebUI 열기 및 세션 JSON export

## 사용법
1. **ComfyUI → Creative Studio (Advanced)** 실행
2. 좌측 **Add Inputs**로 이미지나 미디어 입력 추가
3. 우측 상단에서 워크플로 프리셋 선택
4. 파라미터를 조정하고 출력 폴더와 파일 prefix 설정
5. **Export Session** 또는 **Run Workflow** 실행
6. 필요하면 **Open WebUI**로 ComfyUI 웹 인터페이스를 연다

## 요구사항
- **ComfyUI** 설치 필요
- **PySide6** 설치 필요
- 실제 workflow 템플릿과 노드 팩은 사용 프리셋에 따라 추가 필요

## 참고
- 현재 Qt 파일럿은 자산 관리와 파라미터 셸 표준화가 목적이다
- workflow 템플릿이 없는 프리셋은 세션 JSON export로 안전하게 fallback 한다
