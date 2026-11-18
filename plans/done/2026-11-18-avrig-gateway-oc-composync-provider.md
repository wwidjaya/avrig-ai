# Avrig Gateway: `oc-composync` on OpenCode Go, session passthrough, legacy gateway removal

Status: completed
Owner: plan
Created: 2026-11-18
Revised: 2026-11-18 (Go endpoint, session passthrough, removal of `avrig-ai/gateway`)
Released: 0.3.0

## Goals and Objectives

1. Register a direct provider named `oc-composync` in the avrig gateway, pointing at the OpenCode Go endpoint `https://opencode.ai/inference/go/v1` and authenticating with `{env:OPENCODE_COMPOSYNC_API_KEY}`.
2. Forward the client's OpenCode session id to the upstream. OpenCode sends `x-opencode-session` on every model request, and OpenCode Go requires it. The gateway must preserve it per conversation and generate one when a client does not supply it. User-Agent becomes a per-provider choice: forward the caller's agent, or send a fixed value. `oc-composync` forwards.
3. Serve real completions through the Go subscription: at least two distinct model families return 200 with non-empty content, in both the non-streaming and streaming paths. The gateway's `usage` is a closed `OpenAIUsage` (`avrig-lib/crates/avrig-gateway/src/antigravity/types.rs:219-233`), so upstream `usage.opencode.billing_source` is dropped before the client sees it; billing is confirmed separately by direct curl outside the gateway, and no struct is widened to surface it.
4. Do not create a `paid` alias. `oc-composync/paid` must return 404 `model_not_found`, and no combo or virtual id may appear under this provider.
5. Leave existing providers unchanged. The measured baseline drifts upstream, so the requirement is relative: `composync`, `opencode`, `agy` and `ollama` keep their model sets (1079, 87, 34, 2 when last read, total 1202), and no new header reaches providers that do not ask for one.
6. Remove the legacy `avrig-ai/gateway` folder and its Cargo workspace membership, delivered as `d4db928`, so `avrig-lib/crates/avrig-gateway` is the only gateway runtime left. The duplicated types inside `avrig-ai/test` and `avrig-ai/claude` are separate members and stay.
7. Survive redeployment: `avrig-api/scripts/deploy.ps1` overwrites the runtime config from the repository copy, so both config files must carry the block.

## Context and Measured Evidence

### Gateway provider mechanics

| Fact | Evidence |
|---|---|
| Providers are a free-form map keyed by provider name | `avrig-api/src/main.rs:105` |
| Entry schema is `base_url`, `api_key`, `api_keys`, `enabled`, no `deny_unknown_fields` | `avrig-api/src/main.rs:159-166` |
| Enabled entries are registered at startup | `avrig-api/src/main.rs:1117-1138` |
| `{env:VAR}` resolves at startup, empty when unset | `avrig-api/src/main.rs:1143-1151` |
| `DirectProviderAccount` holds name, base url, keys and a key cursor | `avrig-lib/crates/avrig-gateway/src/client.rs:40-46` |
| Direct registration signature is `(name, base_url, keys)` | `avrig-lib/crates/avrig-gateway/src/client.rs:222-238` |
| Non-stream dispatch builds the upstream request | `avrig-lib/crates/avrig-gateway/src/client.rs:1392-1418` |
| Stream dispatch builds the upstream request | `avrig-lib/crates/avrig-gateway/src/client.rs:1420-1456` |
| Model ids are advertised as `<provider>/<upstream-id>` | `avrig-lib/crates/avrig-gateway/src/client.rs:327-358` |
| Unknown sub-models are rejected against the catalogue | `avrig-lib/crates/avrig-gateway/src/client.rs:467-494` |
| The chat handler deserializes `ChatRequest` directly from JSON | `avrig-api/src/gateway.rs:178-181` |
| `ChatRequest` is the upstream wire type | `avrig-lib/crates/avrig-gateway/src/antigravity/types.rs:170-192` |
| `rand` 0.8 is already a dependency | `avrig-lib/crates/avrig-gateway/Cargo.toml:21` |

### OpenCode Go endpoint behaviour

Measured 2026-11-18 with the current `OPENCODE_COMPOSYNC_API_KEY`:

| Probe | Result |
|---|---|
| `GET /inference/go/v1/models` with bearer only, no session header | 200, 32 ids |
| `POST /inference/go/v1/chat/completions` without `x-opencode-session` | 400 `MissingSessionID` |
| Same with any opaque session value | 200, `usage.opencode.billing_source = "go"`, `cost = 0`, allowance fields present |
| Session value `abc123`, 22 char base64url, canonical UUID v4 | all 200 |
| Same session reused for two calls | 200 both times |
| `paid`, `combo`, `auto` in the body with a session header | 400 `server_error`: "Model paid isn't included in OpenCode Go" |
| `GET /inference/go/models` (no `/v1`) | 404 |

Model families confirmed at 200 on the Go path: `deepseek-v4.1-flash`, `deepseek-v4-pro`, `kimi-k3`, `qwen3.8-max`, `glm-5.3`, `minimax-m3`, `gpt-6-luna`, `claude-haiku-5-5`.

Go catalogue (32 ids): `beam-free`, `claude-haiku-5-5`, `deepseek-v4.1-flash`, `deepseek-v4-pro`, `gemini-4-argon`, `glm-5.2`, `glm-5.3`, `glm-5.3-flash`, `gpt-5.6-luna`, `gpt-6-luna`, `grok-4.7`, `hy3`, `hy4`, `hy4-flash-free`, `hy4-preview`, `iceman-contributor-free`, `kimi-k2.7-code`, `kimi-k3`, `kimi-k3.1-pro`, `longcat-2.0`, `longcat-2.5-free`, `mimo-v2.6-flash`, `mimo-v2.6-pro`, `minimax-m3`, `minimax-m3.1-flash`, `muse-spark-1.2-contributor`, `muse-spark-1.3-contributor`, `qwen3.7-plus`, `qwen3.8-flash`, `qwen3.8-max`, `qwen4-max`, `step-5-preview`.

The older `/inference/openai/v1` path stays out of scope. It returns 44 ids, and every paid model there answers 402 "Insufficient balance" for this org, because that path is pay-as-you-go rather than subscription.

### Does OpenCode send a session id? Yes

Inspected the installed client, `d:\nodejs\.npm\global\node_modules\@opencode\cli\bin\opencode.exe` (247.7 MB). At byte offset 183548329 the provider request builder sets, for every model request:

```js
headers: {
  "x-opencode-session-id": l.id,
  ...(l.parentID ? { "x-opencode-parent-session-id": l.parentID } : {}),
  "x-session-affinity": B,
  "X-Session-Id": B,
  ...(l.parentID ? { "x-parent-session-id": l.parentID } : {}),
  "User-Agent": sc(L),
  "x-opencode-project": l.projectID,
  "x-opencode-session": B,
  "x-opencode-client": L.name
}
```

This applies to provider requests in general, including custom OpenAI-compatible providers such as the `avrig` provider that points at `http://127.0.0.1:8000/v1`. So the gateway already receives a session header today and currently drops it.

The Go documentation states the requirement directly: "Send a stable session ID in `x-opencode-session` for each conversation so we can optimize routing and prompt caching", and for proxy setups: "preserve the session header when forwarding requests."

Header precedence to use, first non-empty wins: `x-opencode-session`, then `x-opencode-session-id`, then `X-Session-Id`. Header lookup in axum is case-insensitive; the three names are distinct entries and all may be present.

### Credential state

| Variable | User scope | Machine scope |
|---|---|---|
| `OPENCODE_API_KEY` | set | set |
| `OPENCODE_COMPOSYNC_API_KEY` | not set (cleared during rotation) | set, valid, rotated 2026-11-18 |

The gateway resolves the variable at startup and Machine scope is visible to the NSSM service `avrig` (`avrig-api/scripts/deploy.ps1:33`).

### Legacy gateway inventory

`D:\Cloud\OneDrive\AI\Agentic\avrig-ai\gateway` contains a Go mock (`main.go`, `go.mod`, `README.md`, `main_test.go`), a duplicate Rust crate (`Cargo.toml`, `build.rs`, `src/*` mirroring `avrig-lib/crates/avrig-gateway`), one SQL file (`migrations/20261118000001_multi_client_sessions.sql`), and a committed binary `gateway.exe` (8.8 MB). It is a Cargo workspace member at `avrig-ai/Cargo.toml:7` (`"crates/avrig-sdlc", "test", "gateway", "claude",`) and is git-tracked in the `avrig-ai` repository.

Checks performed:
- No Makefile target and no `avrig-ai/README.md` section references the folder.
- Nothing outside the folder references `multi_client_sessions`, so the SQL file is dead.
- No crate depends on the `gateway` package; the active gateway is `avrig-lib/crates/avrig-gateway`, consumed by `avrig-api`.
- `avrig-ai/test` is a separate workspace member with its own near-duplicate of the antigravity types. It is not part of this removal and stays as-is.

## Key Detailed Design

### Program Design

Two connected changes: one config field per provider, one passthrough of the inbound session header.

