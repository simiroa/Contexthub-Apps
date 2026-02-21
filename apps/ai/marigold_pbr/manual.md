# Marigold PBR Generator (AI PBR 맵 생성)

## 소개
Marigold AI 모델을 사용하여 일반 사진/텍스처에서 3D용 PBR 맵(Depth, Normal)을 자동 생성합니다.

## 생성 가능한 맵

| 맵 종류 | 설명 | 용도 |
|--------|-----|------|
| **Depth Map** | 깊이 정보 | 시차 효과, 3D 변환 |
| **Normal Map** | 표면 법선 | 조명 효과, 디테일 추가 |

## 사용법

1. 텍스처/사진 파일 선택 후 우클릭
2. **AI → Marigold PBR Generator** 선택
3. 생성할 맵 종류 선택
4. 처리 완료 대기 (이미지당 5-15초)

## 출력 파일
```
원본파일_depth.png    # 깊이 맵
원본파일_normal.png   # 노멀 맵
```

## 활용 예시
- 게임 텍스처 PBR 맵 생성
- 2D 이미지에 3D 시차 효과 적용
- 조명 반응형 배경 제작
- 3D 모델 디테일 추가

## 시스템 요구사항
- NVIDIA GPU 필수 (CUDA)
- VRAM 6GB 이상 권장

## 의존성
- Marigold (Diffusion 기반)
- PyTorch
