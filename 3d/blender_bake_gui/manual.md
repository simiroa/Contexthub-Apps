# Remesh & Bake (리메쉬 및 텍스처 베이크)

## 소개
Blender를 사용하여 고폴리곤 메쉬를 저폴리곤으로 재구성하고 노멀맵 등을 베이크합니다.

## 주요 기능
- **리메쉬**: 폴리곤 수 최적화
- **노멀맵 베이크**: 고폴리 디테일을 텍스처로 전송
- **UV 자동 생성**: Smart UV Projection
- **LOD 생성**: 거리별 디테일 레벨

## 사용법

1. 3D 메쉬 파일 선택 후 우클릭
2. **3D → Remesh & Bake** 선택
3. 옵션 설정:
   - **Target Poly Count**: 목표 폴리곤 수
   - **Bake Resolution**: 텍스처 해상도
   - **Bake Types**: Normal, AO, Curvature
4. 처리 시작

## 출력 파일
```
모델명_lowpoly.fbx      # 저폴리 메쉬
모델명_normal.png       # 노멀맵
모델명_ao.png           # 앰비언트 오클루전
```

## 요구사항
- **Blender**: 4.0 이상 설치 필요
- Manager → Settings에서 경로 설정
