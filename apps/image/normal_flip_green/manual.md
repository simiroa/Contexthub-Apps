# Normal Flip Green (노멀맵 그린채널 반전)

## 소개
노멀 맵의 그린(Y) 채널을 반전시킵니다. DirectX↔OpenGL 노멀맵 변환에 사용됩니다.

## 왜 필요한가?
- **DirectX (Y-)**: Unreal Engine, 3ds Max
- **OpenGL (Y+)**: Unity, Blender, Maya
- 엔진 간 노멀맵 호환성을 위해 변환 필요

## 사용법

1. 노멀 맵 이미지 선택 후 우클릭
2. **Image → Normal Flip Green** 선택
3. 그린 채널 반전된 이미지 생성

## 출력 파일
- `원본파일명_flipped.png`

## 활용 예시
- Unity 에셋을 Unreal로 이전
- 외부 텍스처 엔진 호환 작업
- 노멀맵 방향 수정

## 참고
- 블루(Z) 채널은 변경되지 않음
- 레드(X) 채널도 변경되지 않음
- 그린(Y) 채널만 반전

## 의존성
- Pillow