**Session id carrying.** `ChatRequest` gains a transport-only field, so no dispatch signature changes:

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatRequest {
    // ... existing fields ...
    /// Transport-only: populated from the inbound session header, never serialized upstream.
    #[serde(skip)]
    pub session_id: Option<String>,
}
```

`#[serde(skip)]` keeps the upstream JSON body byte-identical, since the field is skipped on serialization and ignored on deserialization. Three struct literals must add `session_id: None`: `avrig-api/src/main.rs:2487`, `avrig-api/tests/gateway_integration_test.rs:95`, and `:139`. All other constructions go through `serde_json::from_value` and need no edit.

**Header capture.** `handle_chat_completions` (`avrig-api/src/gateway.rs:178`) gains a `HeaderMap` extractor and sets the field before branching:

```rust
pub async fn handle_chat_completions(
    State(state): State<Arc<GatewayState>>,
    headers: HeaderMap,
    Json(mut input): Json<ChatRequest>,
) -> Response {
    input.session_id = session_header_value(&headers);
    // ... unchanged dispatch ...
}
```

with

```rust
/// Session id supplied by the calling client, if any.
///
/// OpenCode sends `x-opencode-session` on every model request and OpenCode Go requires it.
/// `x-opencode-session-id` and `X-Session-Id` are accepted as fallbacks for other clients.
fn session_header_value(headers: &HeaderMap) -> Option<String> {
    ["x-opencode-session", "x-opencode-session-id", "X-Session-Id"]
        .iter()
        .find_map(|name| {
            headers
                .get(*name)
                .and_then(|v| v.to_str().ok())
                .map(str::trim)
                .filter(|v| !v.is_empty())
                .map(str::to_owned)
        })
}
```

**Provider opt-in.** Both the session header and the User-Agent policy are declared per provider, so `ollama`, `composync`, `opencode` and the built-in backends keep their current behaviour.

```rust
#[derive(Clone, Debug, Default, Deserialize)]
pub struct GatewayProviderConfig {
    pub base_url: String,
    pub api_key: Option<String>,
    pub api_keys: Option<Vec<String>>,
    #[serde(default = "default_true")]
    pub enabled: bool,
    /// When set, each chat completion carries the session id under this header name.
    pub session_header: Option<String>,
    /// Outbound `User-Agent` policy: absent sends the gateway default, `{forward}` sends the
    /// caller's agent when it identifies an application, any other value sends that literal.
    pub user_agent: Option<String>,
}
```

Registration (`avrig-api/src/main.rs:1135-1137`) passes both through, and a blank `session_header` is normalised to `None` so a malformed config cannot reach `reqwest::header("")`, which panics on an invalid header name:

```rust
let session_header = pcfg
    .session_header
    .as_deref()
    .map(str::trim)
    .filter(|v| !v.is_empty())
    .map(str::to_owned);
let user_agent = pcfg.user_agent.as_deref().map(|v| resolve_env_var(v.to_owned()));

client
    .add_direct_provider(
        name.clone(),
        pcfg.base_url.clone(),
        keys,
        session_header,
        user_agent,
    )
    .await;
```

`resolve_env_var` only rewrites values starting with `{env:`, so the `{forward}` sentinel survives registration unchanged and `user_agent = "{env:MY_AGENT}"` also resolves.

**Dispatch.** `DirectProviderAccount` gains `session_header: Option<String>` and `user_agent: Option<String>`, `add_direct_provider` takes five parameters, and both executors add, after the `Authorization` header:

```rust
if let Some(header) = &direct.session_header {
    let session = input
        .session_id
        .as_deref()
        .filter(|v| !v.trim().is_empty())
        .map(str::to_owned)
        .unwrap_or_else(new_session_id);
    req = req.header(header.as_str(), session);
}
```

The hardcoded `.header("User-Agent", "opencode/1.0.0")` in both executors becomes a computed value:

```rust
const DEFAULT_USER_AGENT: &str = "opencode/1.0.0";
const FORWARD_SENTINEL: &str = "{forward}";

let user_agent = match direct.user_agent.as_deref().map(str::trim) {
    Some(FORWARD_SENTINEL) => input
        .user_agent
        .as_deref()
        .and_then(application_user_agent)
        .unwrap_or(DEFAULT_USER_AGENT),
    Some(fixed) if !fixed.is_empty() => fixed,
    _ => DEFAULT_USER_AGENT,
};
// ...
.header("User-Agent", user_agent)
```

Default behaviour is unchanged: a provider that declares no `user_agent` still sends `opencode/1.0.0`, so `composync`, `opencode`, `ollama` and `agy` are untouched. The guard exists because OpenCode Go states it monitors traffic for abuse and asks clients to identify themselves, so a generic library agent is a worse signal than the gateway's own:

```rust
/// Caller user agent, when it identifies an application rather than an HTTP library.
fn application_user_agent(value: &str) -> Option<&str> {
    const GENERIC: &[&str] = &[
        "curl/", "wget/", "python", "reqwest/", "node", "axios/", "okhttp/",
        "go-http-client/", "java/", "powershell/", "mozilla/", "httpie/",
        "postmanruntime/", "insomnia/", "undici/", "deno/", "bun/", "hyper/",
        "libwww-perl", "httpclient/", "guzzlehttp/", "faraday", "restsharp",
    ];
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return None;
    }
    let lowered = trimmed.to_ascii_lowercase();
    if GENERIC.iter().any(|prefix| lowered.starts_with(prefix)) {
        return None;
    }
    Some(trimmed)
}
```

`new_session_id()` builds a canonical UUID v4 from `rand`, avoiding a new dependency:

```rust
/// Generate a session id for a request that carried none.
///
/// OpenCode Go accepts any opaque value, so a UUID v4 keeps callers that cannot send the
/// header (curl, internal callers) working without tracking conversation state.
fn new_session_id() -> String {
    let mut b = [0u8; 16];
    rand::thread_rng().fill_bytes(&mut b);
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    format!(
        "{:02x}{:02x}{:02x}{:02x}-{:02x}{:02x}-{:02x}{:02x}-{:02x}{:02x}-{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}",
        b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7],
        b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15]
    )
}
```

Needs `use rand::RngCore;`. Catalogue paths stay untouched: `list_models` (`client.rs:327-358`) and `direct_provider_models` (`client.rs:369-410`) work against the Go endpoint with the bearer token alone.

Runtime flow after the change:

1. Startup reads `gateway.toml` and registers `oc-composync` with base url `https://opencode.ai/inference/go/v1`, the key from `OPENCODE_COMPOSYNC_API_KEY`, `session_header = "x-opencode-session"`, and `user_agent = "{forward}"`.
2. OpenCode calls `POST /v1/chat/completions` with `x-opencode-session` set from its own session affinity, plus its own `User-Agent` and other OpenCode headers.
3. `handle_chat_completions` stores the session id and the caller agent on `ChatRequest`; the direct dispatcher forwards the session under `x-opencode-session` and, because the policy is `{forward}`, sends the caller agent when it identifies an application.
4. Upstream answers 200 with `billing_source = "go"`; the gateway returns the response unchanged. The gateway's `usage` struct is closed, so that upstream billing field is not surfaced to the client.
5. A caller without the session header, such as curl or the document search path, gets a generated UUID v4 per request, and its generic `curl/` agent is replaced by `opencode/1.0.0`.
6. `oc-composync/paid` fails catalogue validation before dispatch: 404 `model_not_found`.

### Configuration

Append after the `[gateway.providers.composync]` table in both config files:

```toml
[gateway.providers.oc-composync]
enabled = true
base_url = "https://opencode.ai/inference/go/v1"
api_key = "{env:OPENCODE_COMPOSYNC_API_KEY}"
session_header = "x-opencode-session"
user_agent = "{forward}"
```

Notes: `oc-composync` is a valid TOML bare key and a valid routing prefix. The `/v1` suffix is required. No `models` table, since aliasing does not exist and `paid` is out of scope.

There are three independent copies of this file, which matters for the change to take effect everywhere:

| Copy | Path | Versioned | Synced by |
|---|---|---|---|
| Repository source | `avrig-api/config/gateway.toml` | No, gitignored at `avrig-api/.gitignore:10` | `deploy.ps1:92-101` reads it |
| Windows runtime | `D:\avrig\config\gateway.toml` | No | Overwritten from the repository copy on every deploy |
| WSL runtime | `/opt/avrig/config/gateway.toml` in distro `avrig-ai` | No | Nothing. `deploy.ps1` copies only the binary to WSL |

Because the repository copy is gitignored, the provider table is deployment state, not release content. A fresh clone will not carry it, and the release commit will not include it. The WSL copy is intentionally left alone: the gateway role is Windows-only by decision, so that node keeps its older file (1024 bytes, no `oc-composync`).

### Revision: gateway topology and client addressing

Discovered at the build gate, after deploy. Port 8000 has two owners on this machine, and the one the client was configured against is not the Windows node:

