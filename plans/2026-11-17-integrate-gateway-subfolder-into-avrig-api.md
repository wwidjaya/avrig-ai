---
title: "Plan: Integrate AI Gateway Role into avrig-api under /v1"
status: completed
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

# Plan: Integrate AI Gateway Role into avrig-api under /v1

## 1. Architectural Division: avrig-lib vs avrig-api

In accordance with system design guidelines, backend capabilities must be strictly partitioned between **foundational library crates (`avrig-lib`)** and **runtime server/daemon executables (`avrig-api`)**:

| Boundary Layer | Target Repository / Path | Primary Responsibilities & Scope |
|---|---|---|
| **`avrig-lib`** (Foundational Libraries & Domain Crates) | `avrig-lib/crates/*` | - **Pure Domain & Client Logic**: Gateway types, standard OpenAI schema models, error enums.<br>- **Upstream Provider Adapters**: Antigravity Cloud Code client, OAuth token refresh logic, converter mechanisms (`gemini` <-> `openai`), and SIWC ChatGPT client.<br>- **Shared Middleware**: Pure Tower layers, auth token validators, header extractors.<br>- **Zero Daemon Footprint**: No CLI arg parsing, no environment binding, no direct `TcpListener` or daemon lifecycle tasks. |
| **`avrig-api`** (Runtime Daemon & Gateway Service) | `avrig-api/` | - **Axum HTTP Runtime**: Route registration, mounting OpenAI-standard routes directly under `/v1/` (`/v1/models`, `/v1/quota`, `/v1/chat/completions`).<br>- **Node Role & Lifecycle**: Role `gateway` management (`run_gateway`), task cancellation tokens, signal shutdown handling.<br>- **Runtime Configuration**: Loading `config/gateway.toml`, CLI commands (`avrig gateway`), Vault token decryption, logging initialization.<br>- **Co-hosting**: Binding standalone port 8085 or embedding routes into the central API server. |

---

## 2. Objective

Integrate the unified AI Gateway capabilities (Google Antigravity OAuth and ChatGPT SIWC proxy) currently located in `avrig-ai/gateway` into the central `avrig-api` Axum server runtime directly under standard OpenAI-compatible routes (`/v1/models`, `/v1/quota`, `/v1/chat/completions`, and `/health`), managed via a first-class node role (`gateway`).

This consolidates AI gateway routing into the production `avrig-api` daemon with native OpenAI client compatibility, independent configuration, and coexistence with existing KM document/intent endpoints.

---

## 2. Architecture & Design

### A. Route Layout (`/v1/...`)
All gateway endpoints follow standard OpenAI API paths directly under `/v1/` without the `/api/` prefix:
- `GET  /health` : Health and upstream provider connection status (Google Antigravity, OpenAI SIWC).
- `GET  /v1/models` : Unified models list (prefixed models: `agy/*`, `chatgpt/*`).
- `GET  /v1/quota` : Google Antigravity quota and project tier details.
- `POST /v1/chat/completions` : Streaming (SSE) and non-streaming completions dispatcher routing across Antigravity and SIWC ChatGPT upstream adapters.

### B. OAuth Login Capabilities (CLI Subcommands & Interactive Web Flows)
To obtain or refresh tokens without manual JSON editing, `avrig` will include dedicated OAuth login capabilities:

1. **CLI Login & Account Management Commands**:
   - `avrig login antigravity [--account <ALIAS>]`: Initiates the Google OAuth PKCE authorization flow, receives tokens, and adds or updates the named account in `config/antigravity-accounts.json`.
   - `avrig login siwc [--account <ALIAS>]`: Initiates the Sign-in-with-ChatGPT (SIWC) OAuth flow and registers the account in `config/chatgpt-accounts.json`.
   - `avrig accounts list`: Lists all registered accounts across providers, their health status, token expiration, and configured aliases.
   - `avrig accounts remove <PROVIDER> <ALIAS>`: Unregisters a specific account.

