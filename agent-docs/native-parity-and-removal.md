# Native SystemC Parity & Market Removal

기준: 2026-07-10  
네이티브: `Contexthub/src/ContextHub.SystemC` + `Apps_system`  
마켓: `Contexthub-Apps` only

## 1. 패리티 / 판정

| 마켓 앱 | 네이티브 정본 | 패리티 메모 | 판정 |
|---------|---------------|------------|------|
| `leave_manager_C` | `leave_manager` | 빌트인 정본 | **REMOVED** r1 |
| `pdf_merge` / `pdf_split` | `pdf_toolkit` | Split/Merge | **REMOVED** r1 |
| `extract_audio` / `remove_audio` / `interpolate_30fps` | `av_toolbox` | ffmpeg 동일 축 | **REMOVED** r1 |
| `normalize_volume` | `av_toolbox` | loudnorm | **REMOVED** r1 |
| `image_convert` | `media_converter` | EXR/ICO write + LongEdge (메인 커밋 e8f4065, 7187c35) | **REMOVED** r2 |
| `resize_power_of_2` | `media_converter` Po2 | Standard Po2/force-square. **잔여: Real-ESRGAN AI 모드 없음** | **REMOVED** r2 |
| `video_convert` | `media_converter` + `MediaVideoEncode` | H.264 High/Proxy/NVENC, ProRes, DNxHR, copy, GIF, CRF/scale, delete-original (5d53ae1 계열) | **REMOVED** r2 |
| `audio_toolbox` / `extract_bgm` / `extract_voice` | (없음) | Demucs AI stem — 네이티브 미흡수 | **KEEP** |
| `merge_to_exr` 등 VFX 단품 | (없음) | multi-layer EXR / ORM | **KEEP** |
| `simple_normal_roughness` | `TextureToolkit` (Normal/Roughness 모드) | 탄젠트 노멀 생성 + 러프니스 파생, FloatRGBA 브리지 | **REMOVED** r3 |
| `normal_flip_green` | `TextureToolkit` (FlipGreen 모드) | 노멀맵 그린채널 반전 (OpenGL↔DirectX) | **REMOVED** r3 |
| `blur_gray32_exr` | `TextureToolkit` (Gray32 블러 모드) | 스무딩 반경 포함 그레이스케일 float32 EXR 변환 | **REMOVED** r4 |
| AI / 3D / Comfy / youtube 등 | (없음) | — | **KEEP** |

## 2. Round-2 제거 단위 (실행됨)

### 앱 페이로드
- `video/video_convert/`
- `image/image_convert/`
- `image/resize_power_of_2/`

### 엔진
- `video/_engine/features/video/video_convert_*.py`, `tools.py`
- `image/_engine/features/image/image_convert_*.py`
- `image/_engine/features/image/resize_power_of_2_*` (+ package)

### 레지스트리 / 아티팩트
- `market.json` entries
- `dist/{video_convert,image_convert,resize_power_of_2}.zip`
- Diagnostics captures / logs / gui_runs
- 전 카테고리 `menu.py` / `headless_inputs.py`

## 3. 의도적 유지

- **AI 오디오**: `audio_toolbox`, `extract_bgm`, `extract_voice` (Demucs/UVR — SystemC 없음)
- **VFX 이미지**: `merge_to_exr`, `split_exr`, `texture_packer_orm` (EXR/ORM — 네이티브 `TextureToolkit` 미흡수)
  - **주의**: normal/roughness/flip-green/gray32-blur 계열은 r3~r4에서 `TextureToolkit`로 흡수·제거됨 (아래 §1, §5)
- **Host `*_C` alias**: 허브 config 마이그레이션 (Apps 레포 밖)

## 4. 잔여 소실 (문서화)

| 소실 | 영향 |
|------|------|
| Real-ESRGAN on Po2 | 마켓 `resize_power_of_2` AI 모드 제거됨 → 네이티브 Standard Po2만 |
| video 마켓 대형 Qt 셸 | 네이티브는 Convert Anything 다이얼로그 (기능 패리티 위주) |
| extract_audio WAV/copy | r1 부터 MP3 고정 감수 |

## 5. 실행 상태

### Round-1
- [x] AV/PDF/leave 단품 + 빈 껍데기

### Round-2
- [x] `video_convert`, `image_convert`, `resize_power_of_2` 물리 삭제
- [x] menu / headless / market / dist / Diagnostics
- [x] agent-docs 갱신
- 당시 마켓: **28** apps (manifest / market.json / dist 정합)

### Round-3 (네이티브 `TextureToolkit`)
네이티브 정본: `src/ContextHub.SystemC/Utils/TextureToolkitLogic.cs` (모드: FlipGreen / Normal / Roughness / Resize)
- [x] `simple_normal_roughness`, `normal_flip_green` payload 물리 삭제
- [x] 엔진: `_engine/features/image/simple_normal_roughness_{qt_app,service,state}.py` + `normal_flip_green_console.py` + 두 패키지 디렉터리(`simple_normal_roughness/`, `normal_flip_green/`)
- [x] menu.py ×9 / `headless_inputs.py` / `market.json` / `dist/*.zip`
- [x] `APP_TEST_LIST.md` / `Diagnostics/image_feature_smoke.py`(라이브 import 프루닝) / `gui-runtime-status`(Compact 5→4, Mini 8→7) / `gui-cleanup-backlog` / `new-app-guidelines` / `templates/README`
- 프리즈 유지: `.agents/**`, `agent-docs/designs/2026-07-10-*`, `agent-docs/prompts/*`, `Diagnostics/gui_capture_log.md`(런타임 생성)
- 현재 마켓: **24** apps

### Round-4 (네이티브 `TextureToolkit` Gray32 블러 모드)
- [x] `blur_gray32_exr` payload 물리 삭제
- [x] 엔진: `_engine/features/image/blur_gray32_exr/` 패키지 디렉터리(`__init__.py`, `console.py`, `qt_app.py`, `service.py`)
- [x] `market.json`(24→23) / `APP_TEST_LIST.md`
- [x] `gui-runtime-status`(Compact 4→3) / `gui-cleanup-backlog`
- 참고: 9x `menu.py` / `headless_inputs.py` / `Diagnostics/image_feature_smoke.py` / `new-app-guidelines` / `templates/README`에는 애초에 `blur_gray32_exr` 참조가 없어 변경 불필요(확인 완료)
- 프리즈 유지: `.agents/**`, `agent-docs/designs/2026-07-10-*`, `agent-docs/prompts/*`, `Diagnostics/gui_capture_log.md`(런타임 생성)
- 현재 마켓: **23** apps