| Node | Roles (`config.toml`) | Binds | Reported `target_triple` | Accounts | Providers |
|---|---|---|---|---|---|
| Windows, `D:\avrig\avrig.exe` (NSSM `avrig`) | `watcher`, `reranker`, `gateway` | `0.0.0.0:8000`, loopback-only peers | `x86_64-pc-windows-msvc` | 6 | google-antigravity, openai-siwc, composync, **oc-composync**, ollama, opencode, plus `chatgpt` models |
| WSL `avrig-ai`, `avrig.service` | `server` | `127.0.0.1:8000` inside the distro | `x86_64-unknown-linux-gnu` | 5 | google-antigravity, openai-siwc, composync, ollama, opencode |

`wslrelay.exe` exposes the WSL loopback listener on the Windows side, so `http://127.0.0.1:8000` resolves to the Linux node. Every LAN address returns 403 `localhost clients only` from the Windows node, so a remote address cannot reach it either. Consequence: the `avrig` provider in `.opencode/opencode.json`, which pointed at `127.0.0.1:8000`, was talking to the WSL node and never saw `oc-composync`.

Resolution, decided by the user:

1. Point the client at the Windows node through a loopback alias: `http://127.0.0.2:8000/v1`. Measured 200, loopback peer, full provider set. No infra change, no WSL config, keeps the gateway Windows-only.
2. The client's `models` map is authoritative, not `/v1/models`: `opencode models` listed exactly the 27 declared `avrig` models while the gateway advertises 87 `opencode/*` ids. So `oc-composync` needed explicit entries to be selectable.
3. All 32 Go ids are added with `Go: <Model>` display names, taking the `avrig` provider from 27 to 59 models.

Correction after the first picker screenshot: the labels are display text only and read as a separate naming scheme (`AGY:`, `ChatGPT:`, `Go:`) next to ids that already carry a prefix. Decided by the user: every `avrig` model entry's `name` is set to its own key, so the picker reads `oc-composync/deepseek-v4.1-flash`, `agy/claude-opus-5-5-high`, `chatgpt/gpt-6-luna`, `opencode/kimi-k3`. No gateway change is needed, because the advertised id already is `<provider>/<upstream-id>` at `client.rs:370`, and the prefix is configurable today by naming the provider table in `gateway.toml`.

Side effect worth recording: the `chatgpt` models declared in the client map were never served by the WSL node either (it reports no `chatgpt` provider), so they start working with the same address change.

This also means the earlier baseline measurements of 1201 to 1202 models were taken against the WSL node, while the counts in T7 and T17 must come from `127.0.0.2:8000`.

### Defect found in real use: streams end without `finish_reason`

Hit through OpenCode after deploy: `OpenAI Chat stream ended without finish_reason`, then a retry. Reproduced against `127.0.0.2:8000` with `stream: true` and `max_tokens: 16`, comparing the gateway's SSE output to the same model called directly on the Go endpoint.

| Model | Frames from gateway | Frames with `finish_reason` | Status |
|---|---|---|---|
| `oc-composync/gpt-6-luna` | 3 | 1 | works |
| `oc-composync/kimi-k3` | 6 | 1 | works |
| `oc-composync/qwen3.8-max` | 10 | 1 | works |
| `oc-composync/minimax-m3` | 5 | 1 | works |
| `oc-composync/deepseek-v4.1-flash` | 8 | 0 | broken |
| `oc-composync/deepseek-v4-pro` | 9 | 0 | broken |
| `oc-composync/glm-5.3` | 0, only `data: [DONE]` | 0 | broken |

Upstream shape, captured directly: intermediate frames carry `finish_reason: ""` and deltas that may hold only `reasoning_content`; the terminal frame has an empty `delta`, `finish_reason: "stop"`, and the `usage` block. The gateway re-serializes each delta into `{role, content, reasoning_content}` and the terminal frame never reaches the client, and for `glm-5.3` nothing does. The same model through the older `opencode` provider streams correctly, so this is the direct-provider relay, not the SSE writer.

Fix requirements recorded for `be`: always end with a non-empty `finish_reason` (forwarded, or synthesized as `length` or `stop`), never drop a frame, keep `OpenAIUsage` closed, add stub-based regressions for the three frame shapes. Release is on hold until this is fixed, deployed, and re-verified.

Root cause and fix, delivered as avrig-lib `de8923d`: `filter_direct_usage_stream` discarded any frame carrying `usage`, which on these models is the same frame that carries `finish_reason`, so the reason was destroyed by design. The relay now pins id and model on the first frame, strips usage into a saved value, holds the reason back, forwards every frame whose delta has any field, and always appends one terminal chunk with the upstream reason, or `length` when the last usage hit `max_tokens`, otherwise `stop`. Undecodable frames warn instead of vanishing, and in-band error frames surface as errors.

Re-verified after redeploy (`avrig.exe` SHA-256 `fbe00222…1f9a`, `1b9a25a` plus avrig-lib `de8923d`):

| Model | Frames | Terminal `finish_reason` | Last frame is the reason |
|---|---|---|---|
| `deepseek-v4.1-flash` | 8 | `stop` | yes |
| `deepseek-v4-pro` | 11 | `stop` | yes |
| `glm-5.3` | 7 | `length` | yes |
| `gpt-6-luna` | 3 | `stop` | yes |
| `kimi-k3` | 2 | `length` | yes |
| `qwen3.8-max` | 12 | `stop` | yes |
| `minimax-m3` | 5 | `length` | yes |

End-to-end through OpenCode, `avrig/oc-composync/deepseek-v4.1-flash` and `avrig/oc-composync/glm-5.3` both returned `ok` with no `stream ended without finish_reason` retry.

Two notes carried forward. The build metadata in `/v1/health` reports the `avrig-api` commit only, so `de8923d` in `avrig-lib` is not visible there. And `sse_data_stream` still drops a final line that lacks a trailing newline at EOF; it is shared with the antigravity and SIWC paths, so it stays a separate fix.

### Legacy gateway removal

Delivered ahead of the feature work as commit `d4db928` in `avrig-ai` ("chore(avrig-ai): remove legacy gateway folder and workspace member"). It removed the Go mock, the duplicate Rust crate, the orphan SQL file, and the tracked `gateway.exe`, dropped `"gateway"` from the workspace members, and regenerated the lock. What remains is verification, not removal:

1. Confirm `avrig-ai/gateway` is absent and untracked: `Test-Path`, `git ls-files gateway`.
2. Confirm `avrig-ai/Cargo.toml` members contain no `"gateway"` and `avrig-ai/Cargo.lock` has no `name = "gateway"` package.
3. Run `cargo check --workspace` in `avrig-ai`.
4. Accept that "only one gateway implementation" holds for the gateway runtime, not for every duplicate type in the tree: `avrig-ai/test` keeps its own copy of the antigravity types and `avrig-ai/claude` its own code. Those are separate members and out of scope.

Do not re-create the folder. If the removal commit needs reverting, `git revert d4db928` and re-add the workspace member, which is an independent action from the feature commit.

### Target Program Files (Mandatory)

| Action | Path | Change |
|---|---|---|
| Edit | `avrig-lib/crates/avrig-gateway/src/antigravity/types.rs` | Add two transport-only fields to `ChatRequest` (170-192): `#[serde(skip)] session_id: Option<String>` and `#[serde(skip)] user_agent: Option<String>` |
| Edit | `avrig-lib/crates/avrig-gateway/src/client.rs` | Add `session_header: Option<String>` and `user_agent: Option<String>` to `DirectProviderAccount` (40-46); widen `add_direct_provider` to five parameters (222-238); forward the session header, resolve the User-Agent policy with `DEFAULT_USER_AGENT` and `application_user_agent()`, and add `new_session_id()`, in both executors (1392-1418, 1420-1456) |
| Edit | `avrig-api/src/gateway.rs` | `handle_chat_completions` gains `HeaderMap`, sets `input.session_id` and `input.user_agent`, plus `session_header_value` helper and its unit tests (178) |
| Edit | `avrig-api/src/main.rs` | `GatewayProviderConfig` gains `session_header` and `user_agent` (159-166); both resolved and passed at registration (1135-1137); `session_id: None` and `user_agent: None` at the document search literal (2487) |
| Edit | `avrig-api/tests/gateway_integration_test.rs` | Add `session_id: None` at the two `ChatRequest` literals (95 and 139) and the fourth argument `None` at the two `add_direct_provider` call sites (38 and 219) |
| Edit | `D:\Cloud\OneDrive\AI\Agentic\avrig-api\config\gateway.toml` | Append the `[gateway.providers.oc-composync]` table after line 43 |
| Edit | `D:\avrig\config\gateway.toml` | Append the same table for the running node |
| Verify | `D:\Cloud\OneDrive\AI\Agentic\avrig-ai\gateway\` | Already deleted in `d4db928`; confirm the path and its git tracking are gone |
| Edit | `D:\Cloud\OneDrive\AI\Agentic\avrig-ai\Cargo.toml` | Remove `"gateway"` from `members` (line 7) |
| Regenerate | `D:\Cloud\OneDrive\AI\Agentic\avrig-ai\Cargo.lock` | Drop the `gateway` package entry |
| No change | `avrig-lib/crates/avrig-gateway/src/client.rs:327-410` | Catalogue paths need no session header |
| No change | `avrig-lib/crates/avrig-gateway/src/resolver.rs` | `oc-composync` is a configured provider, not a builtin prefix |
| No change | `avrig-ai/test`, `avrig-ai/claude` | Separate workspace members with their own copies; out of scope |
| No change | `D:\Cloud\OneDrive\AI\Agentic\.opencode\opencode.json` | Client configuration, unchanged |

Deployment coupling: `avrig-api/scripts/deploy.ps1:92-101` copies the repository `gateway.toml` over the runtime file unconditionally, so both config edits are mandatory.

### EDM Design

Not applicable. The one SQL file being deleted belongs to the legacy folder and has no consumer. No table, column, index, constraint, or migration is created.

### Environment Design

1. `OPENCODE_COMPOSYNC_API_KEY` is valid at Machine scope, visible to the NSSM service. No change needed; confirm with a live completion after restart. This is verified by the completion, not by a service-account inspection: `deploy.ps1:33-34` only names the service `avrig` and stops or starts it around the binary swap, it does not show the account or its environment.
2. The gateway role runs on Windows only. The WSL node (`avrig.service`, user `avrig`, loopback `127.0.0.1:8000` inside the distro) is explicitly out of scope for this provider: it keeps its current config and unit environment, and no `oc-composync` block or key is added there.
3. Because `wslrelay.exe` owns `127.0.0.1:8000` on the Windows side, the client must address the Windows node as `http://127.0.0.2:8000/v1`. That is a `.opencode/opencode.json` change only, recorded under "Revision: gateway topology and client addressing".
4. Two config copies matter for this change, the repository file and the Windows runtime, as tabulated under Configuration. The WSL copy exists but is not a target.
5. Never place the literal key in any `gateway.toml`; only the `{env:...}` reference.