2. **Web / API Login Endpoints (Optional Admin Mode)**:
   - `GET /v1/auth/antigravity/login?account=<ALIAS>` -> Returns redirect URL for a specific account.
   - `GET /v1/auth/antigravity/callback` -> Local callback receiver.
   - `GET /v1/auth/siwc/login?account=<ALIAS>` -> Returns ChatGPT OAuth URL.
   - `GET /v1/auth/siwc/callback` -> Callback receiver.
   - `GET /v1/auth/status` -> Shows connected accounts, active quotas, and token expiry across all registered accounts.

### B. Modular Structure & Division

#### 1. `avrig-lib` (`crates/avrig-gateway`):
New crate `avrig-gateway` staged inside `avrig-lib/crates/avrig-gateway/`:
- `src/types.rs`: OpenAI-compatible request/response data types (`ChatRequest`, `ChatCompletionResponse`, `ChatCompletionChunk`, models, quota structures).
- `src/converter.rs`: Bidirectional transformation between OpenAI format and Google Antigravity (Gemini/Cloud Code) and ChatGPT SIWC structures.
- `src/antigravity/`: Antigravity OAuth token handling, credential loading, and HTTP communication with Cloud Code endpoints.
- `src/siwc/`: Sign-in-with-ChatGPT OAuth client, token refresh flow, and chat stream decoding.
- `src/router.rs`: Core request dispatcher function mapping model prefixes (`agy/*`, `chatgpt/*`) to upstream providers.
- `src/client.rs` (**Reusable Multi-Provider Client Component with Multi-Account Pool**):
  - A unified, reusable client struct (`GatewayClient` / `LlmProviderClient`) that any crate or service in the platform can instantiate to invoke OpenAI-compatible completions.
  - **Multi-Account Registry for Each Provider Type**:
    1. **Google Antigravity (`agy`) Multi-Account**:
       - Registry of multiple Google accounts (e.g. `work`, `personal`, `fallback`).
       - Account health, quota tracking, and automatic failover / round-robin selection when quota or rate limits (HTTP 429) are reached on one account.
    2. **Sign-In With ChatGPT (`siwc`) Multi-Account**:
       - Registry of multiple ChatGPT accounts/refresh tokens.
       - Automatic token refresh per account and load-balancing/pool rotation.
    3. **Direct API Keys Multi-Account**:
       - Pool of API keys per provider (e.g., multiple OpenAI, OpenCode, Groq, or DeepSeek keys).
  - **Account Selection & Routing**:
    - Optional account targeting via header or model suffix (e.g., `agy/gemini-3.8-flash@work` or `x-avrig-account: account_id`).
    - Default strategy: health-aware least-recently-used (LRU) / round-robin across enabled accounts with automatic backoff on exhausted quota.
  - Exposes ergonomic methods:
    - `.chat_completion(request: ChatRequest) -> Result<ChatCompletionResponse>`
    - `.chat_completion_stream(request: ChatRequest) -> Result<impl Stream<Item = Result<ChatCompletionChunk>>>`
    - `.list_models() -> Result<Vec<ModelInfo>>`
    - `.list_accounts() -> Vec<AccountStatus>`

#### 2. `avrig-api`:
Consumes `avrig-gateway = { path = "../avrig-lib/crates/avrig-gateway" }`:
- `src/gateway.rs`: Axum HTTP request handlers (`chat_completions_handler`, `models_handler`, `quota_handler`, `health_handler`, and auth endpoints).
- `src/main.rs`: Adds role `gateway` (`run_gateway`), config loading from `config/gateway.toml`, CLI subcommands `Command::Gateway` and `Command::Login`, and mounting of routes under `/v1/`.

#### 3. `avrig-gateway` (in `avrig-lib`) Auth Modules:
- `src/antigravity/oauth.rs`: `login(...)`, `load_credentials(...)`, `refresh_access_token(...)`, PKCE state generation.
- `src/siwc/oauth.rs`: `login(...)`, `load_credentials(...)`, `exchange_code_for_token(...)`, `refresh_access_token(...)`.
- Core functions exported so both CLI subcommands and Axum HTTP endpoints can initiate login and save credentials.

