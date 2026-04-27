# Open with Mayo (Mayo로 열기)

## 소개
선택한 3D CAD 파일을 Mayo 뷰어로 바로 넘겨 빠르게 확인합니다.

## Mayo란?
- 무료 오픈소스 CAD 뷰어
- STEP, IGES, BREP 등 지원
- 빠른 로딩 및 가벼운 메모리 사용

## 사용법

1. CAD 파일 선택 후 우클릭
2. **3D → Open with Mayo** 선택
3. mini Qt 확인 창에서 선택 개수와 대상 파일을 확인
4. **Open** 실행
5. Mayo에서 모델 확인

## 지원 포맷
| 포맷 | 설명 |
|-----|-----|
| **STEP** | 표준 CAD 교환 포맷 |
| **IGES** | 레거시 CAD 포맷 |
| **BREP** | OpenCASCADE 네이티브 |
| **STL** | 3D 프린팅용 |
| **OBJ** | 폴리곤 메쉬 |

## 요구사항
- **Mayo**: 설치 필요 ([다운로드](https://github.com/fougue/mayo))
- Manager → Settings에서 Mayo 실행 파일 경로 설정

## UI 유형
- mini Qt shell

## 활용 예시
- CAD 파일 빠른 확인
- 엔지니어링 데이터 검토
- 3D 프린팅 전 확인
