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
3. mini 확인 창에서 선택 파일 수와 출력 규칙 확인
4. **Convert**를 누르면 콘솔 흐름에서 OBJ 변환 진행

## 출력 파일
- `원본파일명.obj`: 원본 CAD 파일과 같은 폴더에 생성되는 폴리곤 메쉬

## 활용 예시
- CAD 모델을 게임 엔진으로
- 제품 디자인 렌더링
- 3D 프린팅 준비
- VR/AR 콘텐츠 제작

## 요구사항
- Mayo 설치 필요
- Mayo 경로 문제는 앱 본문이 아니라 실행 시 경고/알림 흐름에서 처리될 수 있음
