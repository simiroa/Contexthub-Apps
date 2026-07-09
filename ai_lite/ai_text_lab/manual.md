# AI Text Lab (AI 텍스트 연구소)

## 소개
Gemini AI 및 Ollama 로컬 모델을 활용하여 텍스트 번역, 요약, 분석, 코드 설명 등 다양한 AI 작업을 수행하는 도구입니다.

## 주요 기능

### 내장 프리셋
| 프리셋 | 설명 |
|-------|-----|
| **번역** | 한↔영 자동 감지 번역 |
| **요약 (3줄/10줄/한 문단)** | 텍스트 핵심 요약 |
| **코드 설명** | 프로그래밍 코드 분석 및 설명 |
| **개념 단순화** | 복잡한 개념을 쉽게 풀이 |
| **SNS 포스트** | SNS용 짧은 글 생성 |
| **마케팅 카피** | 광고/마케팅 문구 작성 |
| **에이전트 지시문** | AI 에이전트용 구조화된 지시문 생성 |

## 사용법

1. 트레이/메뉴에서 **AI Text Lab** 실행
2. 텍스트 입력 (직접 입력 또는 파일 열기)
3. 프리셋 선택 또는 커스텀 프롬프트 입력
4. AI 모델 선택 (아래 "설정" 참고):
   - **Gemini**: 클라우드 API (API 키 필요)
   - **Ollama**: 로컬 모델 (설치 필요)
   - **Custom Endpoint**: OpenAI 호환 엔드포인트 (자체 API, 로컬 LLM 서버, 백그라운드 에이전트 등)
5. **실행** 버튼으로 결과 생성

## 설정
- **API 키**: Manager → Settings에서 Gemini API 키 설정
- **Ollama**: 로컬에 Ollama 설치 후 자동 감지
- **모델 전환**: 현재 UI에는 모델 선택 드롭다운이 없습니다. `ai_text_lab/config.json`의
  `settings.default_model` 값을 편집해서 전환하세요.
  - Ollama 모델명 (예: `qwen3:4b`) → 그대로 사용
  - Gemini 모델 → `✦ ` 접두사 (예: `✦ gemini-2.0-flash`)
  - Custom Endpoint → `⚡ ` 접두사 (예: `⚡ Custom Endpoint`)
- **Custom Endpoint 설정**: `ai_text_lab/config.json`의 `settings`에 아래 키를 채우세요.
  - `custom_endpoint_url`: OpenAI 호환 base URL (예: `http://localhost:11434/v1` for Ollama,
    `https://api.openai.com/v1`, 또는 자체/에이전트 서버 URL)
  - `custom_endpoint_api_key`: API 키 (필요 없으면 빈 문자열)
  - `custom_endpoint_model`: 실제로 호출할 모델명
  - 세 값을 채운 뒤 `default_model`을 `⚡ Custom Endpoint`로 바꾸면 활성화됩니다.

## 팁
- 긴 텍스트는 자동으로 청크 분할 처리됨
- 결과를 클립보드에 복사하여 다른 앱에서 사용 가능
