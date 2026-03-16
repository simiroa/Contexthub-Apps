# Split EXR (EXR 분리)

## 소개
멀티레이어 EXR 파일을 개별 이미지 파일들로 분리합니다.

이 앱은 짧은 확인 UI 후 콘솔 흐름으로 처리됩니다.

## 사용법

1. 멀티레이어 EXR 파일 선택 후 우클릭
2. **Image → Split EXR** 선택
3. 파일 개수 확인 후 **Split** 실행
4. 콘솔 진행 로그 확인

## 출력 파일
```
원본파일_split\beauty.png
원본파일_split\diffuse.png
원본파일_split\specular.png
...
```

- 기본 출력 포맷은 `PNG`
- 기본 출력 폴더는 `원본파일명_split`

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
