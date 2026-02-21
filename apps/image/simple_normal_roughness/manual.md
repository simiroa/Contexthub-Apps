# Simple Normal/Roughness (간단 노멀/러프니스 생성)

## 소개
일반 텍스처 이미지에서 간단한 노멀맵과 러프니스 맵을 자동 생성합니다. AI가 아닌 알고리즘 기반으로 빠르게 처리됩니다.

## 생성 가능한 맵
| 맵 | 생성 방식 |
|---|---------|
| **Normal Map** | Sobel 필터 기반 엣지 검출 |
| **Roughness Map** | 그레이스케일 변환 + 반전 |

## 사용법

1. 텍스처 이미지 선택 후 우클릭
2. **Image → Simple Normal Roughness** 선택
3. 생성 옵션:
   - **Strength**: 노멀맵 강도
   - **Invert**: 러프니스 반전 여부
4. 생성 실행

## 출력 파일
```
원본파일명_normal.png
원본파일명_roughness.png
```

## 활용 예시
- 빠른 프로토타입 텍스처
- 간단한 게임 에셋
- AI 맵(Marigold)이 과할 때

## 참고
- 정밀한 맵이 필요하면 Marigold PBR 사용 권장
- 알고리즘 기반으로 빠르지만 정확도 낮음

## 의존성
- Pillow, scipy
