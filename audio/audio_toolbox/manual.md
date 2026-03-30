# Audio Toolbox

## 소개
`Audio Toolbox`는 `audio` 카테고리의 분리, 정규화, 변환 기능을 한 화면으로 모은 통합 앱입니다.

하나의 창에서 다음 작업을 선택하고 바로 실행할 수 있습니다.

- `Extract Voice`
- `Extract BGM`
- `Normalize Volume`
- `Convert Audio`

## 주요 기능
- `audio-separator` 기반 보컬/BGM 분리
- 모델 선택과 출력 포맷 제어
- 긴 파일을 위한 chunk duration 설정
- `ffmpeg-normalize` 우선 기반 loudness 정규화
- FFmpeg 기반 포맷 변환 및 메타데이터 유지 옵션

## 사용법
1. 오디오 파일을 선택한 뒤 우클릭합니다.
2. `Audio -> Audio Toolbox`를 실행합니다.
3. 왼쪽에서 입력 파일을 확인합니다.
4. 오른쪽에서 작업 종류와 옵션을 선택합니다.
5. 출력 폴더 모드를 고릅니다.
6. `Run Task`를 눌러 실행합니다.

## 출력 규칙
- `Extract Voice`: 기본적으로 원본 폴더에 `*_voice.<format>`
- `Extract BGM`: 기본적으로 원본 폴더에 `*_bgm.<format>`
- `Normalize Volume`: 기본적으로 원본 폴더에 `*_normalized.<ext>`
- `Convert Audio`: 기본적으로 원본 폴더에 `*_conv.<format>`

`Task Folder` 또는 `Custom` 모드를 선택하면 작업별 전용 폴더 또는 지정한 폴더로 출력할 수 있습니다.

## 의존성
- `audio-separator`
- `ffmpeg-normalize`
- `ffmpeg`

## 참고
- 기존 `Extract BGM`, `Extract Voice`, `Normalize Volume` 앱은 그대로 유지됩니다.
- 이 앱은 고급 옵션 조정과 일괄 작업을 위한 메인 진입점으로 설계되었습니다.
