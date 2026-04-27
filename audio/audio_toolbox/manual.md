# Audio Toolbox

`Audio Toolbox`는 `audio` 카테고리의 통합 작업창입니다. 왼쪽은 입력 목록과 미디어 미리보기, 오른쪽은 작업 설정과 실행 영역으로 나뉩니다.

## 지원 작업

- `Extract Voice`
- `Extract BGM`
- `Normalize Volume`
- `Convert Audio`
- `Compress Audio`
- `Enhance Audio`

## UI 구성

- 입력 파일은 왼쪽 목록에 표시됩니다.
- 선택한 파일은 상단 플레이어 카드에서 확인할 수 있습니다.
- 작업별 세부 옵션은 오른쪽 `Task Settings`에서 바뀝니다.
- 출력 포맷과 출력 폴더 모드는 실행 카드 하단에서 선택합니다.

## 출력 위치

- `Source folder`: 원본 파일과 같은 위치
- `Task folder`: 작업별 하위 폴더
- `Custom`: 사용자가 지정한 폴더

## 사용 방법

1. 오디오 파일을 앱에 전달하거나 목록에 추가합니다.
2. 작업 종류를 선택합니다.
3. 필요한 옵션과 출력 포맷을 고릅니다.
4. 출력 폴더 모드를 선택합니다.
5. `Run Task`를 눌러 실행합니다.

## 참고

- `audio-separator`, `ffmpeg-normalize`, `ffmpeg`가 사용될 수 있습니다.
- 단일 작업용 앱들은 `Extract Audio`, `Normalize Volume`, `Compress Audio`, `Convert Audio`, `Enhance Audio`입니다.