### Rollback

1. Remove the `[gateway.providers.oc-composync]` table from both config files and restart. No binary change needed.
2. Revert the feature commit if the session forwarding itself regresses; the legacy folder removal is an independent commit and can stay reverted separately.
3. To restore the legacy folder, `git revert` its removal commit in `avrig-ai` and re-add the workspace member.

## Parallel Execution Plan

| Phase | Owner | Work | Depends on |
|---|---|---|---|
| 1. Discovery and design | `plan` | Completed: endpoint behaviour, session header evidence from the client binary and docs, dispatch sites, legacy folder inventory | none |
| 2. Quality gate, parallel | `tester` | Finalise the matrix with concrete commands, expected values, and stub-based header assertions | Phase 1 |
| 2. Quality gate, parallel | `analyst` | Audit against coding principles, wire-type purity, and the release policy; append to `## Review Findings` | Phase 1 |
| 3. Approval | `primary` | User approves goals, the target file list, and the matrix | Phases 1 and 2 |
| 4. Removal verification, parallel | `be` | Confirm `d4db928` landed: folder absent, no `"gateway"` member, no lock entry, `cargo check --workspace` in `avrig-ai` | Phase 3 |
| 4. Feature workstream, parallel | `be` | `ChatRequest` field, `handle_chat_completions` header capture, provider config field, dispatch forwarding, both TOML edits, test literals | Phase 3 |
| 5. Build gate | `build` | `cargo check --workspace` in `avrig-api`, `make build` in `avrig-api` for both targets, `make deploy` | Phase 4 |
| 6. Verification | `tester` | Execute the matrix against `http://127.0.0.1:8000/v1`, using `.secrets/test_token.json` where a token is required | Phases 4 and 5 |
| 6. Feature commits | `be` | Commit the `avrig-lib` and `avrig-api` changes, since `release.ps1:142` stages everything with `git add -A` | Phase 4 |
| 6. Release | `build` | `make release-minor`, annotated tag equal to the version in all four repos, push branch and tag, verify with `git ls-remote --tags origin`, report SHA, tag and branch per repo | Phase 6 passing |
| 6. Retrospective | `km` | Record the Go session header finding, the endpoint split, and the legacy folder removal in the vault | Phase 6 |
| 7. Close-out | `primary` | Mark completed, move the plan to `plans/done/` in the project root | Phase 6 |

Ordering constraints:
- The binary that forwards the header must be deployed before the `oc-composync` block is enabled, otherwise every call fails with 400 `MissingSessionID`.
- Removal and feature commits stay separate within Phase 4, both landing before the build gate.
- `Infra` restarts `avrig` and `avrig.service` only after `build` replaces the binaries.

## Test Specification and Validation Matrix

Authored here as a draft; `tester` owns the final wording.

**Base URL for every case below is `http://127.0.0.2:8000` (the Windows node).** `127.0.0.1:8000` is the WSL node and does not carry `oc-composync`; see "Revision: gateway topology and client addressing". Cases that compare against a pre-change baseline must read that same address, since the earlier 1201 to 1202 figures came from the WSL node.

Baseline before the change, measured on the then-current address: `GET /v1/models` total 1202, split `composync` 1079, `opencode` 87, `agy` 34, `ollama` 2. The upstream composync catalogue drifts between measurements (1078 was seen earlier the same evening, 1073 after deploy), so no case may hard-code a catalogue total. Compare prefix counts with a tolerance of a few ids, and assert the `oc-composync` count against a fresh `GET /inference/go/v1/models` for the same key (32 at time of writing).

| ID | Check | Command | Expected |
|---|---|---|---|
| T1 | Workspace compiles | `cargo check --workspace` in `avrig-api` | Clean |
| T2 | avrig-ai compiles after removal | `cargo check --workspace` in `avrig-ai` | Clean, no `gateway` package resolved |
| T3 | Legacy folder gone | `Test-Path D:\Cloud\OneDrive\AI\Agentic\avrig-ai\gateway`, `git -C avrig-ai ls-files gateway` | Path absent, no tracked files |
| T4 | No stale member | `Select-String avrig-ai/Cargo.toml -Pattern '"gateway"'` | No match |
| T5 | No stale lock entry | `Select-String avrig-ai/Cargo.lock -Pattern 'name = "gateway"'` | No match |
| T6 | Provider registered | `Invoke-RestMethod http://127.0.0.1:8000/v1/health` | `oc-composync` present |
| T7 | Models advertised | `GET /v1/models`, prefix `oc-composync/` | 32 entries |
| T8 | No virtual ids | Same response, filter `/paid`, `/combo`, `/auto`, `/free`, `/pro` | Zero matches |
| T9 | `paid` rejected locally | POST `{"model":"oc-composync/paid", ...}` | 404 `model_not_found` with no upstream call while the catalogue is reachable. If the catalogue fetch times out, the request is forwarded unchecked and the Go endpoint answers 400, mapped to 502 `upstream_error`; record that variant instead of treating it as a defect |
| T10 | Session forwarded, non-stream | POST with header `x-opencode-session: plan-test-0001` for `oc-composync/deepseek-v4.1-flash` | 200, non-empty content, usage reported |
| T11 | Session forwarded, stream | Same with `"stream": true` | SSE frames, non-empty content delta, terminal `[DONE]` |
| T12 | Second model family | `oc-composync/gpt-6-luna` | 200, non-empty content |
| T13 | Missing header still works | POST without any session header | 200, proving the generated fallback |
| T14 | Fallback precedence | POST with only `x-opencode-session-id: plan-test-0002` | 200, and the unit test asserts the forwarded value equals that string |
| T15 | No leakage to other providers | POST `composync/paid`, an `ollama` model, and `opencode/deepseek-v4.1-flash` | Responses match current behaviour, and a stub assertion shows no session header is sent for providers without `session_header` |
| T16 | Header value reaches upstream | Unit test in `avrig-gateway` with a local listener that parses the raw request and exposes its headers | Received value equals the inbound value; a UUID v4 shape when absent. The existing stub helper does not expose inbound headers, so extend it or add a dedicated listener |
| T17 | Existing provider counts | Compare `/v1/models` split to baseline | `composync`, `opencode`, `agy`, `ollama` match the run's own pre-change measurement within a few ids; no hard-coded total |
| T18 | Deploy parity | Compare the repository and Windows copies, then run the deploy config sync | Both carry the block and stay in sync after deploy. The WSL copy is out of scope by decision and is neither inspected nor modified |
| T19 | Restart idempotence | Restart `avrig`, re-run T7 and T10 | Identical results |
| T20 | No secret leakage | Search both config files for `oc_sk_` | Zero matches |
| T21 | OpenCode really sends the header | Run one OpenCode completion through the `avrig` provider against a model the Go endpoint serves, and capture the inbound request at the gateway (temporary trace or header echo) | `x-opencode-session` present and non-empty, matching the value later forwarded upstream |
| T22 | `{forward}` policy passes an application agent | Stub test: `user_agent = Some("{forward}")`, caller sends `opencode/1.2.3` | Upstream sees `opencode/1.2.3` |
| T23 | Generic agent replaced under `{forward}` | Same provider, caller sends `curl/8.9.1` | Upstream sees `opencode/1.0.0`, proving the guard |
| T24 | Fixed literal and absent policy | Stub tests: `user_agent = Some("avrig/0.3.0")` with any caller, and `user_agent = None` with caller `opencode/1.2.3` | Upstream sees `avrig/0.3.0` in the first case and `opencode/1.0.0` in the second |
| T25 | Client sees the provider | `opencode models` after the client config change | 59 `avrig/` entries: the 27 pre-existing plus 32 `avrig/oc-composync/*`, ids matching `/v1/models` exactly |
| T26 | Client address reaches the Windows node | `GET http://127.0.0.2:8000/v1/health` and the `avrig` `baseURL` value in `.opencode/opencode.json` | `target_triple` ends `windows-msvc`, `oc-composync` in `providers`, and `baseURL` equals `http://127.0.0.2:8000/v1` |

