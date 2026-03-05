# Contexthub Apps Git Guide

이 가이드는 Contexthub Apps 프로젝트의 Git 워크플로우와 자동 릴리즈 시스템을 설명합니다.

## 1. 기본 워크플로우

프로젝트의 변경 사항을 반영할 때는 항상 다음 순서를 권장합니다.

```powershell
# 1. 변경 사항 스테이징
git add .

# 2. 커밋 메시지 작성 (예시)
git commit -m "feat: 새로운 앱 추가 및 로직 업데이트"

# 3. 원격 저장소의 최신 상태 반영 (Conflict 방지)
git pull origin main

# 4. 최종 Push
git push origin main
```

## 2. 자동 릴리즈 시스템 (GitHub Actions)

저장소에는 GitHub Actions가 설정되어 있어, 특정 변경 사항이 `main` 브랜치에 push되면 자동으로 후속 작업이 진행됩니다.

### 동작 조건
- `apps/**` 경로 내의 파일 변경이 감지될 때.
- 수동으로 Workflow를 실행할 때.

### 수행 작업
1. **패키징**: `apps/` 아래의 각 앱 폴더를 개별 `.zip` 파일로 묶습니다.
2. **레지스트리 갱신**: 각 앱의 메타데이터를 기반으로 `market.json` 파일을 업데이트하고 자동으로 커밋합니다.
3. **릴리즈 업로드**: `marketplace-latest`라는 태그 이름의 Release 섹션에 최신 `.zip` 파일들을 업로드합니다.

> [!IMPORTANT]
> GitHub Action이 `market.json`을 직접 커밋하므로, 로컬에서 작업하기 전 반드시 `git pull`을 수행하여 충돌을 방지하십시오.

## 3. 주요 파일 가이드

- `apps/`: 모든 개별 앱 코드가 들어있는 폴더입니다.
- `market.json`: 마켓플레이스 앱 목록을 담고 있는 중앙 레지스트리 파일입니다. (자동 관리됨)
- `git_push.bat`: `add`, `commit`, `pull`, `push` 과정을 자동화한 배치 파일입니다. 필요한 경우 이 파일을 실행하여 한번에 처리할 수 있습니다.

## 4. 커밋 메시지 규칙 (권장)

- `feat:` : 새로운 기능이나 앱 추가
- `fix:` : 버그 수정
- `chore:` : 빌드 시스템 수정, 문서 수정 등 단순 관리 작업
- `refactor:` : 코드 리팩토링
