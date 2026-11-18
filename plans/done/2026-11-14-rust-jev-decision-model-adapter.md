---
title: "Rust JEV Decision-Model Adapter"
status: done
created: 2026-11-14
completed: 2026-11-15
---

# Rust JEV Decision-Model Adapter

## Objective

Implement the Rust equivalent of the Go decision-model adapter described in the Vault note `03-knowledge/AI/models/Decision-Model-and-Reranker-Implementation-in-Go.md`.

Use the OpenCode Console System One API, keeping the decision model separate from the existing BGE reranker.

## Confirmed API contract

- Method: `POST`
- Endpoint: `https://opencode.ai/inference/systemone/v1/systemone`
- Default model ID: `jev-1.13`
- Authentication: OpenCode Console API key as a Bearer token, supplied through server-side configuration.
- Request uses System One fields: `model`, `state`, and `questions`.
- Do not use `/v1/chat/completions` for JEV.
- `jev-1.13-free` may be supported as a configurable alternative, but its availability must be checked before relying on it.

Source: OpenCode Console Models documentation, https://opencode.ai/v2/docs/console/models/

## Implementation steps

1. Review Rust service structure and local conventions. Identify module placement, configuration patterns, and the API integration point. **Assignee: be**
2. Define typed Rust request and response structures for System One, including model, state, typed questions, answers, choices, probabilities, and confidence as applicable. **Assignee: be**
3. Implement the HTTP client using the confirmed endpoint. Configure model and API key outside source code, reuse the client, apply a timeout, propagate request cancellation, and handle upstream errors safely. **Assignee: be**
4. Construct the six-mood choice request using the canonical keys and criteria from the Vault note: `calm`, `dark`, `energetic`, `melancholy`, `quirky`, and `romantic`. **Assignee: be**
5. Validate the response contains the expected answer and usable probabilities. Return all six mood keys and round values to four decimal places, with explicit handling for absent or invalid values. **Assignee: be**
6. Add tests for request serialization, response parsing, normalization, missing fields, and upstream failures. Tests should not require a live API key. **Assignee: be**
7. Run formatting, tests, and build checks. Report required configuration and whether a live endpoint check was performed. **Assignee: be**

## Out of scope

- Changes to the BGE reranker.
- Database schema or migration changes.
- Deployment or live service configuration changes unless separately authorized.