Notes for `tester`: T10 to T12 consume Go subscription allowance, so keep `max_tokens` at 32 or lower and record the `usage.opencode` fields. A 402 or 429 there means the subscription lapsed or the allowance ran out, not a gateway defect. `deepseek-v4.1-flash` occasionally emits artifacts such as `dY\`<` inside its content; direct curl calls show the same, so it is upstream model output.

## Risks and Open Decisions

| Risk | Mitigation |
|---|---|
| Session header not forwarded, Go rejects with 400 | Forward it and keep the generated fallback; T10, T13 and T16 cover both paths |
| Session id changes per request when a client sends none | Only affects callers without the header (curl, document search). OpenCode always sends one, so conversation affinity holds |
| Header leaks to providers that do not want it | Both policies are per provider: no `session_header` means no session header, and no `user_agent` means the fixed default. T15 and T24 assert isolation |
| A provider sets a `user_agent` literal the upstream dislikes | The value is a config line, so it changes without a rebuild; the default stays `opencode/1.0.0` when the key is absent |
| `#[serde(skip)]` on the wire type surprises a reader | Documented as transport-only; serialization is skipped so upstream bodies are unchanged |
| Config deployed before the binary | Every call is 400 `MissingSessionID`. Sequence per the execution plan, verify with T10 |
| Legacy removal breaks the avrig-ai workspace | Dedicated commit, member edit plus lock regeneration, gated by T2 |
| Someone assumes `127.0.0.1:8000` is the Windows gateway | Measured and documented: that address is the WSL node via `wslrelay.exe`. The client was repointed to `127.0.0.2:8000`, and T26 asserts the address and the `windows-msvc` triple |
| Go allowance is finite | Small `max_tokens` in tests, usage recorded per call |

Open decisions for the user, each with a recommended default that ships unless overridden:
1. Resolved by the user: User-Agent is a per-provider config choice, not a global boolean. Each provider picks `{forward}`, a fixed literal, or nothing (the current default). `oc-composync` uses `{forward}`, with generic library agents replaced by the gateway default. `x-opencode-client` and `x-opencode-project` are not forwarded.
2. Resolved by the user: the gateway role is Windows-only, so the WSL node gets no provider block and no key. See Out of Scope item 6.
3. Whether `composync/paid` should also disappear from `/v1/models`. Recommended: leave it. That needs an exclude filter which does not exist in `GatewayProviderConfig`, so it belongs to a later change.
4. Whether `avrig-ai/test` should be cleaned up like `avrig-ai/gateway`. Recommended: no in this plan. It is a separate workspace member with its own duplicated antigravity code, and removing it needs its own dependency audit.

## Out of Scope

1. Model aliasing in the gateway, including emulating `paid` on the Go endpoint.
2. Switching the existing `opencode` provider from `/inference/openai/v1` to the Go endpoint; it uses `OPENCODE_API_KEY` and works as-is.
3. Removing `paid` from `.opencode/opencode.json`, where provider `composync` declares a single model `paid`.
4. Curating the composync catalogue (about 1040 to 1080 ids, drifting between reads).
5. `avrig-ai/test` and `avrig-ai/claude`, which are separate workspace members with their own duplicated antigravity code. Only `avrig-ai/gateway` is removed here.
6. WSL gateway parity. The gateway role is Windows-only by decision, so `/opt/avrig/config/gateway.toml` and the `avrig.service` unit environment are not touched, and no `oc-composync` entries appear on that node.
7. Rotating the plaintext `client_secret` present in `gateway.toml`.

## Review Findings

Audit date: 2026-11-18. Read-only audit of the plan text against the code as it stands today. Evidence was collected by file and line inspection, `git` state, and read-only HTTP probes of `http://127.0.0.1:8000/v1` and `https://opencode.ai/inference/go/v1`. No source, config, or other plan section was modified, and no build or deploy was run.

**Verdict: not ready to execute as written.** The design is sound, nearly every citation resolves, and the external premises check out (Go catalogue is exactly the 32 ids listed). Four defects would block or invalidate verification: unobservable goal 3, stale baseline counts, a missing call-site edit that breaks the `avrig-api` build, and legacy-removal steps that are already committed.

### 1. Goal measurability

| Goal | Verdict | Basis |
|---|---|---|
| 1 Provider registered | pass | `handle_health` lists provider names (`gateway.rs:90-101`), so T6 works; T7 covers the 32 ids |
| 2 Session passthrough | pass | T10, T11, T13, T14, T16 |
| 3 Real completions with `billing_source = "go"` | **fail** | Not observable through the gateway; see below |
| 4 No `paid` alias | pass | T8, T9 (T9 needs the caveat in section 6) |
| 5 Existing providers unchanged | **fail** | Counts are stale and mix baseline with post-change totals |
| 6 Only one gateway implementation | **fail** | Unsatisfiable wording, and already done |
| 7 Survives redeployment | pass, partial | T18, T19, but the WSL config is not in scope (section 2e) |

Goal 3 cannot be measured at the gateway boundary. `ChatResponse.usage` is `OpenAIUsage` (`types.rs:219-233`), a closed struct with three `i64` fields and no `#[serde(flatten)]` catch-all, so an upstream `usage.opencode` object is dropped on deserialize and never re-serialized. Streaming does the same: `filter_direct_usage_stream` re-emits `OpenAIUsage` (`client.rs:1458-1490`). Restate goal 3 as "upstream returns 200 with `billing_source = "go"` (probed directly) and the gateway returns 200 with non-empty content", or widen `OpenAIUsage` in a separate change.

Goal 5's numbers are stale. Live `GET /v1/models` on 0.2.1 today: total 1164, `composync` 1041, `opencode` 87, `agy` 34, `ollama` 2. The plan states 1078 and 1201, which is 37 more `composync` ids than the catalogue now advertises. The goal also needs to separate the invariant ("existing providers keep their counts") from the new total (baseline + 32).

Goal 6 is already delivered and is worded too strongly. `avrig-ai/gateway` is absent and `Cargo.toml` at HEAD has no `"gateway"` member (commit `d4db928 chore(avrig-ai): remove legacy gateway folder and workspace member`). "Only one gateway implementation in the repo tree" remains false by design, because `avrig-ai/test` keeps an OpenAI-compatible gateway server (`test/src/antigravity/server.rs:453`, `test/README.md:52`), which out-of-scope item 5 preserves.

### 2. Target Program Files accuracy

Every cited range resolves and says what the plan claims: `main.rs:105` (providers map), `159-166` (`GatewayProviderConfig`, no `deny_unknown_fields`), `1117-1138` (registration loop), `1135-1137` (the `add_direct_provider` call), `1143-1151` (`resolve_env_var`), `2487` (document search literal); `gateway.rs:178-181` (handler deserializes `ChatRequest` directly); `client.rs:40-46`, `222-238`, `327-358`, `467-494` (function body is 471-494), `1392-1418`, `1420-1456`; `types.rs:170-192`; `avrig-gateway/Cargo.toml:21` (`rand = "0.8"`). Both config files exist and `avrig-api/config/gateway.toml` ends at line 43, so "append after line 43" is correct.

Defects:

- **a. Already-applied removal.** `avrig-ai/Cargo.toml:7` does read `"crates/avrig-sdlc", "test", "gateway", "claude",` at HEAD `f6f30d6`, so the citation was accurate when written. It is now committed as removed, `avrig-ai/gateway` does not exist, and `avrig-ai/Cargo.lock` has no `name = "gateway"`. Phase 4 step 1 (`git rm -r gateway`) will fail on a missing path. Steps 1 to 3 are done; T3, T4, T5 pass before any work.
- **b. Wrong citation.** `avrig-api/scripts/deploy.ps1:33` is `$serviceName = 'avrig'`. The file contains no `Environment` or Machine-scope handling at all, so it does not evidence "Machine scope is visible to the NSSM service". Replace the citation or mark the assumption unverified.
- **c. Missing call sites.** `add_direct_provider` has four callers, and the fourth parameter breaks all of them: `main.rs:1136` (listed), `tests/gateway_integration_test.rs:38` and `:216` (not listed), and the in-crate helper at `client.rs:1859-1865` (already updated to pass `None`). Until the two test call sites are fixed, `avrig-api` does not compile against the changed crate. The three `ChatRequest` literals named in the plan are correct and complete (`main.rs:2487`, `tests:95`, `tests:139`); every other construction goes through `serde_json::from_value` (`client.rs:1570`, `client.rs:1824`, `converter.rs:986`, `:1080`, `:1338`, `:1416`), and `avrig-ai/test` has its own unrelated type at `test/src/antigravity/types.rs:168`.
- **d. Config is not versioned.** `avrig-api/config/gateway.toml` is gitignored (`avrig-api/.gitignore:10`), so the repository copy is a machine-local file. The plan's "both config files must carry the block" is a local-state guarantee only, and T18 compares two local files.
- **e. Third config omitted.** The WSL node has `/opt/avrig/config/gateway.toml` with only `ollama`, `opencode`, and `composync`, and `deploy.ps1:126-157` copies only the binary to Linux. Neither the file list nor T18 covers it, and `Infra` restarts `avrig.service` there.

