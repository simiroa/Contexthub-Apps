# Qt App Builder Skill Review Plan

## Purpose

이 문서는 `qt-app-builder-contexthub` 스킬이 실제 `Contexthub-Apps`의 현재 Qt 규약을 제대로 반영하는지 검토하기 위한 사례 기반 계획이다.

검토 목적은 두 가지다.

1. 스킬이 4개 템플릿 `mini / compact / full / special`을 올바르게 선택하는지 확인
2. 스킬이 shared runtime 계약, 헤더 규칙, grip 규칙, 테마 토큰 규칙을 빠뜨리지 않는지 확인

## Reference Apps

스킬 검토는 아래 5개 앱을 기준 사례로 삼는다.

| Template | App | Why |
| --- | --- | --- |
| `mini` | `normal_flip_green` | confirm shell 성격의 작은 단일 작업 mini 사례 |
| `compact` | `pdf_merge` | 배치형처럼 보여도 실제로는 짧은 옵션과 단순 실행 중심인 compact 사례 |
| `full` | `video_convert` | preview/list/parameter/output이 분리된 full 사례 |
| `full` baseline | `resize_power_of_2` | full bucket의 비교적 안정적인 기준 샘플 |
| `special` | `versus_up` | bespoke workspace 구조지만 공통 header/theme를 유지해야 하는 special 사례 |

## Review Questions

각 사례에 대해 아래 질문을 확인한다.

1. 스킬이 올바른 `ui.template`를 고르는가
2. `ui.framework = pyside6`, `ui.shared_theme = contexthub`, `ui.template`를 항상 명시하는가
3. 헤더를 앱 이름 + 아이콘 버튼으로만 제한하는가
4. `mini`를 제외한 모든 템플릿에서 `attach_size_grip()`를 넣는가
5. raw hex / `rgb()` / `rgba()` 로컬 스타일을 금지하는가
6. scroll body/viewport 빈 영역을 `surfaceRole="content"` 규칙으로 다루는가
7. `special`을 레이아웃 예외로만 다루고, 테마 예외로 취급하지 않는가
8. 앱을 앱 단위 복제보다 표준 컴포넌트 조합으로 설명하는가
9. queue 중심 앱에서 `QueueManagerCard` 같은 더 적합한 관리형 컴포넌트를 고르는가
10. 결과 검사형 앱에서 `ResultInspectorCard`나 도메인 프리뷰 카드를 적절히 선택하는가

## Scenario Prompts

스킬 검토는 아래 프롬프트 세트로 수행한다.

### 1. Mini Prompt

`선택된 normal map 이미지들의 green 채널만 뒤집는 작은 Qt 앱을 새로 만든다. 확인 후 바로 실행되는 mini 앱으로 시작한다.`

기대 결과:

- `mini` 선택
- grip 없음
- 짧은 body
- console handoff 또는 small CTA 중심 구조

### 2. Compact Prompt

`여러 PDF를 받아도 큰 workspace 없이 병합 순서와 짧은 출력 옵션만 확인하고 바로 실행하는 compact Qt 앱을 만든다. preview나 list는 많아야 하나만 있어야 한다.`

기대 결과:

- `compact` 선택
- one-column flow
- non-mini grip
- options와 execution이 과도하게 분리되지 않음

### 3. Full Prompt

`비디오 파일 리스트, preview, 파라미터, 실행 영역이 함께 있는 full Qt 변환 앱을 만든다.`

기대 결과:

- `full` 선택
- splitter 또는 multi-panel 구조
- `PreviewListPanel`, `FixedParameterPanel`, `ExportRunPanel` 사용 후보 제시

### 4. Special Prompt

`제품 비교용 matrix/workspace 앱을 만든다. 상호작용은 특수하지만 공통 테마와 헤더 규칙은 유지해야 한다.`

기대 결과:

- `special` 선택
- bespoke workspace 허용
- header/theme/grip 계약 유지

## Review Procedure

1. 스킬을 명시적으로 호출해 각 시나리오에 대한 생성 계획을 받는다.
2. 계획 안에 아래 항목이 모두 있는지 확인한다.
   - 선택 템플릿
   - 대상 카테고리
   - 생성 파일 목록
   - `_engine` 재사용 여부
   - manifest 필수값
   - 적용할 shared runtime 규칙
   - 선택한 표준 컴포넌트 목록
   - 검증 명령
3. 결과를 위 기준 사례 앱과 비교한다.
4. mismatch가 있으면 아래 분류로 기록한다.
   - template misclassification
   - shared runtime omission
   - header/grip rule omission
   - theme contract drift
   - overly generic output
   - missing domain component selection
5. 결과 기록은 `agent-docs/qt-app-builder-review-log-template.md` 형식으로 남긴다.

## Acceptance Criteria

스킬은 아래를 만족해야 통과로 본다.

- 네 가지 템플릿 시나리오 모두 올바른 bucket을 선택한다.
- `pyside6 / contexthub / ui.template`를 항상 빠뜨리지 않는다.
- `mini`를 제외한 템플릿에 grip 규칙을 포함한다.
- 헤더에 subtitle/open/runtime badge를 기본값으로 넣지 않는다.
- 색 규칙을 shared runtime 기반으로 설명하고 raw color를 허용하지 않는다.
- `special`을 별도 테마로 오해하지 않는다.

## Follow-up If It Fails

실패 유형별 조정 방향은 다음으로 고정한다.

- template 오판: `references/template-selection.md` 수정
- 공통 shell 누락: `references/runtime-deps.md`와 템플릿 skeleton 수정
- 헤더/grip 누락: `references/theme-contract.md` 수정
- 출력이 너무 일반적임: `SKILL.md`의 output contract 강화
- validation 누락: `references/validation-checklist.md` 강화
