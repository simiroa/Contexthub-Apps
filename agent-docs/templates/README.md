# Templates

이 폴더는 새 앱 또는 새 카테고리를 만들 때 복제해서 시작하는 템플릿 모음이다.

## 포함 템플릿

- `new-app-template/`: legacy `_engine` wrapper 중심의 일반 템플릿
- `new-category-template/`: 새 카테고리를 만들 때 사용하는 최소 골격

GUI 앱은 이 폴더의 정적 템플릿보다, 가장 가까운 기존 앱과 `qt-app-builder-contexthub` 스킬 문서를 기준으로 시작하는 편이 안전하다.
특히 Qt 앱은 이 폴더를 직접 복제하지 않고, 사용자 skill 라이브러리의 `qt-app-builder-contexthub`를 우선 기준으로 본다.

## Qt Policy

- 새 PySide6 Qt 앱의 기본 시작점은 `qt-app-builder-contexthub`
- `new-app-template/`는 Qt 템플릿으로 간주하지 않음
- `new-category-template/sample_app/`도 Qt 템플릿으로 간주하지 않음
- Qt 앱은 복제 후 `manifest.json`의 `ui.framework`, `ui.shared_theme`, `ui.template`를 반드시 명시

## 사용 원칙

- 템플릿은 실제 앱이 아니다. 그대로 배포 대상에 넣지 않는다.
- 복제 후 앱 ID, 카테고리명, 스크립트 경로, 트리거, 확장자를 반드시 바꾼다.
- 아이콘 파일은 템플릿에 바이너리로 넣지 않았으므로 복제 후 `icon.png` 또는 `icon.ico`를 직접 추가한다.
- **주의**: 앱을 만들 때 `ExportRunPanel`, `PresetParameterPanel`, `ParameterControlsPanel`, `QueueManagerPanel`, `ResultInspectorPanel`, `VideoPreviewCard`와 같은 존재하지 않는 가상의 컴포넌트(phantom Cards)를 사용하거나 복제하지 않는다.

## 권장 순서

1. 가장 가까운 기존 앱과 계약 문서를 비교해 시작점 결정
   - **Market Golden Recipes**:
     - `mini`: `extract_textures`, `extract_bgm`, `cad_to_obj`
     - `compact`: `auto_lod`, `doc_convert`, `simple_normal_roughness` (`auto_lod_qt_window.py` 등)
     - `full`: `audio_toolbox`, `doc_scan`, `merge_to_exr`, `image_compare` (`upscale_qt_app.py`, `bg_removal_qt_app.py` 등)
     - `special`: `versus_up`, `qwen3_tts`
2. Qt면 skill을 먼저, non-Qt legacy wrapper면 이 폴더 템플릿을 검토
3. `manifest.json`, `main.py`, `manual.md` 수정
4. 필요 시 카테고리 `_engine`에 공통 기능 추가
5. `python .github/scripts/package_apps.py`로 검증
