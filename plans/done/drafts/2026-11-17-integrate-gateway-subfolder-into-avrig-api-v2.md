---
title: "Plan: Integrate AI Gateway Subfolder Capabilities into avrig-api"
status: planned
created: 2026-11-17
author: avrig-ai
tags:
  - plan
  - backend
  - axum
  - gateway
  - antigravity
  - siwc
  - chatgpt
  - routing
---

# Plan: Integrate AI Gateway Subfolder Capabilities into avrig-api

## 1. Objective

Integrate the unified AI Gateway capabilities (Google Antigravity OAuth and ChatGPT SIWC proxy) currently located in `avrig-ai/gateway` into the central `avrig-api` Axum server runtime under a dedicated subfolder/namespaced route prefix (`/api/v1/gateway/...`), managed via an optional node role (`gateway`).

This consolidates AI gateway routing into the production `avrig-api` daemon while preserving clean namespacing, independent configuration, and existing KM document/intent endpoints.

---

## 2. Architecture & Design

### A. Subfolder Route Layout
The gateway capabilities will be mounted under the `/api/v1/gateway` prefix:
- `GET  /api/v1/gateway/health` : Health and upstream provider connection status (Google Antigravity, OpenAI SIWC).
- `GET  /api/v1/gateway/v1/models` : Unified models list (prefixed models: `agy/*`, `chatgpt/*`).
- `GET  /api/v1/gateway/v1/quota` : Google Antigravity quota and project tier details.
- `POST /api/v1/gateway/v1/chat/completions` : Streaming (SSE) and non-streaming completions dispatcher routing across Antigravity and SIWC ChatGPT upstream adapters.

### B. Module Structure in `avrig-api`
Port and organize the gateway components directly into `avrig-api/src/gateway/`:
- `src/gateway/mod.rs` : Gateway module root, configuration types, and router builder.
- `src/gateway/server.rs` : Request handlers (`handle_chat_completions`, `handle_models`, `handle_quota`, `handle_health`) and model resolver.
- `src/gateway/antigravity/` : Google Antigravity OAuth token management, prompt converter, and Cloud Code client.
- `src/gateway/siwc/` : ChatGPT Sign-in-with-ChatGPT OAuth client, token refresh, and streaming HTTP client.

### C. Node Role & Configuration
Add `gateway` as an optional role in `[node] roles`:
```toml
# config/node.toml or config.toml
[node]
roles = ["server", "gateway"]

# config/gateway.toml
[gateway]
enabled = true
mount_prefix = "/api/v1/gateway"
antigravity_credentials = "config/antigravity.json"
chatgpt_credentials = "config/chatgpt.json"
local_only = true
```

---

## 3. Implementation Phases & Subagent Assignments

### Phase 1: Dependency Audit & Module Staging
**Assignee: be**
1. Audit `avrig-api/Cargo.toml` for required gateway dependencies (`reqwest` with stream/blocking, `tiny_http` if needed, `sha2`, `base64`, `rand`, `tokio-stream`, `futures-util`).
2. Add necessary crates to `avrig-api/Cargo.toml` matching workspace versions.
3. Stage `src/gateway/` in `avrig-api`, porting `antigravity` and `siwc` submodules without breaking existing builds.

### Phase 2: Configuration & State Integration
**Assignee: be**
1. Define `GatewayConfig` in `src/gateway/mod.rs` and incorporate into `avrig-api/src/main.rs` config loader.
2. Update `AppState` or create a unified runtime state holding optional `GatewayState` (Antigravity credentials/state and SIWC client).
3. Support credential paths from config and environment variable overrides.

### Phase 3: Route Mounting & Security Middleware
**Assignee: be**
1. Build the gateway Axum router with `build_gateway_router(state)`.
2. Mount the router onto the main `avrig-api` application router under `/api/v1/gateway` when the `gateway` role is active.
3. Apply security middleware (loopback-only check or OIDC token validator consistent with `avrig-api` security requirements).

### Phase 4: Verification & Automated Tests
**Assignee: be**
1. Add unit tests for gateway model prefix parsing (`strip_model_prefix`, `is_siwc_model`, `resolve_upstream_model_id`).
2. Write integration tests in `avrig-api/tests/` verifying `/api/v1/gateway/health`, `/api/v1/gateway/v1/models`, and mock `/api/v1/gateway/v1/chat/completions`.
3. Verify that existing `/api/v1/documents/*` and `/api/v1/mood` endpoints continue to function without regressions.

### Phase 5: Documentation & Reverse Proxy Configuration
**Assignee: Infra**
1. Update Nginx configuration if `/api/v1/gateway` should be exposed or restricted through reverse proxy.
2. Update Vault project documentation (`02-projects/avrig-ai/design/System-Architecture.md`) documenting the unified gateway routes.
3. Move plan to `plans/done/` upon successful verification.

---

## 4. Acceptance Criteria

- `avrig-api` builds and starts cleanly with `roles = ["server", "gateway"]`.
- The gateway endpoints are accessible under `/api/v1/gateway/...`.
- Model routing dispatches correctly to Google Antigravity or ChatGPT SIWC according to model name and prefix.
- All existing `avrig-api` capabilities (KM document ingestion, search, JEV intent routing, OpenCode adapter) remain unaffected.
- Automated tests pass on both Windows and Linux/WSL environments.
