# Extract Audio

`Extract Audio`는 미디어 파일에서 오디오를 추출하거나 AI 기반 분리를 수행하는 mini Qt 앱입니다.

## 지원 모드

- `Extract All Audio (Copy)`
- `Extract Voice (AI)`
- `Extract BGM (AI)`

## UI 구성

- 상단에서 입력 개수와 현재 상태를 확인합니다.
- 가운데에서 모드와 출력 포맷을 선택합니다.
- `Run` 버튼으로 실행합니다.
- 출력 폴더는 작업별 기본 폴더, 원본 폴더, 사용자 지정 폴더 중 하나를 쓸 수 있습니다.

## 출력 위치

- `Extract All Audio`: 기본적으로 원본 위치
- `Extract Voice` / `Extract BGM`: 기본적으로 `Separated_Audio`

## 사용 방법

1. 오디오 또는 비디오 파일을 앱에 전달합니다.
2. 추출 모드를 선택합니다.
3. 출력 포맷을 고릅니다.
4. 필요하면 출력 폴더를 지정합니다.
5. `Extract`를 눌러 실행합니다.

## 요구 사항

- `ffmpeg`
- `audio-separator` 또는 `demucs`는 AI 분리 모드에서 사용될 수 있습니다.
