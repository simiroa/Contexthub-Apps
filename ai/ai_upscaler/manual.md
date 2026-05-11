# AI Image Upscaler

ComfyUI 워크플로우에 위임해 이미지를 업스케일·복원하는 ai 카테고리 앱입니다.
지원 모델: **Real-ESRGAN**, **DiffBIR-v2**, **SUPIR**.

## 1. 사전 준비

1. **ComfyUI 서버 기동**
   - `comfyui/comfyui_dashboard` 앱으로 ComfyUI 서버를 실행해 두세요.
   - 기본 포트(8190 / 8188 / 8189) 중 어디든 응답하면 됩니다.

2. **커스텀 노드/체크포인트 설치 (모델별)**
   - Real-ESRGAN: ComfyUI 기본 `ImageUpscaleWithModel` + `UpscaleModelLoader`.
     체크포인트 예: `RealESRGAN_x4plus.pth`, `4x_NMKD-Siax_200k.pth`.
   - DiffBIR-v2: `ComfyUI-DiffBIR` 커스텀 노드 + 가중치(`general_full_v1.ckpt` 등).
   - SUPIR: `ComfyUI-SUPIR` 커스텀 노드 + SDXL 베이스 + SUPIR 가중치. **VRAM ≥ 16GB 권장.**

3. **워크플로우 저장**
   - ComfyUI에서 원하는 업스케일 그래프를 구성한 뒤 메뉴에서 **Save (API Format)** 으로 저장.
   - 다음 약속된 파일명으로 `ai/_engine/assets/workflows/upscaler/` 폴더에 배치합니다:
     - `esrgan.json`  — Real-ESRGAN 워크플로우
     - `diffbir.json` — DiffBIR-v2 워크플로우
     - `supir.json`   — SUPIR 워크플로우
   - 앱의 **Open workflows folder** 버튼으로 해당 폴더를 바로 열 수 있습니다.

## 2. 워크플로우 작성 규칙

앱은 워크플로우 JSON을 단순한 규칙으로 주입합니다:

- **LoadImage 노드의 첫 인스턴스**의 `image` 필드를 선택된 입력 이미지로 교체합니다.
  (입력 이미지는 ComfyUI 서버의 `/upload/image` API로 자동 업로드됩니다.)
- **SaveImage 노드의 첫 인스턴스**의 `filename_prefix` 가 사용자가 지정한 출력 prefix로 교체됩니다.
- `KSampler*` 노드가 있고 사용자가 Seed 를 지정하면 `seed` 필드가 갱신됩니다.
- `*Upscale*` 계열 노드의 `scale_by` 또는 `upscale_by` 필드가 발견되면 Scale 값으로 갱신합니다(있을 때만).

따라서 워크플로우 한 개당 LoadImage 1 개, SaveImage 1 개 구조면 가장 안정적입니다.

## 3. 사용 흐름

1. 앱 실행 → 좌측 패널에서 이미지 추가 또는 컨텍스트 메뉴로 이미지 우클릭 → "AI Image Upscaler".
2. 우측에서 **Model** 선택. 해당 워크플로우 파일이 없으면 경로 안내가 표시됩니다.
3. (선택) **Scale**, **Seed**, **Output prefix**, **Output dir** 조정.
4. **Run** 클릭 → ComfyUI 큐잉 → 완료되면 결과 이미지가 출력 폴더에 저장됩니다.

## 4. 트러블슈팅

- **"ComfyUI server not reachable"**: ComfyUI Dashboard 앱으로 서버를 먼저 실행하세요.
- **"Workflow file not found"**: 해당 모델의 JSON 파일명이 정확한지 확인하세요(`esrgan.json` 등).
- **"No LoadImage node"**: 워크플로우에 LoadImage 노드를 1개 이상 두세요.
- **결과 색공간 이상**: SaveImage 노드를 워크플로우 끝에 명시적으로 두었는지 확인하세요.
