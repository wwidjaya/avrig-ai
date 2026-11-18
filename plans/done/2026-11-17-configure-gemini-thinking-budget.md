---
title: "Configure Gemini 3.8 Thinking Budget and Headroom in Avrig Gateway"
status: done
date: 2026-11-17
author: Plan Agent
assignee: be
---

# Configure Gemini 3.8 Thinking Budget and Headroom in Avrig Gateway

## Objective
Prevent `gemini-3.8-flash-low` and other Gemini 3.8 models from prematurely exhausting `maxOutputTokens` on hidden reasoning tokens (which results in `finish_reason: "length"` and empty completion text) while maintaining fast responsiveness, low latency, and factual accuracy.

---

## 1. Problem Statement & Root Cause

1. **API Semantics Mismatch:**
   - In OpenAI-compatible clients (e.g. OpenCode, custom SDKs), `max_tokens` limits visible assistant text tokens.
   - In Google Gemini API, `maxOutputTokens` caps the sum of internal thinking tokens and visible output tokens.
2. **Exhaustion Behavior:**
   - `gemini-3.8-flash-low` generates 40–110 thinking tokens by default.
   - When requests specify small limits (e.g. `max_tokens: 50` or `100`), 100% of the token limit is spent on thinking before any text can be generated.
   - The stream/response terminates with `finish_reason: "length"` and an empty `content` field.
3. **Model Variant Purpose:**
   - The `-low` variant is explicitly designed for fast, low-overhead agent loops. Unbounded thinking adds latency and causes intermittent failure without adding value for standard commands and tool invocations.

---

## 2. Technical Architecture & Design

### Bounded Thinking & Headroom Allocation in `converter.rs`

Modify `to_antigravity_request` in `avrig-lib/crates/avrig-gateway/src/antigravity/converter.rs`:

1. **Model Variant Detection:**
   Check if `model` targets Gemini 3.8 with low-latency expectation:
   - Matches `gemini-3.8-flash-low` or ends with `-low`.

2. **Thinking Configuration Rule:**
   - For `-low` models:
     - If `requested_max_tokens <= 100`: set `thinkingConfig: { thinkingBudget: 0 }` to guarantee immediate text generation without truncation.
     - If `100 < requested_max_tokens <= 500`: set `thinkingConfig: { thinkingBudget: 64 }` for brief verification.
     - If `requested_max_tokens > 500` or unspecified: set `thinkingConfig: { thinkingBudget: 128 }` to preserve swift agent turnaround.
   - For non-`-low` models (e.g. `gemini-3.8-flash`, `gemini-3.8-pro`):
     - If `requested_max_tokens > 0` and `requested_max_tokens < 300`: ensure thinking tokens do not choke output by capping `thinkingBudget` to half of `requested_max_tokens` or padding `maxOutputTokens` upstream with a safety margin (e.g. +256 tokens) so the client's requested visible text limit is preserved.

3. **Pass-Through / Extensibility:**
   Ensure `generationConfig` cleanly serializes `thinkingConfig` when present:
   ```json
   {
     "maxOutputTokens": effective_max_tokens,
     "thinkingConfig": {
       "thinkingBudget": effective_budget
     }
   }
   ```

---

## 3. Implementation Steps

### Phase 1: Gateway Request Converter Update
- **Assignee:** `be`
- **File:** `avrig-lib/crates/avrig-gateway/src/antigravity/converter.rs`
- Add helper `calculate_thinking_config(model: &str, requested_max: i64) -> Option<Value>`.
- Attach `thinkingConfig` into `gen_config` in `to_antigravity_request`.
- Add unit tests in `converter.rs` verifying:
  - `-low` model with `max_tokens = 50` gets `thinkingBudget = 0`.
  - `-low` model with `max_tokens = 250` gets `thinkingBudget = 64`.
  - Standard models preserve headroom without unintended zeroing.

### Phase 2: Gateway Testing & Binary Deployment
- **Assignee:** `be`
- Run `cargo test -p avrig-gateway`.
- Build release binary: `cargo build --release -p avrig` in `avrig-api`.
- Deploy elevated copy to `D:\avrig\avrig.exe` and restart Windows service.
- Verify WSL binary build or parity if required.

### Phase 3: Live Verification
- **Assignee:** `be`
- Test `http://127.0.0.1:8000/v1/chat/completions` with `model: "agy/gemini-3.8-flash-low"` and `max_tokens: 50`. Confirm `finish_reason: "stop"` and non-empty content.
- Test reasoning prompt (*"Which number is bigger: 9.11 or 9.9?"*) to ensure factual accuracy is maintained.
- Run smoke test via OpenCode CLI.

---

## 4. Acceptance Criteria
- [ ] Requests to `gemini-3.8-flash-low` with `max_tokens: 50` return visible content and `finish_reason: "stop"` instead of premature `length`.
- [ ] No regression on tool call signature validations (`skip_thought_signature_validator`).
- [ ] Unit tests pass for thinking configuration mappings.
- [ ] Live Windows daemon service running updated binary cleanly.