### 3. `#[serde(skip)]` transport field

Pass, with one required wording fix. The upstream body is unchanged: both executors serialize with `.json(input)` (`client.rs:1399-1402`, `1427-1430`), and `skip` removes the field in both directions, so the JSON is byte-identical. `Option<String>` satisfies the `Default` bound that `skip` requires on deserialization. A side benefit worth stating: a client cannot set the value through the JSON body, and the handler overwrites it unconditionally anyway.

Threading a parameter instead is not materially better. It would change `chat_completion` (`client.rs:530`) and `chat_completion_stream` (`client.rs:656`) plus their four call sites (`gateway.rs:189`, `gateway.rs:251`, `main.rs:2598`, three crate tests) for about the same edit count, while still requiring the handler change. Keep `serde(skip)`, keep the doc comment, and keep the field non-serializing.

One plan-text correction: "Needs `use rand::RngCore;`" is true against HEAD, but the import is already present in the current worktree (`client.rs:18`) and `rand::thread_rng().fill_bytes` is already used at `client.rs:1413`.

### 4. Header precedence and case handling

Pass. `HeaderMap::get` is case-insensitive because header names are normalized to lowercase and `AsHeaderName for &str` parses case-insensitively, so the uppercase `X-Session-Id` literal resolves correctly. The three candidates are distinct names and cannot collide. Preferring `x-opencode-session` is the right call, and not an arbitrary choice: it is the field OpenCode itself sets when it talks to its own Go provider, so forwarding it reproduces a direct call, whereas `x-opencode-session-id` carries a different value and would deviate.

The premise is verified statically: the strings `x-opencode-session`, `x-opencode-session-id`, `X-Session-Id`, `x-session-affinity`, and `x-opencode-project` all appear in `d:\nodejs\.npm\global\node_modules\@opencode\cli\bin\opencode.exe` (259,702,664 bytes). What is not verified anywhere in the plan is that these headers actually reach a custom OpenAI-compatible provider at runtime; see the matrix gap in section 6.

### 5. Opt-in isolation

Pass. Forwarding is gated on `Option<String>` (`client.rs:47-48`, `1441-1443`, `1472-1474`), and only the new `oc-composync` table sets it (`config/gateway.toml:30-43` sets nothing for `ollama`, `opencode`, `composync`). The Antigravity and SIWC paths never call the `execute_direct_provider_*` functions, so they cannot gain a header. Crate tests already assert both sides (forwarded and absent) at `client.rs:2098-2157`.

Gap: an empty or whitespace `session_header` value would reach `req::header("")` and panic on the request path, because reqwest panics on an invalid header name. Validate or skip blank values at registration so a bad config fails at startup, not per request.

### 6. Test matrix

Coverage shape is adequate: forwarded value (T10, T16), generated fallback (T13, T16), non-leak (T15, T16), `paid` rejection (T8, T9), catalogue count (T7, T17), deploy parity (T18), restart (T19), secret hygiene (T20, and the `oc_sk_` prefix is correct for the actual key format). Gaps:

1. Goal 3's `billing_source` assertion cannot pass through the gateway (section 1).
2. T9's "no upstream call" holds only when the catalogue is `Ready`. On a cold cache the validation itself performs `GET /models` (`client.rs:391-395`) and still rejects, so no `/chat/completions` call is made. But a catalogue failure (3s `CATALOGUE_TIMEOUT`, `client.rs:123`) skips validation (`client.rs:482-484`), the request goes upstream, and Go's 400 "Model paid isn't included in OpenCode Go" does not match `reports_unknown_model` (`client.rs:81-110`), so the caller sees 502 `upstream_error`, not 404. T9 must state "warm the catalogue, expect 404 with no `/chat/completions` call" and record the 502 degradation.
3. T15's assertion needs header capture that does not exist: `spawn_stub_provider` (`tests/gateway_integration_test.rs:178-211`) reads the request head into `head` and discards it. Name the capture change explicitly.
4. No case tests `session_header_value` itself: precedence with all three headers present, blank value, and a non-UTF8 value. Add a unit test beside the helper.
5. No case proves OpenCode's headers arrive at all. One capture run (OpenCode, then gateway, then stub provider) would convert the binary-archaeology premise into evidence.
6. T8's `/free`, `/pro`, `/auto` filters return zero matches today only because the 32 ids use `-free` and `-pro` suffixes. That is fine, but the weaker filter should be stated so nobody "fixes" it later.

### 7. Release policy

The bump level is correct. This is a new provider plus one optional config field plus a passthrough, all backward compatible; `add_direct_provider` is internal with a single consumer and `avrig-gateway` stays at 0.1.0, so `patch` would understate it and `major` is unwarranted. Tagging mechanics match `scripts/release.ps1`: `$RepoOrder` covers all four repos (`:22`), the annotated tag equals the version string (`:165`), and push plus `git ls-remote --tags` verification happen at `:173-175` and `:195`.

Two mechanical gaps. The plan has no step that commits the feature work in `avrig-lib` and `avrig-api` before the release, and `release.ps1:142` runs `git add -A` then commits everything staged, so unrelated pending changes ride into the tagged commit. That is not hypothetical: `avrig-lib` is dirty right now (three files, 719 insertions) and `avrig-ai` holds about thirty untracked or moved plan files. Second, the plan text omits the push and remote-verification step that the policy requires, even though the script performs it; the report requirement (SHA, tag, branch per repo) should be stated.

### 8. Legacy removal independence

Pass on independence, fail on timing. Nothing depends on the old package: only `avrig-api` depends on `avrig-gateway` (`avrig-api/Cargo.toml:19`), no Makefile target references the folder, no script or CI file does, and the ten files in `avrig-ai/.opencode/agents/` never mention it. Nothing references `multi_client_sessions`, and `avrig-ai/migrations` does not exist. The removal is committed, so it cannot break this feature and a revert can stand alone.

Residual: `test/README.md:52` still calls its own server the "Rust version of Go gateway", which invites confusion once the plan claims one implementation. Note it in out-of-scope item 5 rather than editing it here.

### Implementation state observed during the audit

The worktree already contains part of this plan, uncommitted, and `avrig-api` lags behind: `types.rs` has `session_id`, `client.rs` has `session_header`, `session_id_for`, `new_session_id`, and the three tests described in T16, while `gateway.rs` still lacks the `HeaderMap` capture and `main.rs:2487` plus `tests:95` and `:139` still lack `session_id`. Until those three land, `avrig-api` will not compile against the changed crate. The plan file list is correct about which sites need it, so this is a sequencing note, not a plan defect.

### Required corrections

1. Rewrite goal 3 around an externally observable criterion, or scope the `billing_source` check to a direct upstream probe (`types.rs:219-233` explains why the gateway cannot surface it).
2. Replace the goal 5 and T17 numbers with a baseline captured at test time; current live values are total 1164, `composync` 1041, plus 32 for the new provider.
3. Reword goal 6 to "the legacy `avrig-ai/gateway` folder and its workspace membership are gone", and mark Phase 4 removal steps done in `d4db928`; delete `git rm -r gateway` and the member edit, and reassign the lockfile confirmation to `build`.
4. Add `avrig-api/tests/gateway_integration_test.rs:38` and `:216` to the mandatory file list for the fourth `add_direct_provider` argument.
5. Replace the `deploy.ps1:33` citation with real NSSM/environment evidence or label the assumption unverified, and record that the repo `gateway.toml` is gitignored (`avrig-api/.gitignore:10`).
6. Bring `/opt/avrig/config/gateway.toml` into configuration scope (or declare the WSL node explicitly out of scope) and extend T18 to it, since `deploy.ps1` syncs only the Windows config.
7. Tighten T9: warm the catalogue, expect 404 `model_not_found` with no `/chat/completions` call, and document the 502 `upstream_error` degradation when the catalogue fetch fails.
8. Add three matrix cases: a direct unit test of `session_header_value`, header capture in `spawn_stub_provider` for T15, and one OpenCode-originated end-to-end capture.
9. Add explicit commit steps for `avrig-lib` and `avrig-api` before Phase 6, plus push and `git ls-remote --tags` verification, because `release.ps1:142` stages everything with `git add -A`.
10. Reject or skip a blank `session_header` at registration so a malformed config cannot panic the request path.

### Resolution of audit corrections

