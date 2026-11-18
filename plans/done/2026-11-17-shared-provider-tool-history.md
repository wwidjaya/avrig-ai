---
title: "Design Shared and Provider-Specific Tool History Handling"
status: superseded
date: 2026-11-17
author: Plan Agent
assignee: be
---

# Design Shared and Provider-Specific Tool History Handling

> Superseded on 2026-11-17 by `2026-11-17-fix-agy-claude-tool-replay.md`, which is authoritative for the Antigravity Claude route. Shared provider-neutral history validation already exists in `avrig-lib/crates/avrig-gateway` and no longer needs a separate design pass for this defect.

## Objective

Prevent missing or mismatched tool-call IDs across supported models by sharing provider-neutral history validation while keeping OpenAI and Anthropic request serialization provider-specific.

The reported Claude error is:

`messages.5.content.0.tool_use.id: Field required`

The Avrig gateway appears to pass OpenAI-compatible requests through. Confirm the actual request conversion owner before making implementation changes. If conversion occurs in an external OpenCode inference service, route the implementation there rather than adding provider-specific request rewriting to the gateway.

## Component Boundaries

### Shared, provider-neutral responsibilities

- Parse and normalize the incoming chat history into an internal tool interaction representation.
- Preserve valid call IDs unchanged.
- Validate that call IDs are non-empty and unique within the relevant conversation.
- Validate that every result refers to exactly one preceding call and that a call is matched by at most one result.
- Reject malformed history before provider dispatch when safe repair is not possible.
- Keep provider-independent validation errors and policies in one place.

### OpenAI-specific serialization

- Serialize assistant tool calls in OpenAI Chat Completions format, including `tool_calls[].id`.
- Serialize tool responses with the matching `tool_call_id`.
- Do not place Anthropic content-block fields in OpenAI payloads.

### Anthropic-specific serialization

- Serialize assistant calls as Anthropic `tool_use` blocks with IDs.
- Serialize matching results as Anthropic `tool_result` blocks with the corresponding `tool_use_id`.
- Follow Anthropic's required ordering and content-block shape.
- Do not map OpenAI-only wire fields directly into Anthropic payloads.

## Phase 1: Trace Ownership and Protocol Requirements

**Assignee: be**

1. Trace chat history from the gateway/API boundary through model routing to the final OpenAI or Anthropic request body.
2. Identify the exact component that constructs Anthropic Messages payloads and the component that constructs OpenAI Chat Completions payloads.
3. Record repository paths, conversion functions, supported provider/API versions, and existing test harnesses.
4. Verify protocol requirements from the owning provider's documentation for incomplete assistant tool-call turns, result ordering, and ID uniqueness. Record source links/version and map each requirement to its exact serialization boundary.
5. If payload construction is outside the available repositories, document the evidence and provide an actionable handoff to the owning repository/service. Do not implement a workaround in a pass-through gateway.

## Phase 2: Specify Shared History Invariants

**Assignee: be**

1. Define an internal provider-neutral representation for assistant tool calls and tool results, reusing existing domain types where suitable.
2. Preserve valid IDs exactly.
3. Require IDs to be present, non-empty, and unique across the entire request history by default. If an identified provider/API version requires a different scope, document that authoritative requirement and enforce it only in that provider's adapter.
4. Require each tool result to reference exactly one earlier call in normalized history; reject orphaned results, duplicate results for a call, and ambiguous pairings. A result may not precede its call.
5. Define ordering separately for normalized history and provider serialization. Preserve logical call/result order in shared history; each adapter must serialize multiple calls and results according to its verified protocol requirements.
6. Reject unmatched calls at the end of history by default. Permit them only if the identified provider/API version explicitly allows that exact terminal position and representation; document the source and test preservation or rejection.
7. Reject missing, empty, or duplicate IDs by default. Do not repair ambiguous or duplicate identities. Any exceptional repair must have a deterministic documented rule that proves all references are updated atomically, with dedicated tests; otherwise return a clear validation error before dispatch.

## Phase 3: Implement Shared Validation and Separate Serializers

**Assignee: be**

1. Implement shared validation at the provider request-conversion boundary, before network dispatch.
2. Keep OpenAI Chat Completions serialization separate from Anthropic Messages serialization.
3. Ensure both serializers consume the validated internal representation and preserve ID pairing.
4. Avoid duplicating validation rules between serializers or adding Anthropic-specific behavior to generic pass-through paths.
5. Keep changes scoped to the confirmed owner of request serialization.

## Phase 4: Hermetic Tests

**Assignee: be**

1. Shared validator tests:
   - Valid single and multi-turn tool interactions.
   - Preservation of valid IDs exactly.
   - Multiple calls in one assistant turn with correctly paired results and provider-compliant ordering.
   - Missing, empty, and duplicate call IDs.
   - Orphaned results, duplicate results, results preceding calls, ambiguous pairing, and calls/results interleaved across turns.
   - Unmatched calls at end of history, including any explicitly supported exception verified against the provider/API version.
2. OpenAI serializer tests:
   - Assert assistant `tool_calls[].id` and matching tool-message `tool_call_id`.
   - Assert multi-call ordering follows the verified OpenAI API contract.
3. Anthropic serializer tests:
   - Assert `tool_use.id`, matching `tool_result.tool_use_id`, expected ordering, and payload shape.
   - Assert multi-call ordering follows the verified Anthropic API contract.
4. Assert malformed history fails before any provider request is sent.
   - Use a mock dispatch boundary and assert its call count remains zero after validation failure.
5. Tests must not require network access, provider credentials, or live model calls.

## Phase 5: Verification and Handoff

**Assignee: be**

1. Run the owning component's formatting, focused tests, full relevant test suite, lint, and build checks.
2. Keep a live Claude multi-turn tool-use test optional; it supplements hermetic tests and must not be required when credentials are unavailable.
3. If the owner is external, provide a concise handoff with the failing request shape, conversion trace, required invariants, and proposed regression cases.
4. Do not deploy, restart services, or alter production configuration without separate authorization.

## Acceptance Criteria

- Ownership of both provider serialization paths is established before implementation.
- Shared validation applies identical ID and pairing invariants across providers.
- OpenAI and Anthropic payloads use their respective wire formats while preserving the same logical call/result IDs.
- Malformed histories fail clearly before provider dispatch.
- Hermetic tests cover valid and malformed histories and assert both serialized payload formats.
- If the serializer is external, an actionable handoff is produced instead of an ineffective gateway workaround.
