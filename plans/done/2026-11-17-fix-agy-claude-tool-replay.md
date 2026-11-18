---
title: "Fix Tool Call Replay for agy/claude-opus-5-5-high"
status: completed
date: 2026-11-17
author: Plan Agent
assignee: be
---

# Fix Tool Call Replay for agy/claude-opus-5-5-high

## Objective

Make multi-turn tool calling work on `agy/claude-opus-5-5-high` without changing behaviour for Gemini models on Antigravity, for direct OpenAI-compatible providers, or for SIWC.

## Observed Evidence

- Plain chat on `agy/claude-opus-5-5-high` returns HTTP 200, so routing, credentials, model resolution, and generation are healthy.
- Replaying an assistant tool call with its matching tool result fails upstream with HTTP 400 and the message `messages.1.content.0.tool_use.id: Field required`, where index 1 is the assistant turn.
- `opencode/claude-opus-5-5` handles the same history without error, which localises the defect to the Antigravity route.
- Avrig does not construct Anthropic `tool_use` blocks. It sends Gemini-shaped `contents[].parts[].functionCall` and `functionResponse` to the internal `streamGenerateContent` endpoint, and Antigravity/Vertex translates that into the provider request.
- A previous safeguard pass added ID preservation and history validation. The live lib tree already contains a Claude branch, a typed validation error, a Claude-specific test, and an env-gated request trace, so the earlier assumption that the Claude path was untested is wrong and the remaining question is whether the deployed binary contains that branch.

## Authoritative Tree

Implementation lives in `avrig-lib/crates/avrig-gateway` (`src/antigravity/converter.rs`, `src/antigravity/types.rs`, `src/client.rs`) plus `avrig-api/src/gateway.rs`. The `avrig-ai/gateway` package is legacy for this fix and must not be edited; the two trees have already diverged in Gemini policy (the lib omits `functionCall.id` for Gemini and uses `SKIP_THOUGHT_SIGNATURE`, the legacy copy keeps the id and injects an empty signature).

This plan is authoritative for the Antigravity route. `2026-11-17-fix-claude-tool-use-id-and-stream-usage.md` and `2026-11-17-shared-provider-tool-history.md` are out of scope here; their stream-usage work is unrelated to tool-ID replay.

## Existing Implementation To Verify, Not Rebuild

The live lib tree already contains, and the plan must treat as existing:

- `is_claude_model` model classification
- typed `validate_tool_history` returning `ToolHistoryValidationError`
- a Claude branch that emits `functionCall.id`, the matching `functionResponse.id`, and omits `thoughtSignature`
- `claude_replay_preserves_function_call_and_response_ids`
- an env-gated redacted trace, `AVRIG_AGY_TRACE_REQUEST`

These change Phases 1 and 2 from construction work into characterization and regression guards. A passing Phase 1 test does not by itself prove the defect is upstream.

## User Decisions

1. A renamed or undocumented ID field is acceptable if the Antigravity translator honours it. It must be recorded as an unsupported dependency.
2. The structured fix is attempted first. Flattening historical tool interactions into plain text is a last resort only.
3. Changes must be strictly isolated to `agy/claude-*` models. Gemini on Antigravity, direct providers, and SIWC must retain their current behaviour.

## Isolation Rules (apply to every phase)

- Branch on the resolved, normalized model identifier inside the Antigravity converter only.
- Do not touch the Gemini replay path: structured `functionCall` parts and `thoughtSignature` injection stay unchanged.
- Do not alter direct-provider or SIWC paths, and do not add provider conditionals to shared stream or chunk helpers.
- Keep existing history validation: blank, duplicate, orphaned, mismatched, and unpaired IDs are still rejected before dispatch.
- Any new provider-specific field name must live behind the Claude branch, never in generic conversion code.

## Phase 0: Provenance Gate (blocking)

**Assignee: be**

1. Determine whether the deployed `D:\avrig\avrig.exe` contains the current Claude branch. The observed binary timestamp precedes the last converter modification.
2. Cheapest evidence: enable `AVRIG_AGY_TRACE_REQUEST` and observe whether a failing request carries `functionCall.id` on the wire.
3. If the deployed binary is stale, rebuild and redeploy the current lib revision, then retest the original failing scenario before any upstream contract probing.
4. Do not conclude that the translator drops the ID until the ID is demonstrably present on the wire for the failing request.

## Phase 1: Characterization Test

**Assignee: be**

1. Reproduce the real failing shape: a user turn, an assistant turn carrying `tool_calls`, and a matching `tool` result, then assert `contents[1].parts[0].functionCall.id` is non-empty and equals the supplied ID with a matching `functionResponse.id`.
2. Assert no `thoughtSignature` is injected for a Claude model, and record that this assertion may itself need revisiting if signed calls prove necessary.
3. Include a parallel-call case and assert the resulting turn structure, since the live `tool` branch currently pushes one `user` turn per tool message and does not merge consecutive results.
4. Treat this as a regression guard, not as proof that the defect is upstream.

## Phase 2: Outbound Payload Evidence

**Assignee: be**