### C. Node Role & Standalone / Embedded Lifecycle
Add `gateway` as a first-class role in `avrig-api` (joining `server`, `watcher`, and `reranker`):

1. **Role Definition**:
   - `roles = ["gateway"]`: Runs dedicated AI Gateway daemon on its configured `host` and `port` (e.g., `127.0.0.1:8085`).
   - `roles = ["server", "gateway"]`: Can run both the unified KM API server (`8000`) and the AI Gateway service, or mount `/v1/models`, `/v1/quota`, `/v1/chat/completions` directly onto the main HTTP router when co-hosted.
   - CLI command support: Add `gateway` subcommand to `avrig` CLI:
     ```bash
     avrig gateway --config config/
     ```
     in addition to multi-role `avrig run`.

2. **Configuration Layout (`config/gateway.toml` or `config.toml`)**:

```toml
[gateway]
host = "127.0.0.1"
port = 8085
mount_prefix = "/v1"
local_only = true
default_strategy = "round_robin"  # Options: "round_robin", "lru", "failover_priority"

# -------------------------------------------------------------
# Google Antigravity Provider Settings & Multi-Account Registry
# -------------------------------------------------------------
[gateway.antigravity]
enabled = true
client_id = "optional_client_id_override"
client_secret = "optional_client_secret_override"
accounts_file = "config/antigravity-accounts.json"

# Inlined / pre-configured accounts (optional, supplements accounts_file)
[[gateway.antigravity.accounts]]
alias = "primary"
credentials_file = "config/antigravity.json"
project_id = ""                 # If empty, parsed from refresh_token companion
enabled = true
priority = 10                   # Lower number = higher priority for failover

[[gateway.antigravity.accounts]]
alias = "backup"
credentials_file = "config/antigravity-backup.json"
enabled = true
priority = 20

# -------------------------------------------------------------
# ChatGPT SIWC Provider Settings & Multi-Account Registry
# -------------------------------------------------------------
[gateway.siwc]
enabled = true
accounts_file = "config/chatgpt-accounts.json"

[[gateway.siwc.accounts]]
alias = "personal"
credentials_file = "config/chatgpt.json"
enabled = true
priority = 10

[[gateway.siwc.accounts]]
alias = "team"
credentials_file = "config/chatgpt-team.json"
enabled = true
priority = 20

# -------------------------------------------------------------
# Direct OpenAI-Compatible Providers & Key Pools
# -------------------------------------------------------------
[gateway.providers.opencode]
base_url = "https://opencode.ai/api/v1"
api_key = "{env:OPENCODE_API_KEY}"
enabled = true

[gateway.providers.groq]
base_url = "https://api.groq.com/openai/v1"
enabled = true
# Multiple API keys for load balancing / rate limit mitigation
api_keys = [
    "{env:GROQ_API_KEY_1}",
    "{env:GROQ_API_KEY_2}"
]

[gateway.providers.ollama]
base_url = "http://10.30.200.32:11434/v1"
enabled = true
```

3. **Task Lifecycle Execution**:
   In `avrig-api/src/main.rs`:
   ```rust
   if roles.iter().any(|r| r == "gateway") {
       let cfg = config.clone();
       let token = cancellation.child_token();
       tasks.push(tokio::spawn(async move {
           run_gateway(cfg.gateway.clone(), token).await
       }));
   }
   ```
   Ensuring proper cancellation token propagation, signal handling, and clean shutdown alongside other roles.

---

## 3. Implementation Phases & Subagent Assignments

