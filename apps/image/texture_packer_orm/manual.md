# Texture Packer ORM (ORM 텍스처 패킹)

## 소개
Occlusion(R), Roughness(G), Metallic(B) 맵을 하나의 ORM 텍스처 채널로 병합합니다.

## ORM 텍스처란?
Unreal Engine, Unity 등 게임 엔진에서 사용하는 채널 패킹 방식:
- **R 채널**: Ambient Occlusion
- **G 채널**: Roughness
- **B 채널**: Metallic

## 사용법

1. 3개의 텍스처 이미지 선택 또는 1개 선택 후 실행
2. **Image → Texture Packer ORM** 선택
3. 각 채널에 이미지 할당:
   - **R (Occlusion)**: AO 맵
   - **G (Roughness)**: Roughness 맵
   - **B (Metallic)**: Metallic 맵
4. 출력 해상도 설정 (선택)
5. 패킹 실행

## 출력 파일
- `TextureName_ORM.png`

## 활용 예시
- 게임용 텍스처 최적화
- 텍스처 슬롯 수 절약
- PBR 워크플로우 표준화

## 의존성
- Pillow
