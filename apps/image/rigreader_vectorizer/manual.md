# RigReady Vectorizer

## 소개
일반 이미지(PNG, JPG, PSD 등)를 무한 확장 가능한 벡터(SVG) 형식으로 정밀하게 변환합니다. Adobe Illustrator와 After Effects 연동을 지원합니다.

## 주요 기능
- **이미지 → SVG 변환**: vtracer 엔진 기반 고품질 벡터화
- **PSD 레이어 지원**: 포토샵 파일의 레이어별 벡터 추출
- **배경 제거 옵션**: 투명 배경으로 변환
- **앵커 포인트 최적화**: 리깅용 깔끔한 패스 생성
- **AE 스크립트 내보내기**: After Effects용 JSX 자동 생성

## 사용법

1. 변환할 이미지를 우클릭하고 **Image → RigReady Vectorizer** 선택
2. GUI에서 설정 조정:
   - **Detail Level**: 디테일 수준 (낮음 = 깔끔, 높음 = 정밀)
   - **Remove Background**: 배경 제거 여부
   - **Mode**: 일반 / 리깅용
3. **Start** 버튼으로 변환 시작
4. 결과 SVG가 같은 폴더에 저장됨

## 출력 파일
| 파일 | 설명 |
|------|-----|
| `*_vectorized.svg` | 벡터화된 SVG 파일 |
| `*_ae_import.jsx` | After Effects 임포트 스크립트 |

## 지원 포맷
- **입력**: PNG, JPG, JPEG, BMP, GIF, TIFF, PSD
- **출력**: SVG

## 의존성
- vtracer (Rust 기반 벡터 변환 엔진)
- psd-tools (PSD 파싱)
- Pillow (이미지 처리)
