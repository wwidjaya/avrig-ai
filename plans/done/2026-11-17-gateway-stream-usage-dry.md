---
title: "Implement Stream Token Usage Across All Gateway Providers with DRY Design"
status: done
completed: 2026-11-18
date: 2026-11-17
author: Plan Agent
assignee: be
---

# Implement Stream Token Usage Across All Gateway Providers with DRY Design

## Objective
Support standard streaming token usage statistics (`usage` object in SSE chunks) for all three AI Gateway backends (Google Antigravity, ChatGPT SIWC, and Direct OpenAI / OpenCode) without repeating serialization logic or chunk construction.

---

## 1. DRY Architectural Design

To adhere strictly to DRY:
1. **Unified Data Contract (`types.rs`)**:
   - Add `pub usage: Option<OpenAIUsage>` to `ChatCompletionChunk` with `#[serde(skip_serializing_if = "Option::is_none")]`.
   - Provide a single constructor helper:
     ```rust
     impl ChatCompletionChunk {
         pub fn usage(id: &str, model: &str, usage: OpenAIUsage) -> Self {
             Self {
                 id: id.to_string(),
                 object: "chat.completion.chunk".to_string(),
                 created: chrono::Utc::now().timestamp(),
                 model: model.to_string(),
                 choices: vec![],
                 usage: Some(usage),
             }
         }
     }
     ```
   - Provide conversion on `GoogleUsage`:
     ```rust
     impl GoogleUsage {
         pub fn to_openai(&self) -> OpenAIUsage {
             OpenAIUsage {
                 prompt_tokens: self.prompt_token_count,
                 completion_tokens: self.candidates_token_count,
                 total_tokens: if self.total_token_count > 0 {
                     self.total_token_count
                 } else {
                     self.prompt_token_count + self.candidates_token_count
                 },
             }
         }
     }
     ```

2. **Decoupled Upstream Extraction**:
   - Each provider maps its own upstream usage format into `OpenAIUsage`:
     - **Google Gemini**: extracts `usageMetadata` (`promptTokenCount`, `candidatesTokenCount`, `totalTokenCount`) and calls `.to_openai()`.
     - **ChatGPT SIWC**: extracts `response.usage` (`input_tokens`, `output_tokens`) from the `response.completed` event into `OpenAIUsage`.
     - **Direct OpenAI**: `ChatCompletionChunk` now includes `usage`, allowing upstream usage chunks to pass through directly.

---

## 2. Implementation Steps

### Phase 1: Shared Type Definitions & Helpers
- **Assignee:** `be`
- **File:** `avrig-lib/crates/avrig-gateway/src/antigravity/types.rs`
- Add `pub usage: Option<OpenAIUsage>` to `ChatCompletionChunk`.
- Add `ChatCompletionChunk::usage(...)` constructor.
- Implement `to_openai(&self) -> OpenAIUsage` on `GoogleUsage`.

### Phase 2: Provider Stream Refactoring
- **Assignee:** `be`
- **File:** `avrig-lib/crates/avrig-gateway/src/client.rs`
  - In `execute_antigravity_stream`:
    - Track the latest `usageMetadata` encountered in Gemini SSE payloads.
    - When `finishReason` is encountered, emit the finish chunk followed by the `ChatCompletionChunk::usage(...)` chunk.
  - In `execute_siwc_stream`:
    - In `response.completed`, extract `usage` (`input_tokens`, `output_tokens`, `total_tokens`), emit finish chunk, and emit `ChatCompletionChunk::usage(...)` chunk.
  - In `execute_direct_provider_stream`:
    - The existing `sse_data_stream` deserializes `ChatCompletionChunk` directly, which will now automatically preserve the `usage` chunk without data loss.

### Phase 3: Build & Deployment
- **Assignee:** `be`
- Compile `avrig-api` release binary (`cargo build --release`).
- Stop `avrig` service, deploy new `avrig.exe` to `D:\avrig\avrig.exe`, restart `avrig` service.

### Phase 4: Verification
- **Assignee:** `be`
- Query the raw SSE endpoints with curl or PowerShell for all three providers (`stream = true`, `stream_options = { include_usage: true }`).
- Verify that `data: {"id":...,"choices":[],"usage":{...}}` is received right before `data: [DONE]`.
- Verify with `opencode run`.
