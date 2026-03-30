# Meeting Notes AI (Qt)

## 개요
회의 음성을 텍스트로 변환하고, 오디오/비디오 재생과 함께 회의 내용을 정리하는 앱입니다.

입력 큐를 구성한 뒤 한 번에 전사하고, 각 자산을 열어 재생하면서 transcript를 읽고 요약, 결정사항, 액션 아이템, 후속 작업을 정리할 수 있습니다.

## 핵심 기능
- 입력 큐: 오디오/비디오 파일 혼합 등록, 드래그 앤 드롭, 배치 실행
- 재생 연동: 오디오/비디오 플레이어와 seek bar, 재생 속도 조절
- Transcript 보기: 세그먼트 목록과 전체 transcript 읽기
- 회의 메모 보드: `Summary`, `Decisions`, `Action Items`, `Follow-up`
- 세션 복구: transcript와 회의 메모를 자산별 세션 파일로 복구
- 출력: transcript 파일과 회의 요약 markdown 저장

## 사용법
1. 앱 실행 후 입력 파일을 추가합니다.
2. `Run Selected` 또는 `Run Queue`로 transcript 생성을 시작합니다.
3. 생성 완료 후 중앙 플레이어에서 회의를 재생하며 transcript를 확인합니다.
4. 우측 회의 메모 보드에 요약, 결정사항, 액션 아이템, 후속 작업을 정리합니다.
5. `Export`로 transcript와 회의 요약 markdown을 저장합니다.

## 검수 팁
- 긴 회의는 `Queue`로 일괄 전사한 뒤 회의별로 메모만 채우는 방식이 빠릅니다.
- 오디오 전용 입력도 동일한 메모 보드를 사용합니다.

## 시스템 요구사항
- Faster-Whisper 실행 환경
- CUDA 사용 시 적절한 GPU 드라이버 및 런타임
