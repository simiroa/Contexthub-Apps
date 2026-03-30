# Extract Textures (텍스처 추출)

## 소개
FBX 파일 내부에 임베드된 텍스처들을 외부 이미지 파일로 분리하여 추출합니다.

## 사용법

1. FBX 파일 선택 후 우클릭
2. **3D → Extract Textures** 선택
3. mini 확인 창에서 파일 개수를 확인
4. **Extract** 실행
5. 원본 파일과 같은 위치의 `textures` 폴더에 추출 결과 저장

## 출력 파일
원본 파일과 같은 폴더의 `textures` 폴더에 저장:
```
textures/
├── diffuse.png
├── normal.png
├── roughness.png
└── metallic.png
```

## 활용 예시
- 임베드 텍스처 별도 편집
- 다른 모델에 텍스처 재사용
- 텍스처 해상도 확인
- 에셋 정리 및 관리

## 지원 포맷
- FBX (임베드 텍스처 포함)
- GLB/GLTF (일부 지원)

## 의존성
- Blender 또는 pymeshlab

## UI 유형
- mini confirm Qt shell
