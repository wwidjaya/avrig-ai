---
title: "OpenAI-Compatible JEV Intent Router"
status: completed
created: 2026-11-14
---

# OpenAI-Compatible JEV Intent Router

## Objective

Expose an OpenAI Chat Completions-compatible endpoint that uses the existing JEV decision-model client to classify a user's intent into exactly one of three categories:

- `search_knowledge_base`
- `talk_to_agents`
- `casual_greeting`

Keep intent classification separate from actually searching the knowledge base or invoking agents. This endpoint returns the decision for a downstream orchestrator to act on.

## API and model contract

- Public route: `POST /v1/chat/completions`
- Upstream: OpenCode System One, `POST https://opencode.ai/inference/systemone/v1/systemone`
- Default model: `jev-1.13`
- Authentication upstream: server-side OpenCode Console API key, never returned to clients or written to logs.
- Accept OpenAI-style `model`, `messages`, and `stream` fields. Use the latest non-empty user message as the classification state, with preceding messages available as context if the implementation supports it.
- Ask JEV one `choice` question with the three exact intent keys and explicit criteria.
- Put JSON containing `intent`, `confidence`, and the three-category probability distribution in the assistant message's `content`.
- For `stream: true`, return standard Server-Sent Events using Chat Completions chunk framing, ending with `data: [DONE]`. JEV returns a completed decision, so the SSE response streams that result after classification rather than generating tokens incrementally.
- For `stream` omitted or false, return the standard non-streaming Chat Completions envelope.

## Implementation steps

1. Inspect existing API route, middleware, response, and error conventions in `avrig-api`; confirm the existing JEV client can support a three-category choice without changing the mood endpoint. **Assignee: be**
2. Define and validate the supported OpenAI-style request fields, including message extraction, user text validation, optional model handling, and `stream`. **Assignee: be**
3. Add `POST /v1/chat/completions`, invoke JEV with the three intent categories, and serialize the result as a standard non-streaming completion whose assistant content is the agreed JSON contract. **Assignee: be**
4. Implement standard SSE chunks for `stream: true`, including role/content deltas, completion metadata, terminal finish reason, and `[DONE]`. Handle errors before streaming begins using the API's compatible error response conventions. **Assignee: be**
5. Add offline tests for the three-category request, message extraction, response JSON envelope, SSE framing, invalid requests, JEV failures, and credential-safe errors. **Assignee: be**
6. Run formatter, tests, and build checks. Do not call the live model or deploy as part of local verification. **Assignee: be**
7. Ensure the running WSL API launch path loads `OPENCODE_CONSOLE_API_KEY` from the user-only runtime environment file. Do not disclose the secret. Restart the service only with explicit approval. **Assignee: Infra**

## Out of scope

- Executing the selected intent, such as performing a knowledge-base search or launching an agent.
- Changes to the BGE reranker.
- Database schema changes.
- Production deployment or restarting a live service without approval.