### Phase 1: Create `avrig-gateway` in `avrig-lib`
**Assignee: be**
1. Initialize `crates/avrig-gateway` in `D:\Cloud\OneDrive\AI\Agentic\avrig-lib\`.
2. Extract and consolidate the reusable client, converter, and OAuth modules:
   - `antigravity` (OAuth client, quota, token management, prompt converter)
   - `siwc` (ChatGPT client, tokens, streaming parser)
   - `types` (OpenAI completion data models and error envelopes)
   - `resolver` (model prefix extraction and upstream selection)
   - `client` (`LlmProviderClient` component supporting API Key, SIWC, and Antigravity with multi-account pools)
3. Ensure `avrig-gateway` compiles as a clean, reusable library crate with zero daemon or Axum-specific coupling, so other internal crates (such as `avrig-harness`, `avrig-sdlc`, or `avatar-runtime`) can invoke OpenAI-compatible completions uniformly.

### Phase 2: Consume in `avrig-api` & Configuration Integration
**Assignee: be**
1. Add `avrig-gateway = { path = "../avrig-lib/crates/avrig-gateway" }` to `avrig-api/Cargo.toml`.
2. Define `GatewayConfig` in `avrig-api` and incorporate into `src/main.rs` config loader and `config/gateway.toml`.
3. Update `Command` enum in `src/main.rs` to include `Command::Gateway` and `Command::Login`:
   - `avrig login antigravity` (or `avrig login google`)
   - `avrig login siwc` (or `avrig login chatgpt`)
4. Add the `"gateway"` role handler in `src/main.rs` (`run_gateway(config, token)`), supporting both standalone port binding (8085) and embedded mounting.
5. Support credential loading from files, environment variables, and Vault.

### Phase 3: Route Mounting & Security Middleware
**Assignee: be**
1. Build the gateway Axum router with `build_gateway_router(state)`.
2. Mount the router onto the main `avrig-api` application router directly under `/v1/` (`/v1/models`, `/v1/quota`, `/v1/chat/completions`) and root (`/health`) when the `gateway` role is active.
3. Apply security middleware (loopback-only check or OIDC token validator consistent with `avrig-api` security requirements).

### Phase 4: Verification & Automated Tests
**Assignee: be**
1. Add unit tests for gateway model prefix parsing (`strip_model_prefix`, `is_siwc_model`, `resolve_upstream_model_id`).
2. Write integration tests in `avrig-api/tests/` verifying `/v1/models`, `/v1/quota`, and mock `/v1/chat/completions`.
3. Verify that existing `/api/v1/documents/*` and `/api/v1/mood` endpoints continue to function without regressions.

### Phase 5: Documentation & Reverse Proxy Configuration
**Assignee: Infra**
1. Update Nginx configuration if `/v1/chat/completions` or `/v1/models` should be exposed or restricted through reverse proxy.
2. Update Vault project documentation (`02-projects/avrig-ai/design/System-Architecture.md`) documenting the unified gateway routes.
3. Move plan to `plans/done/` upon successful verification.

---

## 4. Acceptance Criteria

- `avrig-gateway` in `avrig-lib` exposes a clean, standalone `LlmProviderClient` supporting multi-account registration for all provider types (API key, SIWC, Antigravity) with automatic rotation and failover.
- Running `avrig login antigravity --account <ALIAS>` or `avrig login siwc --account <ALIAS>` allows registering and managing multiple accounts per provider.
- `avrig-api` builds and starts cleanly with `roles = ["gateway"]` (standalone) as well as `roles = ["server", "gateway"]` (embedded/co-hosted).
- Running `avrig gateway` starts the gateway role directly.
- Running `avrig login antigravity` or `avrig login siwc` successfully guides the user through browser-based OAuth authorization and saves valid credentials.
- The gateway endpoints are accessible under `/v1/...` (`/v1/chat/completions`, `/v1/models`, `/v1/quota`) matching standard OpenAI clients without an `/api/` prefix.
- Model routing dispatches correctly to Google Antigravity or ChatGPT SIWC according to model name and prefix.
- All existing `avrig-api` capabilities (KM document ingestion, search, JEV intent routing, OpenCode adapter) remain unaffected.
- Automated tests pass on both Windows and Linux/WSL environments.
