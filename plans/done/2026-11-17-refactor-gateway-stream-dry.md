---
title: "Refactor Avrig Gateway SSE Streaming to Enforce DRY"
status: planned
date: 2026-11-17
author: Plan Agent
assignee: be
---

# Refactor Avrig Gateway SSE Streaming to Enforce DRY

## Overview
Currently, the SSE stream handling in `avrig-lib/crates/avrig-gateway/src/client.rs` has duplicated TCP packet/line buffering logic across `execute_siwc_stream`, `execute_direct_provider_stream`, and `execute_antigravity_stream`. Noticeably, `execute_antigravity_stream` was still using unbuffered `text.lines()`, which leaves it vulnerable to chopped packet drops under high-latency or chunk-split conditions.

This plan refactors the low-level SSE stream framing into a single, shared helper stream abstraction (`sse_data_stream`), eliminating code duplication across Google Antigravity, ChatGPT SIWC, and Direct OpenAI providers while ensuring consistent packet buffering.

---

## Identified Duplications (DRY Violations)

1. **SSE Line Buffering & Event Extraction**:
   - `execute_siwc_stream` and `execute_direct_provider_stream` duplicate the `buffer.push_str(&text)` + `buffer.drain(..=newline_pos)` loop.
   - `execute_antigravity_stream` lacks proper line buffering, relying on `text.lines()`.
2. **Chunk Construction Boilerplate**:
   - Initial chunk creation (`role: "assistant"`, empty content, `finish_reason: None`) and finish chunk creation (`role: None`, `finish_reason: Some("stop")`) are manually assembled in multiple places.
3. **Upstream HTTP Status Validation**:
   - `!resp.status().is_success()` error text extraction and formatting is repeated across direct, Antigravity, and SIWC calls.

---

## Action Plan

### Phase 1: Shared SSE Framing Stream
- **Assignee:** `be`
- **File:** `avrig-lib/crates/avrig-gateway/src/client.rs` (or a dedicated `stream.rs` submodule)
- Create a reusable stream transformer:
  ```rust
  pub fn sse_data_stream<S>(byte_stream: S) -> impl Stream<Item = Result<String>>
  where
      S: Stream<Item = Result<bytes::Bytes, reqwest::Error>> + Send + 'static
  ```
  - Accumulates incoming raw bytes into an internal buffer.
  - Drains complete lines at `\n`.
  - Filters and strips `data: ` prefixes.
  - Skips empty lines and `[DONE]`.
  - Emits pure, complete SSE data payloads (`String`).

### Phase 2: Refactor Provider Streaming Handlers
- **Assignee:** `be`
- Refactor the three stream functions to consume `sse_data_stream`:
  1. `execute_antigravity_stream`:
     - Feed the Gemini byte stream through `sse_data_stream`.
     - Deserialize Gemini response JSON from complete SSE lines.
     - Eliminate packet-boundary issues on Antigravity streams.
  2. `execute_siwc_stream`:
     - Feed SIWC byte stream through `sse_data_stream`.
     - Parse `response.output_text.delta` and `response.completed`.
  3. `execute_direct_provider_stream`:
     - Feed Direct OpenAI byte stream through `sse_data_stream`.
     - Directly deserialize `ChatCompletionChunk`.

### Phase 3: Shared Chunk Builders
- **Assignee:** `be`
- Create helper constructors on `ChatCompletionChunk`:
  - `ChatCompletionChunk::initial_role(id: &str, model: &str, role: &str) -> Self`
  - `ChatCompletionChunk::text_delta(id: &str, model: &str, text: &str) -> Self`
  - `ChatCompletionChunk::finish(id: &str, model: &str, reason: &str) -> Self`

### Phase 4: Verification and Smoke Testing
- **Assignee:** `be`
- Rebuild `avrig-api` with `cargo build --release`.
- Deploy the updated binary to `D:\avrig\avrig.exe` and restart service `avrig`.
- Execute verification runs with all three providers:
  - `opencode run --model avrig/chatgpt/gpt-6-luna "Say: 'Hello World'"`
  - `opencode run --model avrig/opencode/gpt-5.6-luna "Say: 'Hello World'"`
  - `opencode run --model avrig/agy/gemini-2.5-flash "Say: 'Hello World'"`