1. Add an opt-in, environment-gated debug trace of the serialized Gemini request. Default off.
2. Redact message text and tool argument values. Retain roles, part types, field names, and IDs.
3. Reproduce the failing request once and record whether `functionCall.id` is present on the wire.
4. Treat this as the evidence that separates a local serialization defect from an upstream translation defect. Do not conclude from the upstream error string alone.

## Phase 3: Upstream Field Contract

**Assignee: be**

Enter only after the Phase 0 provenance gate passes.

1. Keep a baseline control variant that first reproduces the reported 400 in the same harness. Treat 429, any 5xx, and timeouts as aborts rather than contract verdicts, cap the total number of requests, and record every 400 response body.
2. Vary exactly one field per request, stopping at the first behavioural success:
   - `functionCall.id` (current behaviour)
   - `functionCall.callId`
   - `functionCall.toolCallId`
   - part-level id placement
   - id plus alias together
   - an Anthropic-style id format such as `toolu_...`, and a charset or length variant, since `response_tool_call_id` mints `call_<base64url>`
   - a variant attaching a `thoughtSignature` to the Claude part, since the translator may only emit a complete `tool_use` for a signed call
3. Add a negative control that must fail: a deliberately unpaired result, proving the harness exercises pairing at all.
4. Define success behaviourally. The reply must contain a sentinel drawn from the synthetic tool result, so a model that ignores history cannot be scored as a pass.
5. Repeat a winning variant three times, then re-run the baseline to prove determinism.
6. Keep all probe code in a scratch or ignored harness, never a runtime switch in the service, and never commit credentials.
7. Any renamed field is an outbound alias only. The OpenAI-facing `tool_calls[].id`, `response_tool_call_id`, signature cache keys, and `validate_tool_history` must continue to key on the client-supplied id. Add a test proving the alias does not leak into the response builder or validation.
8. Record the working variant as an undocumented dependency with the probe date, and name the exact documentation destination (vault `design/Technology-Architecture.md` plus a marked code comment).

## Phase 4: Plain-Text Fallback (conditional)

**Assignee: be**

Enter this phase only if Phase 3 finds no working structured variant.

1. Implement a pure `flatten_tool_history(&[ChatMessage]) -> Vec<ChatMessage>` applied once before the role loop, gated on the Claude family and behind an explicit switch that defaults off until verified.
2. Keep `validate_tool_history` running on the original messages, so malformed pairing still fails before dispatch.
3. Define exact rendering: delimiters, escaping for content containing the delimiter, whether fabricated text lands in the assistant or user turn, and how an assistant turn carrying both text and `tool_calls` flattens.
4. Decide and test turn merging for parallel results. The live `tool` branch generates consecutive `user` turns, so flattening must merge explicitly or justify the alternation.
5. Keep `tools` and `toolConfig` untouched so current-turn tool calling still works.
6. Log flattening at debug level with a code comment stating the trade-off: conversational continuity is preserved, structured tool-block semantics in history are not, and the model may re-request a tool it already called.
7. Tests: parallel calls, consecutive results, delimiter collision, absence of `functionCall` and `functionResponse` in flattened history, `tools` and `toolConfig` still present, malformed history still 400, and no provider conditional leaking into shared stream helpers.
8. The live check must be behavioural, requiring the sentinel from the tool result to appear in the reply, not merely HTTP 200.

## Phase 5: Verification

**Assignee: be**

1. Hermetic: the characterization test, existing Claude test, existing Gemini replay tests, existing validation tests, a golden serialized Gemini snapshot with and without tools, and a table test for `is_claude_model` (agy prefix, bare `claude-*`, uppercase, unknown family receiving neither Claude fields nor a signature).
2. Live on `agy/claude-opus-5-5-high`: plain chat, single call/result replay, two parallel calls with paired results, streaming replay, and a current-turn tool invocation. Behavioural success requires the sentinel from the tool result, not just HTTP 200.
3. Regression: `agy/gemini-*` replay still carries `thoughtSignature` and structured parts; `opencode/claude-opus-5-5` unchanged; SIWC unaffected.
4. Gates: `cargo fmt --all -- --check`, `cargo test -p avrig-gateway`, `cargo clippy --workspace --all-targets -- -D warnings`, and `cargo build -p avrig --release` in `avrig-api`. Extend the existing handler mapping test to assert the Claude-path rejection, not only an empty-call-ID case.
5. Record a scoped change list before building, since all three working trees contain unrelated modifications.

## Phase 6: Deployment

**Assignee: Infra**

1. Only after Phase 5 passes and the scoped change list is recorded. A release built from the current dirty trees would bundle unrelated work, so build from a scoped state or a dedicated worktree, and state which files were included.
2. Elevated `Stop-Service avrig -Force`, timestamped backup of `D:\avrig\avrig.exe`, copy the verified artifact, `Start-Service`, then verify.
3. Post-deploy checks beyond HTTP 200: `/v1/health` returns 200 with the expected provider list and account counts, `/v1/models` includes `agy/claude-opus-5-5-high`, and `D:\avrig\logs\avrig.log` shows a clean start with no Antigravity rejection lines.
4. Rollback criteria and procedure: health failure, chat returning non-200, replay still returning 400, or new startup errors means restore the backup, restart, and re-verify.
5. Record the deliberate Windows-only skew. Windows binds `0.0.0.0:8000` and WSL runs a separate instance on `127.0.0.1:8000`. The WSL `/opt/avrig` rebuild is out of scope unless explicitly requested.

