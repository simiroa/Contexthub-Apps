# Apps_market 업로드 가이드 (`contexthub-apps`)

이 문서는 `C:\Users\HG_maison\Documents\Contexthub\Apps_market`를 별도 Git 리포(`contexthub-apps`)로 올릴 때,
불필요 파일을 제외하고 **앱 소스만** 관리하기 위한 기준입니다.

## 1) 업로드 원칙

- 커밋 대상: 앱 실행에 필요한 **소스/설정/리소스**
- 제외 대상: 실행 중 생성되는 **캐시/로그/모델/임시파일/빌드 산출물**
- 목표: 클론 직후 바로 빌드/실행 가능 + 리포 용량 최소화

## 2) 포함/제외 기준

포함 권장:

- `manifest.json`
- `main.py`, `*.cs`, `*.xaml`, `*.ps1`, `*.bat`, `*.cmd`
- 앱 동작에 필요한 `requirements.txt`, `pyproject.toml`, `package.json`
- 문서/아이콘/프리뷰 (`manual.md`, `icon.png`, `preview.png`)
- 앱별 정적 리소스(`resources/`, `assets/`)

제외 필수:

- Python 캐시: `__pycache__/`, `*.pyc`
- 로그: `logs/`, `*.log`
- 런타임 데이터: `userdata/`, `*.db`, `*.sqlite`
- 임시/빌드: `tmp/`, `temp/`, `dist/`, `build/`, `bin/`, `obj/`
- 가상환경: `.venv/`, `venv/`, `env/`
- 모델/허브 캐시: `hf/`, `hub/`, `blobs/`, `snapshots/`, `refs/`, `models--*/`
- 대용량 프레임/산출물: `frames/`, `outputs/`, `checkpoints/`, `weights/`

## 3) `contexthub-apps`용 `.gitignore` 템플릿

```gitignore
# OS/Editor
.DS_Store
Thumbs.db
.idea/
.vscode/

# Python
__pycache__/
*.py[cod]
*.pyo
.pytest_cache/
.mypy_cache/

# Virtual environments
.venv/
venv/
env/

# Build artifacts
bin/
obj/
build/
dist/
*.egg-info/

# Runtime/temporary
tmp/
temp/
.locks/
*.tmp

# Logs
logs/
*.log

# App runtime data
userdata/
*.db
*.sqlite

# ML/cache artifacts (필수 제외)
hf/
hub/
blobs/
snapshots/
refs/
models--*/
datasets--*/
transformers_modules/
diffusers_modules/
torch/
realesrgan/
whisper/
demucs/
BiRefNet/
ZhengPeng7/
text_encoder/
tokenizer/
unet/
vae/

# Generated media
frames/
outputs/
checkpoints/
weights/
```

## 4) 업로드 전 점검 체크리스트

1. `manifest.json` 없는 폴더는 앱으로 취급하지 않음
2. 민감정보(API 키, 개인 경로, 계정 정보) 제거
3. `requirements.txt`/의존성 파일 최신화
4. 각 앱 최소 1회 실행 확인
5. 대용량 파일(모델/캐시) 커밋 여부 최종 점검

## 5) 사전 점검 명령 (PowerShell)

```powershell
# 1) manifest 없는 디렉터리 빠르게 확인
Get-ChildItem .\Apps_market -Directory -Recurse |
  Where-Object { -not (Test-Path (Join-Path $_.FullName "manifest.json")) } |
  Select-Object -First 50 FullName

# 2) 커밋되면 안 되는 흔한 폴더 탐지
Get-ChildItem .\Apps_market -Recurse -Directory |
  Where-Object { $_.Name -in @("__pycache__","logs","userdata","hf","hub","blobs","snapshots",".venv","venv","bin","obj") } |
  Select-Object FullName

# 3) 대용량 파일(50MB+) 확인
Get-ChildItem .\Apps_market -Recurse -File |
  Where-Object { $_.Length -gt 50MB } |
  Sort-Object Length -Descending |
  Select-Object -First 100 FullName, @{N="MB";E={[math]::Round($_.Length/1MB,1)}}
```

## 6) 권장 운영 방식

- 앱 소스 리포(`contexthub-apps`)와 사용자 런타임 데이터(`userdata`, 캐시)는 분리
- 시스템 앱도 동일하게 소스만 관리하고, 업데이트는 릴리즈 ZIP 기반으로 배포
- 릴리즈에 포함할 ZIP은 `manifest.json` 루트(또는 1-depth 하위) 규칙 유지
