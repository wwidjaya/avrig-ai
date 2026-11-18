---
title: "Plan: Add SSE Streaming to Knowledge Assistant Search"
status: completed
created: 2026-11-17
author: avrig-ai
tags:
  - plan
  - backend
  - frontend
  - sse
  - knowledge-assistant
---

# Plan: Add SSE Streaming to Knowledge Assistant Search

## Objective

Add authenticated Server-Sent Events (SSE) streaming for Knowledge Assistant search so users receive an actual answer grounded in retrieved documents, followed by citations. Keep the existing JSON search API compatible.

## Implementation Phases

### Phase 1: Confirm Answer-Generation Architecture

**Assignee: be**

1. Review the existing document retrieval, reranking, and approved LLM gateway integrations.
2. Confirm the gateway path to generate an answer from retrieved passages. If no approved path exists, resolve the architecture decision before implementation.
3. Keep citations grounded in retrieved results and do not introduce a parallel answer-generation path.

### Phase 2: Define SSE Contract and Resource Limits

**Assignee: be**

1. Add only `POST /v1/documents/search/stream`. Preserve existing JSON `GET` and `POST /v1/documents/search` behavior. Do not add aliases without a concrete compatibility need.
2. Define named events and JSON payload schemas for:
   - Initial metadata, including a request/correlation ID.
   - Ordered answer text deltas.
   - Final citations and completion.
   - Terminal errors.
3. Specify event ordering and partial-answer behavior. Use normal HTTP status codes for authentication, validation, and other errors detected before the stream begins.
4. Define keepalives, request/generation/idle timeouts, and output/token limits.

### Phase 3: Implement Authenticated Backend Streaming

**Assignee: be**

1. Apply the same OIDC bearer authentication, scopes, tenant/document authorization, and rate limits as the JSON search route.
2. Retrieve and rank passages, generate an answer through the approved gateway, and emit answer deltas and final citations according to the SSE contract.
3. Propagate client disconnects to cancel retrieval and generation.
4. Avoid logging bearer tokens or sensitive prompt/context data.
5. Configure CORS to permit the UI origin, `POST`, `Authorization`, and `Content-Type`.

### Phase 4: Implement Frontend Streaming and Assistant UI

**Assignee: fe**

1. Add an authenticated `fetch`/`ReadableStream` client. Use this instead of `EventSource`, which cannot attach the existing bearer token.
2. Handle fragmented and batched SSE frames, non-2xx responses, malformed or unknown events, cancellation, and terminal errors.
3. Stream answer text incrementally and display final grounded citations. Retain the JSON search flow as a fallback and show partial-answer/error state clearly.
4. Set the heading to **Knowledge Assistant**.
5. Keep separate copy controls for the user prompt and assistant answer.
6. Render generated content as text or sanitized Markdown, and validate citation identifiers and URLs before making links clickable.

### Phase 5: Verification

**Assignee: be**

1. Test JSON compatibility, authentication and scope failures, CORS preflight, event order and payloads, pre-stream and in-stream errors, disconnect cancellation, and timeouts/output limits.
2. Run backend formatting, tests, and applicable security checks.

**Assignee: fe**

1. Test fragmented frames, multiple events per chunk, malformed/unknown events, aborts, errors, final citations, and clipboard controls.
2. Run frontend typecheck, tests, and production build.
3. Perform an authenticated browser end-to-end test of streamed answers and citations.

## Verification Criteria

- [ ] Existing JSON search routes and response behavior remain compatible.
- [ ] `POST /v1/documents/search/stream` returns authenticated SSE events with documented payloads.
- [ ] Answers are generated through the approved gateway and grounded in retrieved passages.
- [ ] Final citations correspond to retrieved results.
- [ ] Client cancellation stops backend work, and resource limits are enforced.
- [ ] Knowledge Assistant displays incremental answers, citations, and separate prompt/answer copy controls.
- [ ] Backend and frontend quality gates pass, including authenticated end-to-end verification.

## Analyst Review

The analyst reviewed the plan and recommended confirming the approved LLM gateway path before implementation, specifying a stable SSE contract, retaining the JSON fallback, preserving authorization and CORS behavior, and testing cancellation, limits, errors, safe rendering, and clipboard controls. These recommendations are incorporated above.
