# Image Convert (이미지 변환)

## 소개
범용 이미지 포맷(PNG, JPG, WebP)부터 전문 RAW, PSD, EXR, HEIC 포맷까지 다양한 형식을 일괄 변환합니다.

## 지원 포맷

### 입력 포맷
| 카테고리 | 확장자 |
|---------|-------|
| **일반** | PNG, JPG, JPEG, BMP, GIF, TIFF, WebP |
| **RAW** | CR2 (Canon), NEF (Nikon), ARW (Sony), DNG |
| **전문** | PSD, EXR, HDR, TGA |
| **모바일** | HEIC, HEIF, AVIF |

### 출력 포맷
- PNG (무손실, 투명 지원)
- JPG/JPEG (손실, 용량 최적화)
- WebP (고효율, 투명 지원)
- TIFF (무손실, 레이어 지원)
- BMP (비압축)

## 사용법

1. 변환할 이미지 파일(들) 선택 후 우클릭
2. **Image → Image Convert** 선택
3. GUI에서 설정:
   - **출력 포맷**: 원하는 형식 선택
   - **품질**: JPG/WebP의 경우 압축률 조절
   - **크기 조절**: 필요시 리사이즈 적용
4. **Convert** 버튼으로 변환 시작

## 배치 처리
- 여러 파일을 동시 선택하여 일괄 변환 가능
- 원본 파일명 유지, 확장자만 변경
- 같은 폴더에 결과 파일 저장

## 의존성
- Pillow (기본 이미지 처리)
- rawpy (RAW 포맷)
- pillow-heif (HEIC/AVIF)
- OpenEXR (EXR 포맷)
