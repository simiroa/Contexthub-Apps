# CAD to OBJ (CAD → OBJ 변환)

## 소개
STEP, IGES 등 CAD 포맷을 게임/렌더링에서 사용할 수 있는 OBJ 메쉬로 변환합니다.

## 지원 변환

| 입력 | 출력 |
|-----|-----|
| STEP (.stp, .step) | OBJ |
| IGES (.igs, .iges) | OBJ |
| BREP (.brep) | OBJ |

## 사용법

1. CAD 파일 선택 후 우클릭
2. **3D → CAD to OBJ** 선택
3. 변환 옵션 설정:
   - **해상도**: 테셀레이션 품질
   - **단위**: mm, cm, m
4. 변환 실행

## 출력 파일
- `원본파일명.obj`: 폴리곤 메쉬
- `원본파일명.mtl`: 재질 파일 (선택)

## 활용 예시
- CAD 모델을 게임 엔진으로
- 제품 디자인 렌더링
- 3D 프린팅 준비
- VR/AR 콘텐츠 제작

## 요구사항
- Blender 또는 Mayo 설치 필요
