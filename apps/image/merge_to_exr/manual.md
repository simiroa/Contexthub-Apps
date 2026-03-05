# Merge to EXR (EXR 병합)

## 소개
여러 이미지를 하나의 멀티레이어 EXR 파일로 병합합니다. VFX 합성 작업에서 패스 관리에 유용합니다.

## 사용법

1. 합칠 이미지 파일들 선택 (Ctrl+클릭)
2. 우클릭 → **Image → Merge to EXR** 선택
3. 각 이미지의 레이어 이름 지정:
   - Beauty
   - Diffuse
   - Specular
   - Reflection
   - Shadow
   - etc.
4. 저장 위치 및 파일명 지정
5. 병합 실행

## 지원 입력 포맷
- PNG, JPG, TIFF, EXR (단일 레이어)

## 출력 파일
- `output.exr`: 멀티레이어 EXR

## 활용 예시
- 렌더 패스를 하나의 파일로 관리
- Nuke/AfterEffects 합성 준비
- 렌더팜 출력 정리

## 의존성
- OpenEXR
