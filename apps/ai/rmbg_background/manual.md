# RMBG Background Removal (AI 배경 제거)

## 소개
RMBG(Remove Background) 최신 AI 모델을 사용하여 복잡한 배경에서도 피사체만 깔끔하게 분리합니다.

## 주요 기능
- **정밀 마스킹**: 머리카락, 투명 물체까지 처리
- **자동 피사체 감지**: 사람, 동물, 물체
- **배치 처리**: 여러 이미지 일괄 처리
- **투명 배경 출력**: PNG 형식

## 사용법

1. 이미지 파일(들) 선택 후 우클릭
2. **AI → RMBG Background Removal** 선택
3. 처리 완료 대기
4. 투명 배경 이미지 생성

## 출력 파일
- `원본파일명_nobg.png`

## image_remove_bg_ai와 차이점
- RMBG: BiRefNet 모델 사용 (더 정밀)
- Remove Background AI: rembg 기본 모델

## 활용 예시
- 제품 사진 합성
- 증명사진 배경 교체
- 썸네일/배너 제작
- 콜라주 작업

## 시스템 요구사항
- NVIDIA GPU 권장
- VRAM 4GB 이상
