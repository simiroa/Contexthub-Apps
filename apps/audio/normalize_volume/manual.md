# Normalize Volume (볼륨 정규화)

## 소개
여러 오디오 파일의 볼륨을 일정한 수준으로 평준화하여 소리 크기 차이를 없앱니다.

## 사용법

1. 오디오 파일(들) 선택 후 우클릭
2. **Audio → Normalize Volume** 선택
3. 옵션 설정:
   - **Target Level**: 목표 볼륨 레벨 (-14 LUFS 권장)
   - **Peak Limit**: 클리핑 방지 피크 제한
4. 정규화 실행

## 출력 파일
- `원본파일명_normalized.wav` 또는 원본 덮어쓰기

## 정규화 방식
- **Peak Normalization**: 피크 레벨 기준
- **LUFS Normalization**: 인지 음량 기준 (권장)

## 활용 예시
- 팟캐스트 에피소드 볼륨 통일
- 음악 믹스 수준 맞추기
- 다양한 소스 오디오 편집
- YouTube 업로드 전 음량 조절

## 의존성
- FFmpeg (자동 설치)
