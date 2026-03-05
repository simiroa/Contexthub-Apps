# Apps Market Release Guide

`apps_market`(= `Apps_market`)를 GitHub Actions로 릴리즈/배포할 때 따라야 하는 단일 규칙 문서입니다.

## 1. 목표

- Hub 설치 시 `404`/메타 불일치/아이콘·매뉴얼 누락을 방지한다.
- `market.json` + 릴리즈 ZIP + raw 리소스(icon/manual) 경로를 항상 일치시킨다.

## 2. 현재 Hub 동작 기준 (필수 반영)

- 앱 설치 ZIP URL은 `market.json`의 `zip_url`을 그대로 사용한다.
- 아이콘은 `market.json`의 `icon_url`을 그대로 사용한다.
- 매뉴얼은 `market.json` 값이 아니라 아래 규칙으로 고정 생성된다.
  - `https://raw.githubusercontent.com/simiroa/Contexthub-Apps/main/{category}/{id}/manual.md`
- 따라서 `manual.md`는 반드시 `main` 브랜치의 앱 폴더에 존재해야 한다.

## 3. 리포 구조 규칙

- 루트:
  - `market.json`
  - 카테고리 폴더(`ai`, `ai_light`, `image`, ...)
- 앱 폴더:
  - `{category}/{app_id}/manifest.json` (필수)
  - `{category}/{app_id}/main.py` 또는 엔트리 파일 (필수)
  - `{category}/{app_id}/icon.png` 또는 `icon.ico` (강력 권장)
  - `{category}/{app_id}/manual.md` (강력 권장, 사실상 필수)

## 4. market.json 스키마 규칙

각 항목 필수 필드:

- `id`
- `name`
- `description`
- `version`
- `category`
- `zip_url`
- `icon_url`

예시:

```json
{
  "id": "ai_text_lab",
  "name": "AI Text Lab",
  "description": "Text utility",
  "version": "1.0.1",
  "category": "ai_light",
  "zip_url": "https://github.com/simiroa/Contexthub-Apps/releases/download/marketplace-latest/ai_text_lab.zip",
  "icon_url": "https://raw.githubusercontent.com/simiroa/Contexthub-Apps/main/ai_light/ai_text_lab/icon.png"
}
```

## 5. ZIP 릴리즈 규칙

- ZIP 파일명: `{id}.zip`
- ZIP 내부 구조:
  - 권장: 루트에 바로 `manifest.json` 포함
  - 허용: 1-depth 하위 폴더 안에 `manifest.json` 포함
- 금지:
  - 2-depth 이상 중첩으로 `manifest.json`을 찾기 어려운 구조
  - 앱 루트 외 런타임 캐시/로그/가상환경 포함

## 6. URL 검증 규칙 (Actions에서 실패 처리)

`zip_url`:

- `http/https` 절대 URL이어야 함
- `.zip`으로 끝나야 함
- `github.com/user/repo` 같은 플레이스홀더 문자열 금지

`icon_url`:

- raw GitHub 절대 URL 권장
- 실제 접근 시 `200` 확인

`manual`:

- `{category}/{id}/manual.md` 파일 존재 확인
- raw URL `200` 확인

## 7. GitHub Actions 권장 플로우

1. 앱 폴더 스캔 (`*/ */manifest.json`)
2. 앱별 ZIP 생성 (`{id}.zip`)
3. `marketplace-latest` 태그 릴리즈 생성/갱신 후 ZIP 업로드
4. `market.json` 생성
5. `zip_url`/`icon_url`/`manual.md` 유효성 검사
6. 검증 통과 시 `market.json`을 `main`에 반영

핵심 원칙:

- 릴리즈 ZIP 업로드가 먼저, `market.json` 공개가 나중
- 하나라도 검증 실패하면 `market.json` 배포 금지

## 8. 변경 시 주의사항

- `id` 또는 `category` 변경 시:
  - ZIP 파일명
  - `zip_url`
  - `icon_url`
  - `manual.md` 경로
  - 모두 함께 변경
- `manual.md`/`icon.png`만 바꾼 경우에도 `main` 반영이 필요 (릴리즈 ZIP만 갱신하면 반영 안 됨)

## 9. 릴리즈 전 체크리스트

- [ ] `market.json`에 placeholder URL 없음 (`user/repo`)
- [ ] 모든 `zip_url` HTTP 200
- [ ] 모든 `icon_url` HTTP 200
- [ ] 모든 `{category}/{id}/manual.md` 존재
- [ ] ZIP 내부에 `manifest.json` 존재
- [ ] `market.json`의 `id/category/version`과 앱 `manifest.json` 일치

## 10. 장애 대응 표준

- 증상: 설치 시 `404`
- 1차 확인:
  - Hub 로그의 `Downloading app bundle from ...` 실제 URL
  - 해당 URL 직접 GET
- 원인 분류:
  - `market.json` URL 오타/placeholder
  - 릴리즈 자산 누락
  - 태그(`marketplace-latest`) 갱신 실패
- 조치:
  - 잘못된 `market.json` 즉시 롤백 또는 핫픽스
  - 릴리즈 자산 재업로드 후 검증 완료 뒤 다시 배포
