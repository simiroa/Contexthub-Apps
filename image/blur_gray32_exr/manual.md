# Blur To Gray32 EXR

## 소개
선택한 이미지를 grayscale 기준으로 정리한 뒤, edge-preserving guided smoothing을 적용하고 `float32` EXR로 저장합니다.

이 앱은 작은 확인 UI에서 `blur radius`만 입력받고, 실제 처리는 콘솔 진행 로그로 넘깁니다.

## 사용법

1. 지원 이미지 파일을 선택하고 우클릭합니다.
2. **Image → Blur To Gray32 EXR** 를 실행합니다.
3. 작은 창에서 파일 개수와 출력 규칙을 확인합니다.
4. `blur radius`를 입력한 뒤 **Run** 을 누릅니다.
5. 콘솔 로그에서 처리 진행과 결과를 확인합니다.

## 출력 파일

- `원본파일명_blur_gray32.exr`
- 저장 위치: 원본과 동일 폴더

## 처리 규칙

- 항상 `grayscale -> median denoise -> guided smoothing -> float32 EXR` 순서로 처리합니다.
- 원본 파일은 유지합니다.
- 이미 `_blur_gray32` suffix가 붙은 파일은 다시 처리하지 않습니다.

## 지원 입력

- `.png`
- `.jpg`, `.jpeg`
- `.tga`
- `.tif`, `.tiff`
- `.bmp`
- `.webp`

## blur radius 가이드

- `0` 이면 smoothing 없이 grayscale float32 EXR만 생성합니다.
- `1.5`, `2`, `4` 같은 양수를 넣으면 edge를 유지하면서 평탄 영역을 더 강하게 정리합니다.
- 음수와 비숫자 값은 허용되지 않습니다.

## 의존성

- Pillow
- numpy
- OpenEXR
