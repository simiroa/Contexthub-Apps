# AI Image Enhancer

ComfyUI 기반의 이미지 개선 앱입니다. 업스케일만 하는 도구가 아니라, 원본을 유지하면서 국소 보정, 마스크 페인팅, 레이어별 처리 패스를 조합하는 쪽에 초점을 둡니다.

## 사용 흐름

1. 이미지를 추가합니다.
2. 왼쪽 캔버스에서 필요 영역을 칠합니다.
3. 오른쪽에서 레이어를 추가하고 각 레이어의 워크플로우와 강도를 조절합니다.
4. `Run`으로 선택한 이미지에 레이어를 순차 적용합니다.

## 워크플로우 파일

아래 파일을 `comfyui/_engine/assets/workflows/enhancer/`에 `API Format` JSON으로 넣습니다.

| Mode | Filename |
|---|---|
| Global Enhance | `global.json` |
| Painted Detail | `detail.json` |
| Face Boost | `face.json` |
| Repair Pass | `repair.json` |

## 동작 규칙

- 첫 번째 `LoadImage` 노드의 `image` 필드는 현재 입력 이미지로 치환합니다.
- 첫 번째 `SaveImage` 노드의 `filename_prefix`는 출력 prefix로 치환합니다.
- `KSampler*` 노드의 `seed`가 있으면 고정 시드가 반영됩니다.
- `strength`, `denoise`, `blend`, `opacity` 같은 입력 필드는 가능한 경우 레이어 강도로 갱신합니다.
- 마스크가 있으면 `LoadImageMask` 또는 유사한 mask 입력 노드에 주입합니다.

## 차별점

- 단순 업스케일러보다 국소 보정에 초점을 둡니다.
- 브러시 마스크와 레이어 패스가 함께 동작합니다.
- 세션 JSON에 입력, 마스크, 레이어 구성이 함께 저장됩니다.

## 커스텀 노드 호환성 메모

- `FaceDetailer` 계열을 넣을 계획이면 `ComfyUI-Impact-Pack` 기준의 최신 구조를 따라야 합니다.
- `SUPIR`는 최신 안내상 ComfyUI core 쪽 사용이 우선이며, 외부 wrapper 워크플로우는 레거시 성격으로 보는 편이 안전합니다.
- `ControlNet` 전처리 노드를 쓰면 `comfyui_controlnet_aux` 같은 별도 패키지가 필요할 수 있습니다.
- 실제 워크플로우 JSON이 들어오기 전까지는 이 앱이 특정 custom node를 강제하지 않습니다. 노드명은 ComfyUI 설치본의 custom_nodes와 일치해야 합니다.
