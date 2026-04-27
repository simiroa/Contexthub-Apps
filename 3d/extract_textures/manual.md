# Extract Textures (텍스처 추출)

## 소개
선택한 3D 파일에서 임베드된 텍스처를 추출해 원본 옆 `textures` 폴더로 저장합니다.

## 사용법

1. 3D 파일 선택 후 우클릭
2. **3D → Extract Textures** 선택
3. mini Qt 확인 창에서 선택 개수와 대상 파일을 확인
4. **Extract** 실행
5. 앱이 각 소스 파일 옆에 `textures` 폴더를 만들고 추출 결과를 저장

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
- GLB/GLTF (임베드 리소스 구조에 따라 제한적)

## 의존성
- Blender 또는 pymeshlab

## UI 유형
- mini Qt shell
