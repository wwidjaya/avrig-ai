---
title: "Fix Claude Tool Use IDs and Stream Usage Consistency"
status: superseded
date: 2026-11-17
author: Plan Agent
assignee: be
---

# Fix Claude Tool Use IDs and Stream Usage Consistency

> Superseded on 2026-11-17 by `2026-11-17-fix-agy-claude-tool-replay.md`, which is authoritative for the Antigravity Claude route. The reported rejection was caused by a stale deployed binary, not by a missing upstream ID contract. The stream-usage work described here is unrelated and remains open.

## Objective

Fix the Claude Opus 5.5 upstream rejection:

`messages.5.content.0.tool_use.id: Field required`

by preserving or safely normalizing tool-call IDs across OpenAI-compatible request history, then add regression tests. Also implement the pending stream-usage recommendations: retain the completion ID on the usage trailer and emit usage only when requested with `stream_options.include_usage`.

## Scope and Relevant Components

- `avrig-lib/crates/avrig-gateway/src/antigravity/types.rs`: OpenAI-compatible `ChatMessage`, `ToolCall`, and `ChatRequest` types.
- `avrig-lib/crates/avrig-gateway/src/client.rs`: shared SSE stream handling, Antigravity and SIWC usage conversion, and direct-provider pass-through.
- `avrig-lib/crates/avrig-gateway/src/siwc/client.rs`: SIWC conversion from chat messages to Responses API input, including assistant function calls and function-call outputs.
- Relevant `avrig-api` gateway handler only if request normalization or stream options are applied at the API boundary.

## Phase 1: Trace the Claude Failure and Define the Invariant

**Assignee: be**

1. Trace the configured `claude-opus-5.5` model route to its upstream provider and identify the exact conversion path that creates the reported Anthropic `messages` payload.
2. Inspect how assistant tool-call messages are deserialized, transformed, and replayed, including tool responses and multi-turn history.
3. Confirm whether the request representation entering this project is OpenAI Chat Completions, Anthropic Messages, or another format. Record the exact boundary where `messages.5.content.0.tool_use.id` is constructed.
4. Establish the invariant: every serialized assistant `tool_use` block must have a provider-valid, non-empty ID, and each corresponding tool result must reference that same ID.
5. Confirm whether the ID is absent in incoming history or dropped during provider conversion.
6. If this repository does not construct the reported Anthropic payload, identify the owning component, document the evidence and exact handoff location, then revise the plan's scope, files, and assignee to route the fix to that owner before implementation. Do not proceed with unrelated gateway changes. Keep the independent stream-usage work in scope only if its avrig-gateway ownership is confirmed.

## Phase 2: Repair Tool-Call ID Preservation and Validation

**Assignee: be**

1. Correct the narrow conversion defect identified in Phase 1 and preserve valid IDs unchanged end-to-end.
2. Validate IDs at the request-conversion boundary: presence, non-emptiness, uniqueness in the relevant history, and one-to-one pairing between tool calls and results.
3. Reject malformed history with a clear client error before the upstream request, including missing/empty IDs, duplicate IDs, orphaned results, and unmatched calls. Only use normalization if the source format provides enough information to update both the call ID and every paired result ID atomically and unambiguously.
4. Ensure serialization cannot produce an Anthropic `tool_use` without a valid ID.
5. Keep provider-specific conversion isolated from unrelated stream-usage code and avoid duplicating tool-call conversion logic.

## Phase 3: Stream Usage Recommendations

**Assignee: be**

1. Define one API contract for all providers: emit usage only when `stream_options.include_usage` is explicitly `true`; treat absent and explicitly false as disabled. Apply the same filter to direct-provider upstream usage chunks rather than passing them through unconditionally.
2. Reuse the same completion ID for ordinary chunks and the trailing usage chunk in Antigravity and SIWC streams. Pass the established ID into `latest_usage_stream` instead of generating an independent ID.
3. Ensure at most one usage chunk is emitted. For Antigravity and SIWC, retain the latest valid upstream usage event and emit one trailer after the final choice chunk. For direct providers, filter duplicate usage chunks according to a documented policy and preserve the final valid usage value only when requested.
4. Verify ordering remains: final choice chunk, optional `choices: []` usage chunk, then `[DONE]`.
5. Keep usage extraction, filtering, and trailer construction shared where possible; do not add provider-specific duplicate trailer logic.

## Phase 4: Automated Regression Tests

**Assignee: be**

Add focused tests using existing project test conventions:

1. **Tool IDs**
   - Deserialize and convert a multi-turn assistant tool call with a valid ID, followed by a matching tool result.
   - Assert the ID survives conversion into the upstream tool-use representation and the result references that ID.
   - Cover missing/empty IDs, duplicate IDs, orphaned tool results, and unmatched calls, asserting clear client errors before upstream dispatch.
   - Cover multiple calls in one assistant message, ensuring unique IDs and correct result pairing.
2. **Usage stream**
   - Assert ordinary chunks and the usage trailer share the same completion ID.
   - Assert `include_usage: true` emits at most one usage trailer immediately before `[DONE]`, even when upstream sends zero, one, or multiple usage events.
   - Assert absent and explicitly false `include_usage` do not emit a usage trailer for any provider, including direct-provider upstream chunks.
   - Assert missing upstream usage does not fabricate a zero-valued usage chunk.
3. Use mocked upstream payloads or pure conversion/helper tests. Tests must not require live provider credentials.

## Phase 5: Verification

**Assignee: be**

1. From `avrig-lib`, run `cargo fmt --all -- --check`, `cargo test -p avrig-gateway`, `cargo test --workspace`, `cargo clippy --workspace --all-targets -- -D warnings`, and `cargo build --workspace --release`. Record any pre-existing lint baseline separately rather than suppressing new warnings.
2. Keep the Claude Opus 5.5 multi-turn tool-use scenario manual and optional when credentials or access are unavailable. It supplements, but does not replace, hermetic automated tests.
3. Exercise mocked stream usage enabled and disabled for SIWC, Antigravity, and direct providers; confirm completion-ID consistency, single-trailer behavior, and SSE event order.
4. Report test/build outcomes and provider-specific limitations. Deployment or service restart is out of scope unless separately authorized.

## Acceptance Criteria

- Claude Opus 5.5 no longer receives an assistant `tool_use` without a valid ID for well-formed client history.
- Invalid/missing IDs are handled deterministically without breaking tool-result pairing. Duplicate IDs, orphaned results, and unmatched calls fail before upstream dispatch with a clear client error.
- Automated tests cover valid IDs, malformed histories, multiple tool calls, and matching results.
- SIWC and Antigravity usage trailers reuse the stream completion ID.
- Across all providers, the usage trailer is emitted only when explicitly requested, appears at most once, and precedes `[DONE]`.
- Tests and release build pass without introducing duplicate provider-specific usage handling.
