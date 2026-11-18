---
status: completed
created: 2026-11-18
assignees: [analyst, tester, be, Infra]
parallel_streams: true
---

# Plan: Update Document Search Answer Model to agy/gemini-3.8-flash-low

## Goals and Objectives
Configure the Knowledge Assistant document search endpoint (`POST /v1/documents/search/stream`) to use `agy/gemini-3.8-flash-low` as the default answer model via configuration files. Ensure seamless SSE streaming answer generation through the gateway integration with robust fallback handling and test verification.

## Key Detailed Design

### Program Design
1. **Configuration Baseline:**
   - Primary configuration file: `../avrig-api/config/server.toml` (and `/opt/avrig/config/server.toml` for deployed environments).
   - Change configuration key `answer_model` under `[server]` from `"chatgpt/default"` to `"agy/gemini-3.8-flash-low"`.
   - Maintain clean fallback order:
     - `server.toml` `[server].answer_model`
     - Code default in `../avrig-api/src/main.rs` (`default_answer_model()`): `"agy/gemini-3.8-flash-low"`

2. **Backend Gateway Request Flow (`avrig-api`):**
   - In `../avrig-api/src/main.rs`:
     - `ServerConfig.answer_model` loads string `"agy/gemini-3.8-flash-low"`.
     - `AppState.answer_model` holds the resolved model identifier.
     - `build_grounded_chat_request(answer_model, query, passages)` injects model `"agy/gemini-3.8-flash-low"`.
     - `execute_search_stream` dispatches streaming chat request to `avrig_gateway::LlmProviderClient`.
     - Gateway maps prefix `agy/*` to the Antigravity backend provider and streams response chunks as SSE `answer_delta` events.

3. **Error Handling & Resilience:**
   - If upstream gateway fails or Antigravity quota/auth is unavailable, emit an informative fallback SSE `answer_delta` message (`"Knowledge Assistant answer generation is currently unavailable. See citations below for retrieved passages."`), followed by `citations` and `done` events without crashing the Axum process. Mid-stream failures emit an `event: error` followed by citations and completion.

### EDM Design
No database schema changes, table alterations, or migrations required.

## Parallel Execution Plan

| Stream | Assignee | Execution Mode | Scope |
| :--- | :--- | :--- | :--- |
| **Stream A** | `be` | Sequential (Step 1) | Update default answer model configuration in `../avrig-api/config/server.toml` and code defaults in `../avrig-api/src/main.rs`. Update affected default tests in `main.rs`. |
| **Stream B** | `tester` | Parallel (with Stream A) | Update existing assertions in `server_answer_model_defaults_and_parses_from_config` and add integration fixtures verifying `agy/gemini-3.8-flash-low` chat request construction and SSE dispatch. |
| **Stream C** | `analyst` | Parallel | Audit implementation plan and verify conformance with gateway routing standards and error-handling requirements. |
| **Stream D** | `build` | Gate (Post A/B) | Run multi-crate workspace compilation checks (`cargo check --workspace`, `cargo test`). |
| **Stream E** | `Infra` | Sequential (Final) | Deploy updated `server.toml` to target environments and restart `avrig-api` systemd service. Verify health check. |

## Test Specification and Validation Matrix

### Unit & Handler Tests (`tester`)
1. **Config Loading Test:**
   - Verify `ServerConfig::load()` parses `[server].answer_model = "agy/gemini-3.8-flash-low"`.
2. **Chat Request Generation Test:**
   - Verify `build_grounded_chat_request` outputs `ChatRequest.model == "agy/gemini-3.8-flash-low"`.
3. **SSE Streaming Flow Test:**
   - Mock gateway returning chunks for `agy/gemini-3.8-flash-low`.
   - Send `POST /v1/documents/search/stream` with valid query and bearer token.
   - Assert stream emits `event: metadata`, `event: answer_delta`, `event: citations`, and `event: done`.
4. **Gateway Failure Resilience Test:**
   - Mock gateway returning connection error or 500 error.
   - Assert `POST /v1/documents/search/stream` yields graceful error event and closes stream cleanly.

## Review Findings
Audited by `analyst`:
- Config change cleanly isolates model selection without requiring schema migrations or route interface mutations.
- The route and client contracts for `/v1/documents/search/stream` remain backwards compatible.