| # | Correction | Resolution |
|---|---|---|
| 1 | Goal 3 unmeasurable through the gateway | Goal 3 rewritten around HTTP 200 plus non-empty content; billing confirmed by direct curl, `OpenAIUsage` deliberately not widened |
| 2 | Baseline stale | Baseline restated from a fresh read (1202 total, `composync` 1079, `opencode` 87, `agy` 34, `ollama` 2) and the matrix now requires a test-time measurement, since the upstream catalogue drifts between reads (1164/1041 was observed minutes apart from 1202/1079). No case may hard-code a total |
| 3 | Legacy removal already delivered | Removal section rewritten as verification of `d4db928`, with `git rm` and the member edit removed; goal 6 reworded to the folder plus workspace membership; `avrig-ai/test` and `avrig-ai/claude` copies acknowledged |
| 4 | Missing test call sites | `avrig-api/tests/gateway_integration_test.rs` call sites 38 and 219 added to the mandatory file list |
| 5 | Deployment citations | `deploy.ps1:33` reworded to 33-34 with the claim narrowed to service naming and stop/start; repository config recorded as gitignored at `avrig-api/.gitignore:10` |
| 6 | WSL config out of scope | Three-copy table added under Configuration, WSL runtime named explicitly, T18 extended, Environment Design updated |
| 7 | T9 imprecise | T9 now requires a warm catalogue for the 404 and documents the 502 `upstream_error` degradation when the catalogue fetch fails |
| 8 | Missing matrix cases | Added as unit-test requirements to `be`: `session_header_value` precedence, blank handling, and non-UTF8; stub header capture named in T15/T16; one OpenCode-originated capture run is optional evidence, tracked as T21 below |
| 9 | Commit and push steps | Feature-commit and release rows split in the execution plan, with push plus `git ls-remote --tags` verification and the SHA/tag/branch report |
| 10 | Blank `session_header` panic | `be` instructed to normalise a blank or whitespace `session_header` to `None` at registration |

Correction 8's OpenCode capture is worth one extra case, since the header premise rests partly on inspecting the client binary rather than on an observed gateway request. It is filed as T21 in the main matrix, alongside T22 to T24 for the User-Agent policy.

### Revision: User-Agent becomes a per-provider policy

The user rejected a boolean `forward_user_agent` flag. Every provider now chooses in config, so the same mechanism serves `{forward}`, a fixed literal, or the existing default:

| `user_agent` value | Outbound `User-Agent` |
|---|---|
| absent, or blank | `opencode/1.0.0` (unchanged for every existing provider) |
| `"{forward}"` | the caller's agent when it identifies an application, else `opencode/1.0.0` |
| any other literal, e.g. `"avrig/0.3.0"` | that literal, trimmed |
| `"{env:VAR}"` | the resolved variable, then interpreted by the rules above |

`oc-composync` sets `user_agent = "{forward}"`. Design, dispatch code, runtime flow, T22 to T24, the target file list, and the resolved-decision wording above all reflect this. `forward_user_agent` is removed rather than kept alongside.

### Verification record 2026-11-18 (tester)

Executed after deploy. Gateway under test is the Windows node at `http://127.0.0.2:8000` (loopback alias), `target_triple x86_64-pc-windows-msvc`, 6 accounts, `semver 0.2.1`, build commit `1b9a25a`. Repo HEADs: `avrig-ai d4db928`, `avrig-lib c814cdf`, `avrig-api 1b9a25a`. Deployed `D:\avrig\avrig.exe` SHA-256 `4dd35a92fb2b332bc2aefc5524b81f5541aa9af94e514cc3a777156c43423d93`, and `avrig --version` prints `avrig 0.2.1`.

No bearer token exists (`.secrets` directory absent) and none was created; `/v1/health`, `/v1/models` and every chat call answered without `Authorization`, and no 401 was observed. No source, config, or service state was modified. One restart was attempted for T19 and was refused by the OS, leaving the service untouched.

| ID | Command | Observed | Verdict |
|---|---|---|---|
| T1 | `cargo check --workspace` in `avrig-api` | exit 0, `Finished dev profile` | pass |
| T2 | `cargo check --workspace --exclude avrig-desktop` in `avrig-ai` | exit 0 | pass, with the agreed exclusion |
| T2 residual | `cargo check -p avrig-desktop` in `avrig-ai` | exit 101, `RC2176: old DIB in apps\desktop\src-tauri\icons\icon.ico` | pre-existing, unrelated to this plan |
| T3 | `Test-Path ...\avrig-ai\gateway`, `git -C avrig-ai ls-files gateway` | path False, tracked files 0 | pass |
| T4 | `Select-String avrig-ai/Cargo.toml -Pattern '"gateway"'` | 0 matches | pass |
| T5 | `Select-String avrig-ai/Cargo.lock -Pattern 'name = "gateway"'` | 0 matches | pass |
| T6 | `GET http://127.0.0.2:8000/v1/health` | `oc-composync` among google-antigravity, openai-siwc, composync, ollama, opencode; `ok=true` | pass |
| T7 | `GET /v1/models` filtered to `oc-composync/`, plus a fresh `GET https://opencode.ai/inference/go/v1/models` with the Machine-scope key | 32 and 32, id sets identical (diff 0) | pass |
| T8 | filter `/paid|/combo|/auto|/free|/pro` | 0 matches under `oc-composync/`, 3 globally (`composync/paid`, `composync/free`, `composync/pro`) | pass when scoped as goal 4 requires; matrix wording needs scoping |
| T9 | `POST` `oc-composync/paid`, catalogue warm | 404 `{"type":"model_not_found"}`, gateway log `upstream_status: None`, so no upstream completion | pass |
| T10 | `POST` `oc-composync/deepseek-v4.1-flash`, `x-opencode-session: plan-test-0001`, `max_tokens` 32 | 200, content `OK`, usage 37/13/50, no `usage.opencode` field | pass |
| T11 | same model, `"stream": true`, `max_tokens` 16 | 200, `content-type: text/event-stream`, 7 `data:` frames, terminal `data: [DONE]`; visible deltas were `reasoning_content` with an empty `content` delta | pass under the accepted tolerance in goal 3 |
| T12 | `POST` `oc-composync/gpt-6-luna`, `max_tokens` 32 | 200, content `OK`, usage 13/5/18 | pass, second model family |
| T13 | `POST` `gpt-6-luna` with no session header | 200, content `OK` | pass, generated fallback |
| T14 | `POST` with only `x-opencode-session-id: plan-test-0002` | 200, content `OK`; precedence asserted by `gateway::session_header_tests::opencode_session_id_is_used_alone` | pass |
| T15 | `POST` `composync/paid`; `POST` `ollama/clef-flash:latest`; `opencode/deepseek-v4.1-flash` not run | composync 200 content `OK` unchanged; ollama 502 `upstream_error` because that upstream model does not support chat | pass on the assertion (`provider_without_session_header_sends_none`), partial live coverage |
| T16 | `cargo test -p avrig-gateway` in `avrig-lib` | 50 passed, 0 failed, including `inbound_session_id_reaches_the_provider` and `missing_session_id_is_generated_as_uuid_v4` | pass |
| T17 | two `/v1/models` reads in the same session | first 1238 total (`composync` 1078, `opencode` 87, `agy` 34, `ollama` 2, `oc-composync` 32, `chatgpt` 5), later 1233 total (`composync` 1073, all other prefixes identical) | pass, drift confined to the composync catalogue, 5 ids |
| T18 | SHA-256 of `avrig-api\config\gateway.toml` and `D:\avrig\config\gateway.toml`, block inspection, `deploy.ps1:97-101` | both `237C1707...DA52`, both carry the block, deploy copies repository to destination; the sync itself was not run because it swaps binaries and restarts the service | pass on parity, sync not executed |
| T19 | `Restart-Service avrig`, then T7 and T10 | refused: "Cannot open avrig service on computer '.'", an elevation limit; `/v1/health` re-checked 200 afterwards and the service stayed Running | blocked, no evidence either way |
| T20 | `Select-String oc_sk_` in both config files | 0 matches, the table carries `{env:OPENCODE_COMPOSYNC_API_KEY}` only | pass |
| T21 | `opencode run --standalone -m avrig/oc-composync/gpt-6-luna` | client printed `OK` and the Windows gateway logged the matching `oc-composync/gpt-6-luna` stream request, so client to gateway to Go works; the inbound header value was not captured | partial: chain proven, header value unproven |
| T22 | `forward_policy_sends_the_callers_application_agent` | ok | pass |
| T23 | `forward_policy_still_blocks_library_agents` | ok | pass |
| T24 | `literal_policy_replaces_the_caller_agent`, `absent_policy_keeps_the_gateway_default` | ok | pass |
| T25 | `opencode models` after the address change | 59 `avrig/` entries, 32 `avrig/oc-composync/*`, id sets identical to `/v1/models` (diff 0), the other 27 being agy 13, chatgpt 5, opencode 9 | pass |
| T26 | `GET http://127.0.0.2:8000/v1/health` and `providers.avrig.settings.baseURL` | `x86_64-pc-windows-msvc`, `oc-composync` present, `baseURL` `http://127.0.0.2:8000/v1` | pass |