## Resolution

### Phase 0 verdict: stale binary, not an upstream contract defect

The deployed `D:\avrig\avrig.exe` was written at 15:08:50 while the Claude branch in `avrig-lib/crates/avrig-gateway/src/antigravity/converter.rs` was written at 15:29:05. The binary under test predated the fix it was being blamed for. Rebuilding `avrig-api` and redeploying resolved the reported `tool_use.id: Field required` failure on the first retest, so Phases 3 and 4 were never needed and no upstream probing was performed.

### Phase 1 and Phase 2: confirmed as existing

`is_claude_model`, typed `validate_tool_history` with `ToolHistoryValidationError`, the Claude branch emitting `functionCall.id` and the matching `functionResponse.id` with no `thoughtSignature`, the `claude_replay_preserves_function_call_and_response_ids` test, and the env-gated `AVRIG_AGY_TRACE_REQUEST` trace were all already present in the live lib tree. They were verified, not rebuilt.

### Defects fixed

1. Consecutive Claude tool results were emitted as separate `user` turns, which breaks Anthropic turn alternation for parallel calls. They are now merged into one `user` turn, covered by `claude_parallel_results_merge_into_one_user_turn` and `claude_result_merge_stops_at_a_text_turn`.
2. A completed response carrying tool calls reported `finish_reason: "stop"`, which makes a client treat a tool turn as a final answer and stops the tool loop. The non-stream path now uses `resolved_finish_reason`, returning `tool_calls` whenever the response contains tool calls, and the Antigravity streaming path applies the same rule. Covered by `tool_turn_reports_tool_calls_finish_reason`.

### Live evidence on `agy/claude-opus-5-5-high`

- Single call plus matching result replay returned the sentinel `sentinel-XY7`, later `sentinel-FR9`.
- Two parallel calls with paired results returned `value-alpha,value-bravo`.
- Streaming replay emitted content, a usage trailer under `stream_options.include_usage`, then `[DONE]`.
- A current-turn tool invocation now returns `finish_reason: "tool_calls"` instead of `"stop"`.
- Regression: `agy/gemini-3.8-flash-high` replay kept structured parts and `thoughtSignature` and returned its sentinel; `opencode/claude-opus-5-5` replay returned its sentinel.

### Gates

`cargo test -p avrig-gateway` passed 35 tests, `cargo fmt --all -- --check` is clean, and `cargo build -p avrig --release` succeeded. `cargo clippy -p avrig-gateway --all-targets` reports only pre-existing `collapsible_if` findings in untouched code; `-D warnings` therefore fails on this tree and is recorded as pre-existing debt, not a regression from this work.

### Deployment record

- Artifact `avrig-api/target/release/avrig.exe` deployed to `D:\avrig\avrig.exe`, SHA-256 `EC22A0B2FCC52382B68ED5C19B0CE73EB74D9B496959CCD29C17B5BB3A8F2A4D`, source and target hashes equal.
- Backups: `D:\avrig\avrig.exe.20261117-160239.bak`, `D:\avrig\avrig.exe.20261117-160927.bak`, `D:\avrig\avrig.exe.20261117-161259.bak`.
- Service `avrig` Running, `/v1/health` 200, `/v1/models` lists `agy/claude-opus-5-5-high`, and the log shows a clean start with no Antigravity rejection lines.
- Windows only. The WSL `/opt/avrig` instance on `127.0.0.1:8000` was not rebuilt and remains at the older revision by decision.

### Remaining follow-up

The streaming `finish_reason` correction exists in source but is not in the deployed binary, because `avrig-api/src/main.rs` was under concurrent edit (an `AppState` initializer missing `search_candidates`) at deploy time and the release build no longer compiles. Rebuild and redeploy once that tree settles, then repeat the streaming tool-invocation check.

### Lesson recorded

A reported upstream contract error is not evidence of an upstream defect until the deployed binary is proven to contain the current source. Compare the binary timestamp and hash against the source revision first, and rebuild and redeploy before probing a third-party endpoint.

## Acceptance Criteria

- The deployed binary under test is proven to contain the Claude branch before any upstream contract conclusion is drawn.
- Multi-turn tool replay on `agy/claude-opus-5-5-high` succeeds through the gateway with behavioural evidence.
- Gemini on Antigravity, direct providers, and SIWC behave exactly as before, proven by unchanged tests plus live regression checks.
- The Claude-path behaviour is either a documented field variant or a documented plain-text fallback behind an explicit switch, not an unexplained workaround.
- Malformed tool histories still fail fast with HTTP 400 before upstream dispatch.
- The deployed binary is verified by hash, service status, health payload, model list, and a clean log scan, with rollback criteria defined.
