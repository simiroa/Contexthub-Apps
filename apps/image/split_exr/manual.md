# Split EXR (EXR 분리)

## 소개
멀티레이어 EXR 파일을 개별 이미지 파일들로 분리합니다.

## 사용법

1. 멀티레이어 EXR 파일 선택 후 우클릭
2. **Image → Split EXR** 선택
3. 추출할 레이어 선택 (전체 또는 특정 레이어)
4. 출력 포맷 선택:
   - EXR (개별)
   - PNG
   - TIFF
5. 분리 실행

## 출력 파일
```
원본파일_beauty.png
원본파일_diffuse.png
원본파일_specular.png
...
```

## 지원 레이어
- **Color 레이어**: RGB, RGBA
- **AOV 레이어**: Diffuse, Specular, Reflection
- **Utility 레이어**: Depth, Normal, ID

## 활용 예시
- 합성용 개별 패스 추출
- Photoshop에서 편집하기 위해 분리
- 특정 패스만 재렌더 대신 추출

## 의존성
- OpenEXR