`cargo test --workspace` in `avrig-api` also exited 0 with 15 + 81 + 5 tests passed and 0 failed, including all 5 `gateway::session_header_tests`.

Billing, the check the plan deliberately moved outside the gateway: one direct `curl` to `https://opencode.ai/inference/go/v1/chat/completions` with `x-opencode-session` and `max_tokens` 16 returned 200 with `usage.opencode.billing_source = "go"`, `cost = 0`, `list_cost = 0.0000093`, `allowance = 0.0000372`. The key was read from Machine scope inside the process and never printed; the response contains no key material. Goal 3's billing half is therefore measured, and the closed `OpenAIUsage` behaviour is confirmed by T10, which surfaced no `opencode` object.

**Deviations between plan text and observed behaviour**

1. T8's "zero matches" holds only when the filter is scoped to `oc-composync/`. Applied to the whole catalogue it matches three `composync` ids that out-of-scope item 3 keeps on purpose. The expectation should read "zero matches under `oc-composync/`".
2. T11 asks for a non-empty `content` delta. At `max_tokens` 16 `deepseek-v4.1-flash` spent the budget in `reasoning_content`, so the `content` delta was empty while reasoning deltas were not. Judged a pass on HTTP status plus non-empty output, per the accepted tolerance.
3. T2 cannot pass with a plain `cargo check --workspace`: `avrig-desktop` fails on `RC2176: old DIB in icons\icon.ico`, which predates this change and is unrelated to the gateway.
4. T17's absolute totals moved during the session (1238 then 1233). The movement is entirely in the `composync` catalogue, 5 ids, which confirms the plan's instruction never to hard-code a total.
5. T15's `opencode/` leg was not exercised, and its `ollama` leg returned 502 because both advertised ollama ids are a reranker and an embedding model, neither of which serves chat. The no-leak assertion rests on the passing unit test rather than on a live call.

**Unresolved, stated rather than guessed**

1. T19 could not run. Restarting the `avrig` service requires elevation this session does not have, so restart idempotence after a config re-read remains unproven by direct observation. Settling it needs one elevated `Restart-Service avrig` followed by T7 and T10.
2. T21 proved the client path but not the header value. The gateway logs no request headers, and a recorder provider cannot be injected without editing client config, because `opencode` 2.3.2 ignored both `OPENCODE_CONFIG` and `OPENCODE_CONFIG_DIR` during model discovery (728 models listed either way, and `Model unavailable: stub/x`). Settling it needs a temporary trace at the gateway or an edited client config, and both were out of bounds here.
3. The analyst audit of goals 1 to 7 could not be dispatched from this session, because nested subagent depth is capped at 1. The per-goal verdict under `## Review Findings` is therefore still owed by `analyst`.

Given T1 to T18, T20 and T22 to T26 pass with the deviations above, and T19 and T21 are blocked by verification environment limits rather than defects, this session supports the release trigger for a `minor` increment, on the explicit condition that the two blocked cases are accepted as unproven. If restart idempotence must be observed before release, T19 needs one elevated run first.

### Goal audit 2026-11-18 (analyst)

Scope: achieved-versus-planned audit of the seven goals against the tester record above and the measured facts reported for this session. No build, deploy, or live model call was run. Three read-only confirmations were taken today: `git log --oneline -1 d4db928` resolves to `chore(avrig-ai): remove legacy gateway folder and workspace member`, `git ls-files gateway` returns 0 entries, and both `avrig-api/config/gateway.toml` and `D:\avrig\config\gateway.toml` carry `[gateway.providers.oc-composync]` at line 45 with `session_header = "x-opencode-session"` and `user_agent = "{forward}"` at 49 and 50. Repo heads read `avrig-ai d4db928`, `avrig-lib c814cdf`, `avrig-api 1b9a25a`.

| Goal | Verdict | Evidence | Residual |
|---|---|---|---|
| 1. Register `oc-composync` on Go endpoint with `{env:OPENCODE_COMPOSYNC_API_KEY}` | met | T6 (`oc-composync` in `/v1/health` providers, `ok=true`), T7 (32 ids, id set identical to a fresh upstream read, diff 0), T20 (no `oc_sk_` in either file, env reference only), T18 plus the config read above | none |
| 2. Forward session id, generate when absent, per-provider User-Agent, `oc-composync` forwards | met | T10 and T11 return 200 where Go answers 400 `MissingSessionID` without a session header, so a session header does reach upstream; T13 (no header, 200) and T16 (`missing_session_id_is_generated_as_uuid_v4`) prove the generated fallback; T14 plus `session_header_tests` prove precedence; T16 (50 passed) proves the forwarded value reaches a real listener; T22 to T24 prove the three User-Agent policies | T21: the exact value OpenCode 2.3.2 emits is unobserved, so per-conversation affinity is proven for the gateway mechanism, not for the stock client |
| 3. Real Go completions, two families, both paths, billing confirmed outside the gateway, no struct widened | met | T10 and T12 (deepseek-v4.1-flash, gpt-6-luna, non-stream, content `OK`), T11 (SSE, 7 frames, terminal `[DONE]`), live gpt-6-luna stream 200 with non-empty output; direct curl `billing_source = "go"`, `cost = 0`; T10 surfaced no `usage.opencode`, so `OpenAIUsage` stayed closed | none, with the T11 tolerance noted below |
| 4. No `paid` alias, `oc-composync/paid` 404 `model_not_found`, no combo or virtual id | met | T9 returns 404 `model_not_found` with `upstream_status: None`, so no upstream completion; T8 scoped to `oc-composync/` returns 0 matches for `paid|combo|auto|free|pro`; 32 advertised ids match upstream exactly | none |
| 5. Existing providers unchanged, no header to providers that do not ask | met | T17: `opencode` 87, `agy` 34, `ollama` 2 match the goal text exactly across two reads; the only movement is the `composync` catalogue (1078 then 1073, 5 ids), which the goal declares relative; `chatgpt` 5 appears because the Windows node serves it, not because a named provider changed; T15 `provider_without_session_header_sends_none` and T24 `absent_policy_keeps_the_gateway_default` prove isolation; live `composync/paid` unchanged 200 | `composync` absolute count has no pre-change read on `127.0.0.2`, so equality rests on in-session stability plus drift confinement |
| 6. Remove legacy folder and workspace membership as `d4db928` | met | T3 (path absent, 0 tracked files, reconfirmed today), T4 and T5 (0 matches), T2 (`cargo check --workspace --exclude avrig-desktop` exit 0); T2 residual is a pre-existing `RC2176` icon resource in `avrig-desktop`, untouched by this plan | none; `avrig-ai/test` keeps its own gateway server by the goal's own wording and out-of-scope item 5 |
| 7. Survive redeployment, both config files carry the block | met | T18 both files identical SHA-256 `237C1707...DA52` and both carry the block, reconfirmed at lines 45-50 today; `deploy.ps1:97-101` copies repository to runtime; the deploy run's own stop/start loaded `0.2.1` commit `1b9a25a` and left `oc-composync` registered with 32 ids | T19: a second, independent restart was not observed; survival is evidenced by the deploy's own restart, not by a separate elevated run |

Verdicts resting on residuals: goal 2 rests partly on T21, goal 7 rests partly on T19. Goals 1, 3, 4, 5 and 6 rest on passing cases only. Goals 5 and 7 carry the two qualifications above, neither of which is an implementation defect.

Matrix wording items found while judging (documentation only, no code impact): T8 states "zero matches" without the `oc-composync/` scope that goal 4 and the observed result require; T11 asks for a non-empty `content` delta while the observed stream at `max_tokens` 16 delivered `reasoning_content` deltas and an empty `content` delta; T2 cannot pass without the `--exclude avrig-desktop` qualifier that was applied here.

**Release trigger**

Goals: 7 of 7 met, 2 with the named qualifications. Tests: 24 of 26 pass as written; T19 is blocked by an elevation limit and T21 is partial, both environment limits rather than implementation defects. The literal reading "all tests PASS" is therefore not satisfied.

**Verdict: go, with `minor` confirmed.** The increment is correct under SemVer 2.0.0: a new backward-compatible provider plus one optional per-provider config field plus a passthrough, with no breaking API change. The go rests on accepting T19 and T21 as recorded environment limits with substitute evidence, because for both the behaviour under test is exercised by other passing means: the deploy's stop/start plus the post-restart `0.2.1`/`1b9a25a` health state covers config re-read for goal 7, and the 200 responses through the gateway plus `inbound_session_id_reaches_the_provider` cover header forwarding for goal 2. If the release policy is enforced literally, the verdict becomes no-go until one elevated `Restart-Service avrig` closes T19; T21 cannot be closed in this environment at all without a temporary gateway header log or an edited client config, so it should be moved to accepted-with-note rather than left open.

Release mechanics to confirm at execution, both already in the plan: bump `0.2.1` to `0.3.0` in `avrig-ai/Cargo.toml`, `apps/web/package.json` and `avrig-api/Cargo.toml` through `make release-minor`, and publish tag `0.3.0` in all four repositories with `git ls-remote --tags origin` verification and the per-repo SHA, tag and branch report.
