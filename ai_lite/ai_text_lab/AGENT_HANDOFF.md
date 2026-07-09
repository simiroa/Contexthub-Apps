# Handoff: Custom Endpoint feature (2026-07-09) — review before treating as permanent

## Why this file exists

Standing policy for the `Contexthub` main-repo agent: **this repo (`Contexthub-Apps`) is normally hands-off.** It's a separate marketplace-apps repo maintained independently; the main repo's sessions don't edit it as a matter of course.

On 2026-07-09, an exception was made at the user's explicit request, from a `Contexthub` session working on the native `media_converter` app. The user wanted `ai_text_lab` to be able to reach their own API, a local LLM, or a custom background agent, and asked for the smallest change that covered all three (see rationale below). That's the only work done here — nothing else in this repo was touched or reviewed.

**This file is the flag that policy was bent once, on purpose, for one feature.** A future session (in either repo) should read this, decide whether the feature stays, and delete this file once reviewed (whichever way the decision goes).

## What changed

Commit `f5f5429` on `main` (pushed directly, no PR — matches this repo's existing lightweight commit norm per `agent-docs/git-policy.md`, but flagging since the main-repo agent doesn't normally have standing to push here at all):

- `ai_lite/_engine/features/tools/ai_text_lab_service.py` — new `stream_custom()` method using the `openai` SDK (`OpenAI(base_url=...)`) pointed at any OpenAI-compatible `/chat/completions` endpoint.
- `ai_lite/_engine/features/tools/ai_text_lab_worker.py` — dispatches to it when `model` starts with `⚡ `.
- `ai_lite/ai_text_lab/config.json` — added `custom_endpoint_url` / `custom_endpoint_api_key` / `custom_endpoint_model` (all empty by default — inert unless configured).
- `ai_lite/_engine/features/tools/ai_text_lab_qt_app.py` — reactivated the previously-dead `settings.default_model` config field as the actual model switch. **Side effect worth knowing**: before this, `_on_run` always used a hardcoded `DEFAULT_MODEL` constant, so the app's existing Gemini path (`stream_gemini`, the `✦ ` prefix) was *also* unreachable — this fix made Gemini usable too, not just the new custom endpoint. That's a real bug fix bundled into this change, not scope creep for its own sake.
- `ai_lite/ai_text_lab/manual.md` — documented all three backends and how to switch (`default_model` prefix convention: none = Ollama, `✦ ` = Gemini, `⚡ ` = custom).

Full usage is in `manual.md`. This file only covers the decision context.

## Why this exact shape (not a bigger integration)

The user specifically asked to avoid rebuilding anything like **Hermes** — a much larger AI-agent feature (context builder, plan parser, streaming client, memory store, action executor with undo, ~62 files) that was deliberately and fully removed from the `Contexthub` main repo on 2026-07-08 as "no longer wanted" / over-engineering (see `Contexthub` repo commit `473222c`). A single generic OpenAI-compatible backend was chosen because it covers "my own API," "a local LLM," and "a background agent" with one mechanism (Ollama, LM Studio, vLLM, and a self-hosted agent gateway can all expose this same endpoint shape) — no new abstraction, no agent framework, no memory/tool-calling layer.

## What a future session should check

1. **Is this still wanted?** If the user never configures `custom_endpoint_url`, this is dead-but-harmless code. If it's been sitting unused for a while, it's a fair candidate for removal — ask before assuming either way.
2. **Does it still match `Contexthub-Apps`'s own conventions?** This was written by an agent primarily calibrated to the *other* repo's patterns (see `agent-docs/agent.md`, `agent-docs/architecture.md`, `agent-docs/new-app-guidelines.md` — those weren't consulted when this was built). Check it against this repo's actual house style, not just "does it work."
3. **`openai` SDK dependency** — confirm it's genuinely already available at the `ai_lite` category level (`ai_lite/requirements.txt`) as assumed, and that pinning/version hasn't drifted.
4. **`market.json` / release implications** — per `agent-docs/git-policy.md`, pushing to a category folder on `main` triggers the market release workflow automatically. This change already went through that path once; verify the packaged `ai_text_lab.zip` actually reflects it correctly (this wasn't independently re-verified after the automated packaging ran).

## Disposition

Pick one and delete this file when done:
- [ ] Kept as-is, reviewed against repo conventions
- [ ] Kept but revised to fit `Contexthub-Apps` house style better
- [ ] Reverted (feature removed, `default_model` reactivation optionally kept as its own bugfix — that part is arguably worth keeping independent of the custom-endpoint feature)
