# ComfyUI Inpainting

## 소개
이미지 위에 브러시로 마스크를 칠하고, ComfyUI를 통해 해당 영역을 인페인팅(재생성)합니다.

## 사용법

1. **ComfyUI → Inpainting** 실행
2. **이미지 등록**: Load Image 버튼 또는 드래그앤드롭
3. **마스크 칠하기**: 마우스 좌클릭으로 브러시 페인팅
   - 휠: 브러시 크기 조절
   - Eraser 버튼: 지우개 모드
   - Ctrl+Z / Ctrl+Shift+Z: Undo / Redo
   - Ctrl+휠: 이미지 줌
   - 중클릭 드래그: 이미지 패닝
4. **프롬프트 입력**: 마스크 영역에 생성할 내용 작성
5. **파라미터 조절**: Steps, CFG, Denoise Strength 등
6. **Run Inpainting** 클릭

## 기능
- **브러시 캔버스**: 반투명 마스크 오버레이로 인페인팅 영역 시각화
- **브러시 크기 조절**: 슬라이더 또는 마우스 휠
- **Undo / Redo**: 최대 40단계 마스크 히스토리
- **파라미터 제어**: Checkpoint, Steps, CFG, Denoise, Sampler, Seed
- **ComfyUI 연동**: 로컬 ComfyUI 서버 자동 감지

## 활용 예시
- 사진 속 불필요한 객체 제거 및 교체
- 배경 부분 교체
- 텍스처 보정 및 디테일 추가
- 일러스트 부분 수정

## 요구사항
- **ComfyUI**: 설치 완료 및 실행 중
- **인페인팅 모델**: SD 1.5 inpainting 또는 SDXL 기반 체크포인트 권장
