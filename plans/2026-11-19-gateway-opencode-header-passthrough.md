---
title: "Gateway Client-Header Analysis and Per-Provider Passthrough, OpenCode Free-Tier Retry"
status: draft
created: 2026-11-19
owner: plan (authoring), analyst (gate), tester (verification), be, build, Infra, km (execution)
version_target: 0.4.0
tags:
  - gateway
  - headers
  - opencode
  - free-tier
  - lab
---

# Gateway Client-Header Analysis and Per-Provider Passthrough, OpenCode Free-Tier Retry

## Goals and Objectives

1. Give the gateway a header analysis capability: for any inbound chat request, it records the caller's header profile (name, length, truncated SHA-256, scheme) in redacted form suitable for logs and lab capture, and never records a secret value.
2. Give each direct provider a declarative passthrough allowlist, so a provider can ask for specific caller headers (session ids, project, client, trace context) without the gateway hardcoding one header name per provider. The gateway's own `Authorization`, `Host`, and framing headers are never overridable by passthrough, and no credential-bearing name is eligible at any layer.
3. Attach the passthrough policy to the existing `opencode` provider, switch that provider to the **console OAuth credential** it actually needs, and retry `opencode/deepseek-v4.1-flash-free` through the gateway. Expected result: **200** when the caller is the OpenCode CLI, because the credential becomes `st_` and the body is already the real CLI shape. A hand-written minimal-body curl is expected to still 429, and the matrix records both. This replaces the earlier, weaker goal of merely documenting a 502.
4. Verify the free-model capability that already works: `beam-free`, `longcat-2.5-free`, and `hy4-flash-free` serve through `oc-composync` today, and all four Go free ids including `iceman-contributor-free` are already present in the client picker (`opencode.json` lines 38, 51, 53, 58). Confirm the entries and the routes behind them rather than creating them.
5. Keep a reproducible experiment in `avrig-ai/lab/` that captures the real wire identity the OpenCode CLI presents, so this class of question stays answerable by measurement rather than by guesswork.
6. Leave every existing provider's behaviour unchanged when it declares no passthrough, proven by the existing session and User-Agent suites still passing.

Non-goal: fabricating request bodies. The gate keys on the real CLI body shape, so the gateway forwards what the caller sent. It does not pad or impersonate content to satisfy an anti-abuse check.

## Context and Measured Evidence

### The problem, and the surprise

The free model `opencode/deepseek-v4.1-flash-free` answers 200 through OpenCode's own built-in provider on this machine but 502s through the gateway. The first hypothesis was a header gate. That was tested and rejected. The second was a credential gate, also rejected on its own. The real answer, measured below, is that two conditions must hold together: the **console OAuth credential** and the **real CLI body shape**. Along the way a larger result surfaced: free models already work through the gateway on the Go path, just not that one.

### 2026-11-19 breakthrough measurements

| Probe | Result |
|---|---|
| `POST /inference/openai/v1/chat/completions` `deepseek-v4.1-flash-free`, **no `Authorization` at all** | 429 `FreeUsageLimitError`, `server-timing: gateway;dur=5` |
| Same path, `Authorization: Bearer garbage` | 401 `authentication_error` |
| Paid `deepseek-v4.1-flash` with the **same** `OPENCODE_API_KEY` that 429s the free model | **200**, `usage.opencode.billing_source = "balance"`, `cost = 0.0000192` |
| Native client with `OPENCODE_API_KEY` **removed from its environment** | **200**, still works |
| Console `st_` token before and after a native run | unchanged, no rotation, valid to 2026-12-15 |
| `x-opencode-ticket` = `st_` + `x-opencode-org-id` + `Bearer st_` | 429 |
| `beam-free`, `longcat-2.5-free`, `hy4-flash-free`, `iceman-contributor-free` on the OpenAI path | all 429 |
| Same four on the **Go** path (`/inference/go/v1`) | three 200, `iceman` 400 privacy gate |
| Free model from WSL egress `182.253.59.190` (Jakarta) | 429, same body |

Four conclusions.

1. **`FREE_LIMIT` is not a credential verdict.** A request with no credential gets the same 429, while the identical credential reaches a paid model at 200. The message "Free models work in OpenCode" is a policy statement about *which client* is calling, decided at `gateway;dur=5`, before any upstream work.
2. **It is not IP-bound.** Two different egress addresses produced the same 429.
3. **It is not plan-quota-bound.** `Retry-After` counts down (82628, then 77303, then 77136) so a bucket exists, but the bucket cannot be refilled by waiting if a paid model on the same key succeeds immediately.
4. **Free models already serve through the gateway on the Go subscription:**

| Through `http://127.0.0.2:8000/v1` | Result |
|---|---|
| `oc-composync/beam-free` | **200 OK** |
| `oc-composync/longcat-2.5-free` | **200 OK** |
| `oc-composync/hy4-flash-free` | **200 OK** |
| `oc-composync/deepseek-v4.1-flash-free` | 404 `model_not_found`: "Provider 'oc-composync' does not offer model ..." |

The 404 is the gateway rejecting the model locally against the Go catalogue before any upstream call, because `validate_direct_provider_model` (`client.rs:496-520`) enforces the catalogue. Called directly, the same model returns 400 "isn't included in OpenCode Go". Both statements describe the same exclusion, one local and one upstream.

Verified end to end with the real client: `opencode run -m avrig/oc-composync/beam-free` returned `free-works`.

The Go catalogue holds exactly four free ids: `beam-free`, `iceman-contributor-free`, `longcat-2.5-free`, `hy4-flash-free`. `deepseek-v4.1-flash-free` is deliberately not among them, so it is unreachable on the Go path by design. `iceman-contributor-free` is gated by an org privacy toggle at `https://opencode.ai/console/org_01M72468PMBQ51MKCPZFK55TVC/settings/privacy#training`, an account setting rather than a gateway concern.

### What the gateway does today

| Fact | Location |
|---|---|
| The chat handler reads exactly two inbound headers | `avrig-api/src/gateway.rs:183-184` |
| Session fallback chain `x-opencode-session`, `x-opencode-session-id`, `X-Session-Id` | `avrig-api/src/gateway.rs:301-313` |
| `ChatRequest` carries two transport-only `#[serde(skip)]` fields | `avrig-lib/crates/avrig-gateway/src/antigravity/types.rs:192-197` |
| Provider config has `session_header` and `user_agent` only | `avrig-api/src/main.rs:159-171` |
| Registration passes five arguments to `add_direct_provider` | `avrig-api/src/main.rs:1140-1148` |
| `DirectProviderAccount` stores name, base url, keys, key cursor, two header settings | `avrig-lib/crates/avrig-gateway/src/client.rs:41-52` |
| Outbound headers are only User-Agent, Authorization, session header | `avrig-lib/crates/avrig-gateway/src/client.rs:1535-1544`, `1566-1575` |
| No arbitrary header forwarding anywhere | confirmed across `client.rs`, `antigravity/*`, `siwc/client.rs` |
| Upstream response headers never inspected | no `resp.headers()` outside a test stub |
| Exactly one `http` crate version, 1.5.0, shared by axum 0.8.9 and reqwest 0.12 | `avrig-api/Cargo.lock` |

### What the OpenCode CLI actually sends

Captured 2026-11-19 by `lab/capture-server.ps1` against a temporary `labcapture` provider (`lab/captures/20261119-090543-531-001.json`), 16 headers in arrival order:

```
b3: d7f72eef7d69df312bbb9f6c352c7394-e342081197c6afcb-1-7b77432e06f95d38
traceparent: 00-d7f72eef7d69df312bbb9f6c352c7394-e342081197c6afcb-01
x-opencode-client: cli
x-opencode-project: 0611795a0b9bf6d0f0227769ea038417082ab59e
x-opencode-session: ses_e0e7292cdffe0bU6KCVXwth0GP
x-opencode-session-id: ses_e0e7292cdffe0bU6KCVXwth0GP
x-session-affinity: ses_e0e7292cdffe0bU6KCVXwth0GP
x-session-id: ses_e0e7292cdffe0bU6KCVXwth0GP
Connection: keep-alive
Content-Length: 2119
Content-Type: application/json
Accept: */*
Accept-Encoding: gzip, deflate, br, zstd
Authorization: Bearer <stub value, 5 chars>
Host: 127.0.0.1:8899
User-Agent: opencode/latest/2.3.2/cli
```

Two facts shape the design:

1. The client sends **four** session-shaped headers with one value. The gateway reads the first and drops the rest.
2. The user agent is `opencode/latest/2.3.2/cli`, an application agent that the existing `{forward}` policy already passes through, since it matches no entry in the generic library list.

### Root cause, isolated 2026-11-19

The gate is not the credential alone and not the headers alone. It is **two independent conditions, both required**, and neither was previously tested in combination.

Condition one is the **credential type**. The same request body sent with the console OAuth token returns 200, sent with `OPENCODE_API_KEY` returns 429:

| Body | Credential | Result |
|---|---|---|
| native 66 KiB CLI body | console OAuth `st_` token (39 chars, sha `cf4246c7`) | **200** |
| identical body | `OPENCODE_API_KEY` (51 chars, `oc_sk_` prefix, sha `deba1ef7`) | 429 `FreeUsageLimitError` |

Condition two is the **body shape**. Holding the `st_` token constant and varying the body:

| Body variant | Result |
|---|---|
| exact 66 KiB CLI body (`system` 49 KiB, `tools` 13, `stream: true`, `stream_options`) | **200** |
| `tools` removed | 429 |
| `stream: false` | 429 |
| `stream_options` removed | 200 |
| 1 user message only | 429 |
| generic filler system prompt at 52 KiB | 429 |
| no system message | 429 |
| 1 message plus 13 tools | 429 |

The asymmetry in that table is the answer: `tools` removed gives 429 but `stream_options` removed gives 200, so the trigger is not raw size and not streaming alone. The full asset shape is what the upstream classifier recognises, and the gating predicate evidently looks at `system` plus `tools` together. A generic 52 KiB filler prompt fails while the genuine 49 KiB system prompt passes, so it is the content, not the length.

This is an anti-abuse check keyed to real OpenCode requests. It is why every synthetic probe 429'd, including a request with no `Authorization` header at all, and why the same `OPENCODE_API_KEY` happily serves paid models at 200.

The gateway cannot satisfy condition two honestly for a caller's own request: it must forward whatever body the caller sent, and padding a body to look like the OpenCode CLI would be fabricating request content. The legitimate fix is condition one, which the gateway does control: **`opencode` should use the console OAuth token, not `OPENCODE_API_KEY`**. That token is already on this machine, in the client credential store, and the console config confirms it is the provider identity the client itself uses:

```json
"env": ["OPENCODE_CONSOLE_TOKEN"],
"options": { "apiKey": "{env:OPENCODE_CONSOLE_TOKEN}",
             "headers": { "x-opencode-org-id": "wrk_01KPCJ5BP7MCCSBJFR030NGD6B" } }
```

Read from `https://opencode.ai/console/api/config` with the stored token, 2026-11-19. So the native provider is `st_` token plus `x-opencode-org-id`, exactly as measured.

Practical consequence for this plan: the `opencode` provider's `api_key` must resolve to the console OAuth token rather than `{env:OPENCODE_API_KEY}`, and `x-opencode-org-id` must be sent. Reaching a 200 through the gateway also requires the caller's body to be the real CLI shape, which is true when the caller is the OpenCode client and false for a hand-written curl. So the expected results differ by caller, and the matrix records both.

What this does **not** require is header passthrough. The root cause is credential source plus body shape. Header passthrough remains a legitimate capability and objective 2 still stands, but it is not the fix for this defect, and the plan does not claim it is. `x-opencode-org-id` is a static configured header, not caller passthrough, which is a smaller and safer change than relaying caller state.

### Open design question: token rotation

The `st_` token expires **2026-12-15**, 26 days from the measurement date. A copied token therefore rots. The refresh path could not be located: the CLI advertises `grant_types: ["authorization_code","refresh_token"]` with `token_endpoint_auth_method: "none"` in `https://opencode.ai/oauth/opencode/client.json`, and the credential row records `methodID: device` against `server=https://opencode.ai/console`, so the flow is device-code OAuth. But `/oauth/token`, `/oauth/opencode/token`, `/api/accounts/oauth/token`, and every `/console/api/**/token` variant returned 405 or 404, and neither `GET /oauth/token` nor the well-known metadata resolves.

Three options, and this is a decision for the user:

| Option | Durability | Effort | Risk |
|---|---|---|---|
| A. `{file:...}` with the current `st_` token, refreshed by hand before expiry | 26 days | smallest | silent failure at expiry if the refresh is forgotten |
| B. Gateway reads the token from the client credential store (`opencode.db`) at start and on 401, i.e. piggybacks on the client's own rotation | tied to the client session | medium, needs a sqlite read and a 401 retry | couples the service to the client's private database layout |
| C. Implement device-code OAuth in the gateway, so it mints and refreshes its own token | indefinite | largest, needs an interactive login once | new auth surface, and the device flow was not reverse-engineered here |

Recommendation: **A now, B if the token must outlive the client login.** A is honest, small, and unblocks the 200 today. C is the clean answer but should not gate this plan. Whichever is chosen, the plan must state the rotation story, because shipping a credential that silently dies in 26 days is the same defect class as the 502 it replaces.

### Why the previous attempts failed

The lab's in-process `fetch` trace was chasing the wrong variable. Every prior sweep varied headers with a minimal body and the wrong credential, so every cell returned 429 and the signal was invisible. The body-shape table above is what the existing `lab/body-final/` results already contained; the earlier reading of those results simply did not test the credential axis against the passing bodies.

## Key Detailed Design

### Program Design

#### 1. Transport fields on `ChatRequest`

Add one transport-only field beside the existing two, following the same precedent:

```rust
/// Inbound request headers the caller supplied, captured at the edge and already stripped of
/// credentials and framing headers. Transport-only, never serialized upstream.
#[serde(skip)]
pub forwarded_headers: Vec<(String, String)>,
```

A new field rather than generalizing `session_id` and `user_agent`: both existing fields feed named policies with their own tests, so leaving them intact means zero regression risk on the shipped Go path.

Only **three** true struct literals need editing. The other seven listed sites are `serde_json::from_value` deserializations, and `#[serde(skip)]` defaults the field automatically during deserialization, so they require no change:

| File | Line | Kind |
|---|---|---|
| `avrig-api/src/main.rs` | 2509 | literal, needs the field |
| `avrig-api/tests/gateway_integration_test.rs` | 97, 143 | literals, need the field |
| `avrig-lib/crates/avrig-gateway/src/client.rs` | 1866, 2418, 2638 | `from_value`, no change |
| `avrig-lib/crates/avrig-gateway/src/antigravity/converter.rs` | 985, 1079, 1337, 1415 | `from_value`, no change |

`avrig-ai/test/src/antigravity/types.rs` holds an **independent** `ChatRequest` in a separate crate. Do not touch it.

#### 2. New module `avrig-gateway/src/header_policy.rs`

Pure logic, unit-testable without a server. Uses `reqwest::header::{HeaderMap, HeaderName, HeaderValue}`, so no new dependency. Type compatibility is already proven: one `http` 1.5.0 in the lock means `axum::http::HeaderMap` handed in by the handler **is** this type, with no shim.

```rust
/// One passthrough rule: an exact header name, or a case-insensitive prefix ending in `*`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HeaderPattern { prefix: String, exact: Option<String> }

impl HeaderPattern {
    /// Parse `"x-opencode-project"` or `"user-agent"`. None for a blank or malformed rule.
    pub fn parse(raw: &str) -> Option<Self>;
    /// Match against a lowercase header name.
    pub fn matches(&self, name: &str) -> bool;
}

/// Headers the gateway always owns; passthrough may never supply them.
///
/// This list is the security boundary, so it is deliberately broad. It covers the standard
/// credential and framing headers plus the credential-bearing names observed in this
/// ecosystem, notably `x-opencode-ticket` which carries a live console `st_` token.
pub const NEVER_RELAY: &[&str] = &[
    // Credentials and auth
    "authorization", "proxy-authorization", "www-authenticate", "x-api-key", "api-key",
    "x-auth-token", "x-goog-api-key", "x-opencode-ticket", "x-opencode-org-id",
    // Cookies
    "cookie", "set-cookie",
    // Framing and transport, which reqwest must own
    "host", "content-length", "content-type", "connection", "transfer-encoding",
    "accept-encoding", "upgrade", "te", "trailer", "keep-alive", "proxy-connection",
];
```

`x-opencode-ticket` and `x-api-key`, `api-key`, `x-auth-token`, `x-goog-api-key`, `www-authenticate` are additions demanded by the audit. Omitting `x-opencode-ticket` while shipping an `x-opencode-*` wildcard would have relayed a live console credential, which directly contradicted the plan's own security claim. `x-opencode-org-id` is denied as well: it is an account identifier, not needed for inference, and relaying it spreads tenant identity to a third party for no benefit.

The deny list is applied at **both** capture and apply time. Capture alone is judged insufficient: a future config edit could introduce a pattern that reaches a name added to the list later, so the apply-time check is the second gate.

```rust
/// Capture inbound headers for possible relay.
///
/// Drops `NEVER_RELAY`, non-UTF-8 values, blanks, and anything over `MAX_RELAYED_VALUE`.
/// Caps at `MAX_RELAYED_HEADERS`. Names lowercased; first occurrence wins.
pub fn capture_relayable(headers: &HeaderMap) -> Vec<(String, String)>;

/// Resolve which captured headers a provider policy permits, in policy order, deduplicated.
///
/// Re-checks `NEVER_RELAY` so a policy edit can never resurrect a denied header.
pub fn select_relayable<'a>(
    captured: &'a [(String, String)],
    policy: &[HeaderPattern],
) -> Vec<(&'a str, &'a str)>;
```

Constants: `MAX_RELAYED_HEADERS = 32`, `MAX_RELAYED_VALUE = 8192`.

#### 3. Redacted header analysis

```rust
/// Redacted view of one inbound header, safe to log or persist.
pub struct HeaderFact {
    pub name: String,
    pub length: usize,
    pub scheme: Option<String>,   // "Bearer" when the value is a bearer credential
    pub sha256_16: String,        // first 16 hex chars of the value digest
    pub redacted: bool,
}

/// Build the header profile for a request.
///
/// A value is redacted when the name matches `NEVER_RELAY`, when it carries a `Bearer`
/// scheme, or when it looks like a token (long, and prefixed `sk-`, `oc_sk_`, `st_`, `ghp_`,
/// or `eyJ`).
pub fn header_profile(headers: &HeaderMap) -> Vec<HeaderFact>;
```

`sha2` is already an `avrig-gateway` dependency (`antigravity/oauth.rs:11`, `siwc/oauth.rs:8`), so the digest adds no crate. Emission: one `tracing::info!` in the chat handler, gated by `analyze_headers`, because the deployed runtime config runs at `level = "info"` (`D:\avrig\config\config.toml:2`) and a `debug` emission would be invisible on the node. Only `HeaderFact` fields are logged, never a raw value. The line is emitted once per request, so its volume is bounded by request rate, which loopback-only access already constrains.

Module naming: the file is `header_policy.rs` rather than `headers.rs`, since it holds a relay policy plus a redaction profile rather than generic header utilities, and `header_profile` is the function name rather than `profile`, which is too vague at a call site.

#### 4. Provider policy plumbing

`GatewayProviderConfig` gains two fields:

```rust
/// Header names or `prefix*` patterns to relay from the caller to this provider.
pub forward_headers: Option<Vec<String>>,
/// Emit a redacted inbound header profile at info level for this provider.
#[serde(default)]
pub analyze_headers: bool,
```

`analyze_headers` is a plain `bool` with `#[serde(default)]`, not `Option<bool>`. A tri-state boolean forces an unwrap in the wiring for no benefit, and `analyze_headers = true` parses unchanged either way.

`DirectProviderAccount` gains one field:

```rust
/// Passthrough rules for caller headers. Empty means the provider relays nothing.
pub forward_headers: Vec<HeaderPattern>,
```

`add_direct_provider` takes **one** options argument rather than a sixth positional parameter. Four of its settings are optional, so positional growth reads `None, None, Vec::new()` at every call site and gets worse with each addition.

```rust
/// Optional per-provider settings, so call sites survive future growth.
#[derive(Clone, Debug, Default)]
pub struct DirectProviderOptions {
    pub session_header: Option<String>,
    pub user_agent: Option<String>,
    /// Header names or `prefix*` patterns. Parsed and normalized inside the method.
    pub forward_headers: Vec<String>,
}

pub async fn add_direct_provider(
    &self,
    provider_name: String,
    base_url: String,
    api_keys: Vec<String>,
    options: DirectProviderOptions,
)
```

Parsing lives **inside** `add_direct_provider`, matching the house style at `client.rs:236-251` where `session_header` and `user_agent` are normalized in the method rather than at the call site. It takes `Vec<String>` and parses to `HeaderPattern`, trimming, dropping blanks and unparseable patterns, and degrading to "not forwarded" rather than panicking.

Six registration call sites, each collapsing from five positional arguments to three plus an options value:

| File | Line |
|---|---|
| `avrig-api/src/main.rs` | 1140-1148 |
| `avrig-lib/crates/avrig-gateway/src/client.rs` | 2155, 2407, 2627 |
| `avrig-api/tests/gateway_integration_test.rs` | 38, 222 |

Definition at `client.rs:228`. The audit counted six and is right; the earlier "five" was wrong.

#### 5. Outbound application, in one place

The audit found that both dispatch paths already duplicate three headers (User-Agent, Authorization, session) at `client.rs:1535-1544` and `1566-1575`. Adding a fourth concern to both guarantees drift. So extract one composer and call it twice:

```rust
/// Build a direct provider request with every transport header the gateway sends.
///
/// User-Agent, Authorization, the configured session header, then the relayed set. Gateway
/// owned headers always win, so a relayed value can never replace the credential or framing.
fn direct_provider_request(
    http: &reqwest::Client,
    direct: &DirectProviderAccount,
    key_index: usize,
    input: &ChatRequest,
) -> reqwest::RequestBuilder {
    let url = format!("{}/chat/completions", direct.base_url.trim_end_matches('/'));
    let mut req = http
        .post(&url)
        .header("User-Agent", user_agent_for(direct, input))
        .json(input);
    if let Some(key) = direct.api_key_at(key_index) {
        req = req.header("Authorization", format!("Bearer {}", key));
    }
    if let Some(header) = &direct.session_header {
        req = req.header(header.as_str(), session_id_for(input));
    }
    for (name, value) in select_relayable(&input.forwarded_headers, &direct.forward_headers) {
        if name.eq_ignore_ascii_case("user-agent")
            || direct
                .session_header
                .as_deref()
                .is_some_and(|h| h.eq_ignore_ascii_case(name))
            || is_denied_name(name)
            || is_token_shaped(value)
        {
            continue;
        }
        req = req.header(name, value);
    }
    req
}
```

Three guards, not one. `is_denied_name` re-checks `NEVER_RELAY` at apply time, so a policy edit cannot resurrect a denied header. `is_token_shaped` refuses any value that looks like a credential regardless of its header name, which closes the case where a `Bearer` or `st_` value sits in an unexpected header. Both predicates are shared with `header_profile`, so redaction and refusal cannot drift apart:

```rust
/// True when a header name is owned by the gateway and must never be relayed.
pub fn is_denied_name(name: &str) -> bool;

/// True when a value looks like a credential regardless of header name.
///
/// Length must exceed `MIN_TOKEN_LIKE_LEN` (32) and carry a known prefix: `Bearer `, `sk-`,
/// `oc_sk_`, `st_`, `rt_`, `ghp_`, or `eyJ`.
pub fn is_token_shaped(value: &str) -> bool;
```

`MIN_TOKEN_LIKE_LEN` is a named constant, because the audit correctly noted that "long" was undefined and an unstated threshold would let a test encode a guess.

Prefix rules are also tightened: a pattern must be at least 3 characters before its `*` and must contain a `-`, so a bare `x-*` cannot match `x-api-key` or `x-auth-token`. A pattern that fails this is dropped at registration, the same way a malformed `session_header` degrades today.

Both dispatch functions then become `let resp = direct_provider_request(...).send().await?;`. The deny logic has exactly one home, so a future header cannot be added to one path and forgotten in the other.

#### 5b. Fallback dispatch must not relay

The audit found that `client.rs:664-674` and `731-735` dispatch to `directs.values().next()` when no model prefix names a provider, meaning an unprefixed model reaches an arbitrary provider. Combined with passthrough, caller headers could reach a provider the model never named. That is exactly the missing-prefix trap measured live (H17d): a bare `iceman-contributor-free` fell through and returned an unrelated ToS 403.

Mitigation, both parts required:

1. In the fallback branch, clear `input.forwarded_headers` before dispatch. A provider that was not chosen by the model must not receive caller headers.
2. Assert it with a test: an unprefixed model dispatched through the fallback path sends no relayed header, proven by the stub provider in `client.rs` observing none.

#### 6. Edge capture

One added line beside the two existing ones in `handle_chat_completions`:

```rust
input.forwarded_headers = avrig_gateway::header_policy::capture_relayable(&headers);
```

The edge captures, the provider filters, so one inbound request can serve a provider that wants nothing.

### Target Program Files

Created:

| Path | Purpose |
|---|---|
| `avrig-lib/crates/avrig-gateway/src/header_policy.rs` | `HeaderPattern`, `NEVER_RELAY`, `capture_relayable`, `select_relayable`, `header_profile` |
| `avrig-ai/lab/README.md` | what the experiment measures and how to rerun it |

Edited:

| Path | Change |
|---|---|
| `avrig-lib/crates/avrig-gateway/src/lib.rs` | `pub mod header_policy;` plus re-export |
| `avrig-lib/crates/avrig-gateway/src/antigravity/types.rs` | `forwarded_headers` field |
| `avrig-lib/crates/avrig-gateway/src/client.rs` | `DirectProviderOptions`, account field, `direct_provider_request` composer, fallback clear, unit tests, registration call updates |
| `avrig-api/src/gateway.rs` | capture line, `info` profile emission, `analyze_headers` wiring, unit tests |
| `avrig-api/src/main.rs` | config fields, options construction, registration call, grounded-request literal |
| `avrig-api/config/gateway.toml` | `opencode` block gains `user_agent`, `analyze_headers`, `forward_headers` |
| `D:\avrig\config\gateway.toml` | identical block, because `deploy.ps1` copies the repo file over the runtime file |
| WSL node `/opt/avrig/config/gateway.toml` | same `opencode` block, see the Linux note below |
| `avrig-api/tests/gateway_integration_test.rs` | 3 literals and 2 registrations |
| `avrig-ai/.gitignore` | ignore `lab/` wholesale until a commit decision is made |

Removed: nothing.

### Deployment Target Note

`deploy.ps1` treats the two nodes differently. The Windows branch (`deploy.ps1:96-103`) copies `config/gateway.toml` from the repository over `D:\avrig\config\gateway.toml`. The Linux branch copies only the binary, so `/opt/avrig/config/gateway.toml` on the WSL node is never refreshed. The analyst flagged this as finding 11.

Consequence: the WSL node keeps its old `opencode` block and old binary behaviour unless its config is edited by hand. Two requirements follow.

1. `Infra` updates `/opt/avrig/config/gateway.toml` explicitly on the WSL node, or the plan states clearly that the WSL node is out of scope for this feature.
2. H20d asserts the block is present on whichever nodes are in scope, so a silently stale node cannot pass as a success.

Recommendation: scope this plan to the **Windows node only**, matching the earlier `0.3.0` decision that the gateway role is Windows-only, and state that explicitly rather than leaving a stale WSL node to be discovered later.

### Lab Artifact Hygiene (blocker)

The audit found that `lab/` currently holds **live credentials on disk**: `lab/run-seq.log` (112 KB), `lab/matrix-run.log` (6 KB), and `lab/gate-matrix.log` (3.6 KB) each contain unredacted `Authorization: Bearer st_<redacted>-...`, plus 61 `.txt` and 112 `.json` artifacts under `lab/replay-*/`. The repository `.gitignore:14` covers only `*.log`, so committing the scripts as originally proposed would have staged a live console token.

Required actions, in order:

1. **Before any commit**, delete the credential-bearing artifacts: `lab/*.log` and every `lab/replay-*/` directory. The token is valid until 2026-12-15, so treat it as live.
2. Rotate the console credential if the artifacts were ever committed or pushed. Confirm with `git log --all -- lab/` that nothing leaked into history; the directory is currently untracked, so this should come back empty.
3. Change the `.gitignore` entry from `lab/captures/` to a default-deny pattern: ignore `lab/*` and explicitly un-ignore `!lab/README.md` and the four script files. Default-deny means a future artifact cannot leak by being a new file extension.
4. `tester` must add a check that `lab/` contains no `st_`, `oc_sk_`, or `sk-` string before the release step runs.

The lab scripts must also stop writing raw headers to logs. `capture-server.ps1` already redacts `Authorization`, but the older diagnostic scripts did not, which is how the token reached a log file. Any script that logs a request must route values through a redaction helper.

### Configuration

```toml
[gateway.providers.opencode]
enabled = true
base_url = "https://opencode.ai/inference/openai/v1"
api_key = "{file:D:/avrig/config/secrets/opencode_console_token}"
headers = { "x-opencode-org-id" = "wrk_01KPCJ5BP7MCCSBJFR030NGD6B" }
user_agent = "{forward}"
analyze_headers = true
forward_headers = [
  "x-opencode-project",
  "x-opencode-client",
  "x-opencode-session",
  "x-opencode-session-id",
  "x-session-affinity",
  "x-session-id",
  "traceparent",
  "b3",
]
```

Two changes from the previous revision, both forced by the root cause:

1. **`api_key` is no longer `{env:OPENCODE_API_KEY}`.** That key is `oc_sk_` and 429s on every free model, while serving paid models at 200. The free tier requires the **console OAuth token** (`st_`), which is the credential the client itself uses. `{env:...}` cannot express this because the token is not in the environment; it lives in the client credential store and rotates.
2. **`x-opencode-org-id` is sent.** The console provider definition declares it as a required header.

A new `{file:PATH}` secret source is needed, because `resolve_env_var` (`avrig-api/src/main.rs:1154`) only expands `{env:VAR}`. It reads the file, trims whitespace and a trailing newline, and treats a missing file as an empty key so the provider degrades rather than panics, matching the existing style.

`x-opencode-org-id` needs a `headers` map on `GatewayProviderConfig`, since the current config has no way to express a static outbound header. It is a static value, not a secret.

`x-opencode-ticket` must **not** be in `forward_headers`; it is a credential and appears in `NEVER_RELAY`.

`oc-composync` is untouched, keeping the proven Go free path provably unchanged.

**Why the body is not a problem.** The gate needs the real CLI body shape, and it gets it for free when the caller is the OpenCode client, because the gateway forwards what the caller sent. The gateway's typed re-serialization is safe: `FunctionDefinition` drops the native `function.strict` field, and that was tested directly. Dropping `strict` still returns **200**, so the gateway's shape is close enough. No body manipulation is needed or wanted.

**What this does and does not deliver.** A real OpenCode client calling `avrig/opencode/deepseek-v4.1-flash-free` sends the genuine CLI body, so with the `st_` credential it should return 200. A hand-written minimal-body curl will still 429, and that is correct behaviour, not a defect: it proves the gate is real and that the gateway is not fabricating requests. The matrix records both outcomes separately.

`x-opencode-*` was the original proposal and is **rejected**. The analysis at `avrig-analyst` audit finding 1 is decisive: the CLI compiles `x-opencode-ticket`, which the plan's own evidence line records as carrying a live `st_` console token, so a prefix wildcard over `x-opencode-*` would relay that credential to `opencode.ai` on every request. Objective 2 and the security note both promise credentials can never be relayed. The fix is to enumerate the eight headers that are actually wanted and never use a wildcard over a namespace that also contains a credential.

`HeaderPattern` still supports `prefix*` because the type is general and the tests must cover it, but the shipped configuration uses exact names only. This is recorded as a design decision, not an oversight.

`analyze_headers` is emitted at `info`, not `debug`. The deployed runtime config sets `level = "info"` (`D:\avrig\config\config.toml:2`), so a `debug` emission would be invisible on the node and objective 1 would be untestable in production.

`user-agent` is covered by the existing `{forward}` policy, so it is not repeated. `oc-composync` is left untouched, which keeps the proven free path provably unchanged.

Client picker entries. The analyst found that all four already exist in the live file at `D:\Cloud\OneDrive\AI\Agentic\.opencode\opencode.json` lines 38, 51, 53, and 58, with `name` equal to key:

```json
"oc-composync/beam-free": { "name": "oc-composync/beam-free" },
"oc-composync/hy4-flash-free": { "name": "oc-composync/hy4-flash-free" },
"oc-composync/iceman-contributor-free": { "name": "oc-composync/iceman-contributor-free" },
"oc-composync/longcat-2.5-free": { "name": "oc-composync/longcat-2.5-free" }
```

So objective 4 is **already satisfied** and needs verification, not editing. Phase 8 changes from "add picker entries" to "confirm the four entries and record their line numbers". Editing a live config for zero gain is how a picker gets broken.

All four Go free ids are listed, decided by the user on 2026-11-19.

`iceman-contributor-free` is listed even though it currently fails, and that is deliberate. It is not broken, it is unconsented: the upstream answers `400 invalid_request_error` with "This OpenCode Go model trains on request data. Turn on \"Allow paid endpoints that train on request data\" at https://opencode.ai/console/org_01M72468PMBQ51MKCPZFK55TVC/settings/privacy#training to use it." The user chose to surface it so the toggle is discoverable rather than silently absent. Documentation of that toggle is part of the deliverable: the picker entry and the note land together, so no one mistakes a consent gate for a gateway defect.

Measured through the gateway on 2026-11-19, with the provider prefix present: `HTTP 502`, body `Direct provider upstream error: {... "invalid_request_error" ... "trains on request data" ...}`. The gateway wraps the upstream 400 as a 502 because `chat_completion_error_status` in `avrig-api/src/gateway.rs:316-331` only special-cases 400/404 that name the model, and this 400 does not. So the observable contract for this model is a 502 carrying the privacy message verbatim.

Consequence for testing: `iceman-contributor-free` is asserted to return that specific 502-wrapped privacy message until the toggle is flipped, and to return 200 after. Both states are correct and each must be distinguished from a real failure. See H17a, H17b, H17c, and H18d in the Test Specification; H17c records `SKIP (toggle off)` rather than a failure while the toggle is off.

A routing detail worth recording separately: calling the gateway with a bare `iceman-contributor-free` (no `oc-composync/` prefix) does not reach the Go path at all. It falls through to a default provider and returns `502` with `Upstream HTTP 403: This service has been disabled in this account for violation of Terms of Service`. Model ids must always carry the provider prefix, which is why the picker keys below are fully qualified.

`oc-composync/deepseek-v4.1-flash-free` is NOT added. It returns `400 server_error` "isn't included in OpenCode Go", which no setting can change, so listing it would be a dead entry with no actionable remedy.

### EDM Design

Not applicable. No schema, table, column, or migration is introduced or altered. The gateway holds no persistent state, and provider configuration lives in TOML, not a database.

### Security Notes

- `Authorization` is dropped at capture and again at apply, so a caller cannot substitute the provider credential.
- `x-opencode-ticket` is denied by name. It carries a live console `st_` token and is the single most dangerous name in this namespace, which is why the shipped policy enumerates exact names and never uses an `x-opencode-*` wildcard.
- Redaction is name-based plus value-shape-based, so an unexpected credential header in an allowlist still emerges as a fingerprint rather than a value.
- The apply-time guard refuses any token-shaped value regardless of header name, so a `Bearer` or `st_` payload in an unexpected header cannot reach the provider.
- Prefix patterns shorter than three characters, or containing no `-`, are rejected at registration, so `x-*` cannot widen into `x-api-key`.
- Values capped at 8 KiB and 32 headers bounds per-request memory from a hostile caller.
- Loopback-only access is unchanged, so network exposure does not widen.
- The header profile logs only fingerprints, never values, so it is safe at `info` in production. It emits at most one line per request and at most 32 facts per line.

## Parallel Execution Plan

| Phase | Stream | Assignee | Mode | Depends on |
|---|---|---|---|---|
| 1 | Lab capture and identity trace | general (lab) | in flight | nothing |
| 2 | Author plan, contracts, target files | plan | done | phase 1 evidence |
| 3a | Test matrix attached | tester | parallel | phase 2 |
| 3b | Standards audit | analyst | parallel | phase 2 |
| 4 | User approval gate | plan + user | blocking | 3a, 3b |
| 5 | `header_policy.rs`, `ChatRequest` field, options struct, composer, config fields, edge capture, unit tests | be | serial, one agent | phase 4 |
| 6 | `cargo check --workspace --exclude avrig-desktop` in `avrig-ai`, then `cargo test -p avrig-gateway` in `avrig-lib` and `cargo test -p avrig` in `avrig-api` (separate workspaces, so no shared `-p` invocation) | build | serial | phase 5 |
| 7 | Deploy both targets, restart service, verify free models, live retry of the gated model | Infra, then tester | serial | phase 6 |
| 8 | Verify the four Go free picker entries and record their line numbers; no edit expected | fe | parallel with 7 | phase 6 |
| 9 | Retrospective on the identity finding | km | parallel | phase 7 |
| 10 | SemVer `minor` to `0.4.0` from `0.3.0`, tag, push to four repos | build | serial | phase 7 pass |
| 11 | Archive to `plans/done/` | plan | serial | phase 10 |

Phase 5 touches `client.rs` and `main.rs` together, so it runs as one `be` assignment rather than two agents, avoiding an edit collision.

## Test Specification and Validation Matrix

Attached by `tester`, 2026-11-19, against the revised plan. Every expectation below was measured on this machine on 2026-11-19 unless the row says otherwise, and observed values are quoted inline so an implementer can tell a code defect from changed upstream behaviour.

Identifiers H1 to H21 keep their meaning from the plan's own table, and H13 still means "the existing suites stay green". Expansion rows use a suffixed form (`H2a`, `H16b`, `H19c`) or continue past H21 (`H22`, `H24`, `H25`). Nothing was renumbered, so the Risks table and the Parallel Execution Plan still resolve. Three identifiers are deliberately absent and should not be read as gaps: H13 has no single row because it is H13a to H13i, H11b was the analyst's proposed number for a credential-relay test that landed as H1f, and H26 was never used.

Rows are grouped by how they are executed, because that is what the runner needs. The inventory as attached: 46 unit rows, 3 integration, 9 regression suites, 23 live, and 1 manual equivalence row, for 82 executable rows plus the `V` evidence table in the free-model section which documents observations rather than new work. Within the 46 unit rows: 28 in the new `header_policy` module, 12 dispatch, 4 handler, plus `H27a` and `H27b` which were added after the root cause moved from documenting a 502 to achieving a 200. If a later revision changes the shape, update this sentence rather than trusting it, because two revisions of this section did land in parallel and prose totals went stale within minutes.

Two rows carry the audit's weight and should be read before the rest. H1d and H1f exist because `NEVER_RELAY` originally omitted `x-opencode-ticket`, which the plan's own evidence line records as carrying a live `st_` console token; a prefix wildcard over `x-opencode-*` would have relayed it. H19c and H19d exist because objective 3's actual subject had no row at all, and they are now split by caller: H19c is the real client expecting 200, H19d is a synthetic body expecting the documented 429 behind a 502.

### Preconditions

Run in this order. P0 is the only step whose placement is non-negotiable.

| # | Step | Exact action | Pass condition |
|---|---|---|---|
| P0 | **Pre-change `oc-composync` outbound capture. Must complete before any edit to `header_policy.rs`, `client.rs`, `antigravity/types.rs`, `gateway.rs`, `main.rs`, or either `gateway.toml`.** | Follow `### Outbound Equivalence` E1 to E4. | `oc-composync-baseline.txt` exists and is stored with the session evidence. A baseline captured from a modified tree is void. |
| P1 | Build and type gate | `cd D:\Cloud\OneDrive\AI\Agentic\avrig-ai; cargo check --workspace --exclude avrig-desktop` | Exit 0. `avrig-desktop` is a member of the `avrig-ai` workspace only; `avrig-lib` and `avrig-api` are separate workspaces, so the exclude flag is meaningless there and cargo rejects it. Those two use `cargo check -p avrig-gateway` and `cargo check -p avrig`. `avrig-desktop` is broken before this change and its errors are never a finding of this plan. |
| P2 | Unit suite baseline | `cd D:\Cloud\OneDrive\AI\Agentic\avrig-lib; cargo test -p avrig-gateway --lib -- --list` and `cd D:\Cloud\OneDrive\AI\Agentic\avrig-api; cargo test -p avrig --lib -- --list` | Record both counts and the full name list. Measured today: 56 tests in `avrig-gateway`, of which 8 are `direct_provider_session_header_tests`; 15 `gateway::*` tests in `avrig`, of which 5 are `gateway::session_header_tests`. |
| P3 | Live node and health | `http://127.0.0.2:8000/v1` for every live row. `Invoke-RestMethod http://127.0.0.2:8000/v1/health` | `ok` is `true` and `providers` lists six names: `google-antigravity`, `openai-siwc`, `composync`, `opencode`, `ollama`, `oc-composync`. Measured today: `semver` `0.3.0`, `accounts_count` 6. `127.0.0.1:8000` is a different WSL node without the `opencode` provider block and must never be used. |
| P4 | Token cache | `Test-Path D:\Cloud\OneDrive\AI\Agentic\avrig-ai\.secrets\test_token.json` must be `True`. Verify only `expires_at`, `token_type`, `issuer`. | Present, `expires_at` = `1893456000` (2030-01-01), `token_type` = `Bearer`, `issuer` = `https://iam.avrig.ai/auth/v1/`. Never print `access_token`. |
| P5 | Auth scope | `handle_health`, `handle_version`, and `handle_chat_completions` are registered in `build_gateway_router` with only `local_only_guard`; the chat route has no bearer middleware. | Every live row here runs without a token. The cache is read only if a row is aimed at the IAM edge (`https://api.avrig.ai`), and then only as `Authorization: Bearer <access_token>`, never echoed. |
| P6 | Provider credentials, all three | (a) `[Environment]::GetEnvironmentVariable("OPENCODE_COMPOSYNC_API_KEY","Machine")` then `"User"`. (b) `Test-Path D:/avrig/config/secrets/opencode_console_token`, and if present only its length and first 3 characters. (c) `[Environment]::GetEnvironmentVariable("OPENCODE_API_KEY","User")` length only. Report presence and lengths, never a value. | All three must be assessed, because they serve different rows and one of them is the objective-3 subject. (a) non-empty at **Machine** scope: measured 51 characters at Machine and 0 at User. Reading User first is the trap, because it returns empty, `resolve_env_var` substitutes an empty string, the empty key is dropped, and the provider then sends no `authorization` header at all while still answering `200`. This key drives the `oc-composync` rows (H16 to H18). (b) the `{file:D:/avrig/config/secrets/opencode_console_token}` path that design section 4 now puts in `api_key` for `opencode`. Measured today: `D:/avrig/config/secrets/` **does not exist**, so H19c cannot pass until it is created, and H20c's config check must not be read as proof the credential resolved. It must hold an `st_` value, not `oc_sk_`: `st_` is the credential that makes the free tier answer. (c) `OPENCODE_API_KEY` is `oc_sk_` and 429s every free model, so its presence is a trap rather than a pass. Record it so a later 429 is not mistaken for a gateway regression. |
| P7 | Picker baseline | `(Get-Content D:\Cloud\OneDrive\AI\Agentic\.opencode\opencode.json -Raw \| ConvertFrom-Json).providers.avrig.models.PSObject.Properties \| Where-Object { $_.Name -like 'oc-composync/*free*' -or $_.Name -eq 'opencode/deepseek-v4.1-flash-free' } \| ForEach-Object { "$($_.Name)=$($_.Value.name)" }` | Two separate facts, both required. Measured today: the four `oc-composync` free entries are present with `name` equal to key at lines 38, 51, 53, and 58, and `oc-composync/deepseek-v4.1-flash-free` is absent, so objective 4 is already met and H22 verifies it rather than creating it. But `opencode/deepseek-v4.1-flash-free` is **also absent**, which the command above now checks as its own case, and that absence blocks H19c outright. Record both lines separately so a missing objective-3 entry cannot hide behind objective 4 being satisfied. |
| P8 | Lab secret scan, run before the release step and again after any new capture | `Get-ChildItem D:\Cloud\OneDrive\AI\Agentic\avrig-ai\lab -Recurse -File \| Select-String -Pattern 'st_[0-9a-f]{8}-\|sk-[A-Za-z0-9]{20,}\|oc_sk_[A-Za-z0-9]{20,}'` | Zero matching files. Measured today: 361 files scanned, 0 hits, and a planted fake `st_deadbeef-0000` control matched, so the pattern is not vacuous. Run it recursively: a shallow `lab\*` scan also reports 0 and would pass while missing the 112 files under `lab/replay-*/`. This is the check the plan's `Lab Artifact Hygiene` section assigns to `tester`, and it must be green before `build` tags anything. |

Body writes on Windows must use `[System.IO.File]::WriteAllText($p,$json,(New-Object System.Text.UTF8Encoding($false)))` and be sent with `curl.exe --data-binary "@$p"`. A body passed through `-d`, or built by PowerShell string concatenation, reaches the gateway with a BOM and returns `400`.

### Unit Tests

`new module` rows live in a `#[cfg(test)] mod tests` inside the new `avrig-lib/crates/avrig-gateway/src/header_policy.rs`, run under `cargo test -p avrig-gateway --lib`, and need no server. `dispatch` rows live in a new `#[cfg(test)] mod direct_provider_forward_header_tests` in `client.rs`, reusing the `tiny_http` stub pattern of `direct_provider_session_header_tests` (L2581 to L2618). `handler` rows live in a new `#[cfg(test)] mod header_capture_tests` in `avrig-api/src/gateway.rs`, reusing the `headers(&[(&str,&str)])` builder from `session_header_tests` (L669).

| ID | Layer | What it asserts | Test name to write |
|---|---|---|---|
| H1a | new module | For every name in `NEVER_RELAY`, a map carrying only that header yields no entry from `capture_relayable`. Iterate the constant with `NEVER_RELAY.iter()` so a future addition is covered without touching the test | `header_policy::tests::never_relay_names_are_never_captured` |
| H1b | new module | Iterating `NEVER_RELAY` itself (22 entries as written: 9 credential, 2 cookie, 11 framing) plus two ordinary headers yields exactly the two ordinary ones, proving the filter is per-name and does not stop at the first drop. Iterate the constant rather than hardcoding 22, so the count cannot silently drift | `header_policy::tests::never_relay_filter_keeps_every_other_header` |
| H1d | new module | `x-opencode-ticket` and `x-opencode-org-id` are both members of `NEVER_RELAY`, asserted by name rather than by length. This is the audit's finding 1: without the ticket entry, the `x-opencode-*` wildcard relays a live `st_` console token to a third party, and the plan's own evidence line records that the CLI sends it | `header_policy::tests::deny_list_contains_the_credential_bearing_opencode_names` |
| H1e | new module | A capture map carrying `x-opencode-ticket: st_notarealtoken5678` alongside `x-opencode-session: ses_lab` yields only the session entry. Distinct from H1d: H1d pins membership, this pins the observable drop for the exact credential the plan names | `header_policy::tests::ticket_is_dropped_while_session_survives` |
| H1f | dispatch | The shipped eight-name policy is applied to a capture set that includes `x-opencode-ticket`, `x-opencode-org-id`, and `x-api-key: sk-live`. Even with a wildcard pattern added to the policy, none of the three reaches the stub. The analyst's finding 1 asked for this row by name as H11b; it is numbered H1f here so it sits beside the other deny-list rows rather than among the duplicate-header rows where H11 lives | `direct_provider_forward_header_tests::shipped_policy_never_relays_a_credential_name` |
| H2a | new module | `HeaderValue::from_bytes(b"caf\xE9")` on `x-non-utf8` is dropped; `x-plain: v` survives. Pins that the code rejects via `to_str` rather than a lossy conversion | `header_policy::tests::capture_drops_non_utf8_values` |
| H2b | new module | `x-blank: "   "` and `x-empty: ""` are dropped; `x-keep: "v"` survives | `header_policy::tests::capture_drops_blank_values` |
| H2c | new module | An 8192-byte value on `x-fits` is kept; 8193 bytes on `x-too-long` is dropped. The boundary is inclusive per `MAX_RELAYED_VALUE = 8192` | `header_policy::tests::capture_drops_oversized_values` |
| H3a | new module | 40 headers `x-h00` to `x-h39` yield exactly `MAX_RELAYED_HEADERS` (32), never 33. Assert the count only, because `HeaderMap` iteration order is not a documented insertion order | `header_policy::tests::capture_caps_at_32_headers` |
| H3b | new module | `append("x-dup","first")` then `append("x-dup","second")` yields one entry valued `first`. `insert` cannot create a duplicate, so the test must use `append` or it proves nothing | `header_policy::tests::capture_keeps_the_first_occurrence_of_a_duplicate` |
| H3c | new module | `X-OpenCode-Client: cli` is captured as `x-opencode-client`. Lowercasing is the precondition the whole policy matcher relies on | `header_policy::tests::capture_lowercases_header_names` |
| H4a | new module | `parse("x-opencode-*")` and `parse("user-agent")` both return `Some`. The first matches `x-opencode-session`; the second matches `user-agent` and not `x-opencode-session` | `header_policy::tests::pattern_parse_accepts_prefix_and_exact_forms` |
| H4b | new module | `parse` returns `None` for `""`, `"   "`, `"*"` alone, `"x-*"`, `"x opencode*"`, and `"*x-opencode"`. The bare `*` case is load-bearing: a naive parser keeps an empty prefix and matches every header | `header_policy::tests::pattern_parse_rejects_blank_bare_star_and_malformed` |
| H4c | new module | The tightening rule from finding 7: a prefix must be at least 3 characters before the `*` and must contain a `-`, so `x-*` and `x*` are rejected while `x-opencode-*` is accepted. Assert it through registration behaviour as well, because a rejected pattern must degrade to "not forwarded", not panic: `add_direct_provider` with `vec!["x-*".into(), "x-api-key".into()]` yields exactly one usable pattern | `header_policy::tests::prefix_requires_three_chars_and_a_dash` |
| H5a | new module | `parse("X-OpenCode-*")` matches `x-opencode-session` and `x-opencode-project`, so mixed case in the pattern is normalised rather than silently failing | `header_policy::tests::prefix_match_is_ascii_case_insensitive` |
| H5b | new module | `parse("User-Agent")` matches `user-agent` and not `user-agent-extra`, proving the exact form is case-insensitive and whole-name | `header_policy::tests::exact_match_is_ascii_case_insensitive` |
| H5c | new module | `"x-open*"` matches `x-opencode-session` but not `xopencode-session`, proving the prefix is literal | `header_policy::tests::prefix_match_requires_the_literal_prefix` |
| H6a | new module | Policy `[x-opencode-project, x-opencode-*]` over captured `[x-opencode-client, x-opencode-project, x-opencode-session]` returns project, then client, then session: policy order, not capture order | `header_policy::tests::select_relayable_follows_policy_order` |
| H6b | new module | Policy `[x-opencode-*, x-opencode-session]` returns `x-opencode-session` once, so wildcard plus literal cannot duplicate a header | `header_policy::tests::select_relayable_deduplicates_multiple_matches` |
| H6c | new module | Policy `[x-opencode-session-id]` with nothing captured under it returns empty and does not panic. This is the normal case for the CLI-only headers that never reach a custom provider. The name must not be in `NEVER_RELAY`, because `select_relayable` re-checks the deny list and would return empty for that reason instead, hiding a broken "not captured" path behind the security filter | `header_policy::tests::select_relayable_ignores_names_that_were_not_captured` |
| H7a | new module | `authorization: Bearer abc123` gives `redacted == true`, `scheme == Some("Bearer")`, driven by the name alone | `header_policy::tests::profile_redacts_never_relay_names` |
| H7b | new module | `x-custom-auth: Bearer abc123` gives `redacted == true` with `scheme == Some("Bearer")`. The name is outside `NEVER_RELAY`, so this proves value-shape redaction | `header_policy::tests::profile_redacts_bearer_scheme_values` |
| H7c | new module | One value per prefix the design names: `Bearer `, `sk-`, `oc_sk_`, `st_`, `rt_`, `ghp_`, `eyJ`, each padded to 64 characters. All seven redact. Length is now defined: `MIN_TOKEN_LIKE_LEN` is 32 and the predicate is "longer than the constant", so these fixtures sit far above the boundary and the test cannot fail on an off-by-one | `header_policy::tests::profile_redacts_token_shaped_values` |
| H7d | new module | The six non-`Bearer` prefixes at 8 characters (`sk-x`, `oc_sk_x`, `st_x`, `rt_x`, `ghp_x`, `eyJx`) give `redacted == false`. Without this, an implementation that redacts on prefix alone passes H7c and the profile becomes useless. `Bearer` is deliberately excluded from this row: design section 3 redacts a `Bearer` value on the scheme alone with no length condition, which is what H7b asserts at 11 characters, so a short `Bearer` fixture would redact and this test would fail for a correct implementation | `header_policy::tests::profile_keeps_short_prefixed_values_readable` |
| H7e | new module | The boundary, stated once because two tests depend on it. `is_token_shaped` is false at exactly 32 characters and true at 33, for a `sk-` value. Pins `MIN_TOKEN_LIKE_LEN` as "longer than", so an implementer cannot flip the comparison and still pass H7c and H7d | `header_policy::tests::token_shape_boundary_is_strictly_greater_than_the_constant` |
| H7f | new module | `is_token_shaped` and the `redacted` flag agree for every fixture in H7c and H7d. The design says both share one predicate so redaction and refusal cannot drift; this asserts the sharing rather than trusting it. The one legitimate asymmetry is the `Bearer` scheme, which redacts by name-shape in the profile and by value-shape in the predicate: assert agreement only for fixtures long enough to satisfy both, which is why H7c's are 64 characters and H7d's exclude `Bearer` | `header_policy::tests::redaction_and_refusal_agree_on_every_fixture` |
| H8a | new module | `user-agent: opencode/latest/2.3.2/cli`, `accept: */*`, and `x-opencode-session: ses_e0e7292cdffe0bU6KCVXwth0GP` all give `redacted == false`. The session value matters: `ses_` is not in the token prefix list | `header_policy::tests::profile_leaves_plain_headers_readable` |
| H8b | new module | `sha256_16` is 16 lowercase hex characters, stable across calls, different for different values; `length` equals byte length; `scheme` is `None` off a bearer value | `header_policy::tests::profile_fingerprint_shape_length_and_scheme` |
| H8c | new module | Serialising the whole `header_profile()` output for `authorization: Bearer supersecretvalue` and `x-token: sk-livesecret` yields a string containing neither value. Makes redaction a property of the data rather than of the log call site | `header_policy::tests::profile_facts_never_carry_the_raw_value` |
| H9 | dispatch | Policy `Vec::new()`, `forwarded_headers` carrying session, client, project, and `traceparent`. The stub sees none of them. Run it against both dispatch paths, because the composer is now shared and the empty-policy case is the cheapest proof it was actually called | `direct_provider_forward_header_tests::empty_policy_sends_no_relayed_header` |
| H9b | dispatch | The fallback branch of finding 10: an unprefixed model dispatched through `directs.values().next()` with `forwarded_headers` populated must reach the stub with none of them. The design says the fallback clears `forwarded_headers` before dispatch, and this row is the only thing that keeps that true. Without it, caller session ids and trace context can reach a provider the model string never named | `direct_provider_forward_header_tests::fallback_dispatch_relays_nothing` |
| H10a | dispatch | Policy `[x-opencode-*]`, `forwarded_headers` carrying session `ses_lab`, client `cli`, project `06117`, and `x-unrelated: nope`. The stub sees the three with exact values and no `x-unrelated` | `direct_provider_forward_header_tests::opencode_policy_delivers_session_client_and_project` |
| H10b | dispatch | The same policy driven through `chat_completion_stream`. The design now extracts one `direct_provider_request` composer called from both functions rather than duplicating the loop, so this row proves the extraction happened and the stream path really uses it. A passing H10a with a failing H10b means the stream path kept its own copy | `direct_provider_forward_header_tests::stream_dispatch_applies_the_same_policy` |
| H10c | dispatch | A value that is token-shaped but sits under a harmless name: policy `[x-opencode-project]`, and `forwarded_headers` carrying `x-opencode-project: st_0123456789abcdef0123456789abcdef` (35 characters, comfortably over the 32 boundary). The stub must not see it, because `is_token_shaped` refuses it regardless of name. The name-level deny list cannot catch this, so it is the only row that proves the value-shape guard exists on the apply side. Do not shorten this fixture: a `st_` value under 33 characters is not token-shaped, and a short one would pass for the wrong reason | `direct_provider_forward_header_tests::token_shaped_value_is_refused_under_a_safe_name` |
| H11 | dispatch | Provider with a valid key, policy containing `HeaderPattern::parse("authorization").unwrap()`, and `input.forwarded_headers` holding `authorization: Bearer caller-supplied` directly, bypassing edge capture. On the wire the stub sees exactly one `authorization`, valued `Bearer test-key`. Two headers, or the caller value, fails | `direct_provider_forward_header_tests::passthrough_cannot_replace_authorization` |
| H12a | dispatch | Policy containing `user-agent`, provider `user_agent = "{forward}"`, caller agent `opencode/1.2.3`. The stub sees one `user-agent`, valued `opencode/1.2.3` | `direct_provider_forward_header_tests::passthrough_does_not_duplicate_user_agent` |
| H12b | dispatch | `session_header = Some("x-opencode-session")`, policy `[x-opencode-*]`, caller session `ses_lab`. The stub sees one `x-opencode-session`, valued `ses_lab` | `direct_provider_forward_header_tests::passthrough_does_not_duplicate_the_configured_session_header` |
| H12c | dispatch | `session_header = None`, policy `[x-opencode-*]`, caller session `ses_lab`. The stub sees `x-opencode-session: ses_lab`, proving passthrough supplies the header when no named policy exists, and that the duplicate guard does not blanket-suppress the name | `direct_provider_forward_header_tests::passthrough_supplies_the_session_header_when_none_is_configured` |
| H12d | dispatch | `session_header = Some("x-opencode-session")`, caller session `ses_caller`, policy `[x-opencode-*]`, and `forwarded_headers` carrying a different `x-opencode-session: ses_relayed`. The stub must see `ses_caller`, the gateway-resolved value. Distinguishes "skipped because duplicated" from "skipped in the wrong order" | `direct_provider_forward_header_tests::configured_session_header_wins_over_a_relayed_duplicate` |
| H14b | dispatch | Permanent Rust guard for the unchanged provider, written against the new options struct. Account registered exactly as `oc-composync` is configured: `DirectProviderOptions { session_header: Some("x-opencode-session"), user_agent: Some("{forward}"), forward_headers: Vec::new(), .. }`. Caller supplies the full 16-header OpenCode set including `x-opencode-project` and `x-opencode-client`. The stub's headers are exactly `authorization: Bearer test-key`, `user-agent: opencode/latest/2.3.2/cli`, `x-opencode-session: ses_lab`, plus the ordinary accept and content headers, and no caller header is relayed. This is the Rust half of H14a and the reason the manual capture does not have to be repeated on every future change | `direct_provider_forward_header_tests::oc_composync_shape_relays_nothing` |
| H1c | handler | Feeding `headers(&[("authorization","Bearer x"),("host","127.0.0.2:8000"),("x-opencode-session","ses_lab")])` through the same capture call the handler uses returns only `x-opencode-session` | `header_capture_tests::handler_capture_excludes_authorization_and_host` |
| H24 | handler | The 16-header capture from the plan's own evidence yields exactly the eight policy names that are present in it (`x-opencode-client`, `x-opencode-project`, `x-opencode-session`, `x-opencode-session-id`, `x-session-affinity`, `x-session-id`, `traceparent`, `b3`), excludes every `NEVER_RELAY` name including `host`, `content-type`, `authorization`, and `accept-encoding`, and stays under the cap. Pins the exact set objective 2 depends on, and would fail if the CLI ever adds a credential-bearing `x-opencode-*` name that the deny list has not caught | `header_capture_tests::handler_captures_the_opencode_header_set` |
| H25 | handler | The accessor from design section 4 reports the resolved provider's `analyze_headers`: `true` when registered on, `false` when registered off. Written against the accessor, not against a still-hypothetical field, because finding 8 settled the choice as an account field plus an accessor and the seven `GatewayState` literals are already listed for update | `header_capture_tests::analyze_headers_is_reported_per_provider` |
| H25b | handler | With analysis on, the emitted line for `authorization: Bearer supersecretvalue` contains neither `supersecretvalue` nor the raw value, and does contain the header name and a 16-character fingerprint. Assert on the captured subscriber output at `info` level, not `debug`, because finding 6 requires the emission to remain visible at the level both deployed configs actually use | `header_capture_tests::profile_emission_carries_no_raw_value` |
| H27a | config source, `main.rs` | The new `{file:PATH}` secret source: a file containing `st_abc123\n` resolves to `st_abc123` with the newline and surrounding whitespace trimmed; a path that does not exist resolves to an empty string and does not panic, so the provider degrades exactly as a missing `{env:}` does today. A literal value with no `{file:}` prefix passes through untouched, and `{env:VAR}` keeps working, so the existing `{forward}` and `{env:...}` behaviour cannot regress. This runs in `avrig-api/src/main.rs` `mod tests`, where `resolve_env_var` already lives | `tests::file_secret_source_trims_and_degrades_on_missing_file` |
| H27b | dispatch | The static outbound `headers` map from the `opencode` config block is actually applied on the wire: with `headers = { x-opencode-org-id = "wrk_stub" }` registered on the account, the stub sees `x-opencode-org-id: wrk_stub` even though the caller sent none and the policy does not name it. A caller-supplied `x-opencode-org-id: wrk_caller` must not replace it, which follows for free because the name is in `NEVER_RELAY`, so this row also pins that the static path is not the relay path. Without this row, objective 3's required header has no test at all | `direct_provider_forward_header_tests::static_config_headers_reach_the_wire` |

### Integration Tests

These live in `avrig-api/tests/gateway_integration_test.rs` and drive the real router through `tower::ServiceExt::oneshot`, so they cross the handler, the client, and a real socket. They block on amendment 4: the stub at L180-217 must start capturing inbound headers. The shipped policy is eight exact names, so these rows register that list rather than a wildcard, which is what makes them evidence about the configuration that actually runs.

| ID | Layer | What it asserts | Test name to write |
|---|---|---|---|
| H15 | integration | A stub registered with the eight-name shipped policy receives `x-opencode-session: ses_e2e`, `x-opencode-project: proj-e2e`, and `x-opencode-client: cli` on the wire, delivers none of `host`, `content-type`, `authorization`, or `x-opencode-ticket` even when the caller sends them, and the caller sees `200` | `test_relayed_header_reaches_the_stub_provider` |
| H15b | integration | A stub registered with an empty policy receives no caller header, so the deny default survives the full stack and not just the client | `test_empty_policy_relays_nothing_end_to_end` |
| H15c | integration | A request carrying `authorization: Bearer caller-token` and `x-opencode-ticket: st_live` against the shipped policy reaches the stub with exactly one `authorization`, valued `Bearer test-key`, and no `x-opencode-ticket` at all. Combines the credential-override and credential-relay cases, because both answer the same question: can a caller-supplied credential influence the upstream request | `test_caller_authorization_never_replaces_the_provider_key` |

### Regression Tests

Nothing below may change behaviour. Run each suite and require the pre-change and post-change name lists to match exactly.

| ID | Suite | Location | Existing tests that must stay green |
|---|---|---|---|
| H13a | `direct_provider_session_header_tests` | `avrig-gateway/src/client.rs:2552` | `inbound_session_id_reaches_the_provider`, `missing_session_id_is_generated_as_uuid_v4`, `provider_without_session_header_sends_none`, `blank_session_header_name_degrades_to_no_header`, `forward_policy_sends_the_callers_application_agent`, `forward_policy_still_blocks_library_agents`, `literal_policy_replaces_the_caller_agent`, `absent_policy_keeps_the_gateway_default` |
| H13b | `direct_stream_relay_tests` | `client.rs:2087` | `reasoning_deltas_and_terminal_usage_frame_reach_the_client`, `terminal_usage_stays_closed`, `stream_without_finish_reason_gets_a_synthesized_terminal_chunk`, `stream_that_used_the_token_cap_reports_length`, `empty_upstream_stream_still_closes_with_a_terminal_chunk`, `upstream_error_frame_is_surfaced_instead_of_an_empty_stream` |
| H13c | `usage_stream_tests` | `client.rs:1940` | `provider_usage_trailer_uses_completion_id_and_latest_valid_usage`, `provider_usage_trailer_requires_explicit_opt_in`, `direct_provider_keeps_only_latest_requested_usage_after_choices`, `direct_provider_suppresses_usage_when_not_requested_or_missing`, `usage_requires_stream_options_include_usage_true` |
| H13d | `direct_provider_catalogue_tests` | `client.rs:2364` | `unknown_sub_model_under_registered_provider_is_reported_missing`, `listed_sub_model_is_dispatched`, `unavailable_catalogue_falls_back_to_dispatch`, `catalogue_cache_is_keyed_per_provider_and_key_index`, `upstream_model_faults_are_recognized` |
| H13e | `client_contract_tests` | `client.rs:1817` | `upstream_id_is_the_only_identity_source`, `tool_turn_reports_tool_calls_finish_reason`, `claude_client_id_survives_validation_conversion_and_response_builder` |
| H13f | `resolver::tests` | `avrig-gateway/src/resolver.rs` | `builtin_prefixes_match_the_resolver_special_cases`, `test_is_siwc`, `test_resolve_upstream`, `test_strip_prefix`, `unknown_prefix_reports_prefix_and_model` |
| H13g | `gateway::tests` | `avrig-api/src/gateway.rs:348` | All ten, including `health_reports_version_and_build_metadata`, `unknown_model_prefix_maps_to_not_found`, `unlisted_sub_model_maps_to_not_found`, `claude_path_rejection_maps_to_bad_request_before_dispatch`, `every_tool_history_validation_variant_maps_to_bad_request`, `generic_upstream_bad_requests_stay_bad_gateway`, `non_validation_failure_maps_to_bad_gateway`, `tool_history_validation_body_reports_invalid_request`, `unknown_model_prefix_body_reports_model_not_found`, `upstream_unknown_model_fault_maps_to_not_found` |
| H13h | `gateway::session_header_tests` | `gateway.rs:664` | `canonical_session_header_wins_when_all_are_present`, `opencode_session_id_is_used_alone`, `session_affinity_header_is_used_alone`, `blank_candidate_is_skipped_for_the_next_one`, `no_session_header_yields_none` |
| H13i | `gateway_integration_test` | `avrig-api/tests/gateway_integration_test.rs` | `test_model_resolver`, `test_llm_provider_client_registry`, `test_gateway_route_handlers`, `test_unknown_model_prefix_is_rejected_before_dispatch`, `test_unknown_sub_model_under_direct_provider_maps_to_not_found` |

Count correction that must not be papered over. The plan and the handover both describe **ten** tests in `direct_provider_session_header_tests`. The suite actually contains **eight**, verified with `cargo test -p avrig-gateway --lib -- --list | Select-String direct_provider_session_header_tests`, and all eight are named in H13a above. The eight cover every behaviour the "ten" was meant to protect: session passthrough, generated UUID, absent session header, blank header name, forward policy allowing an application agent, forward policy still blocking library agents, literal policy, and absent policy. Record the count before and after with that exact command, and require the same eight names to be present and green. Any new forward-header tests belong in the separate `direct_provider_forward_header_tests` module, so this suite stays at eight and the mismatch is resolved in favour of measurement rather than renumbered to match the prose.

H13 is satisfied by H13a and H13h together, specifically the four `forward_policy_*` and `absent_policy_*` cases plus `inbound_session_id_reaches_the_provider`.

Scope of this table, stated so it is not mistaken for full coverage. The nine suites above are the ones this change can plausibly reach: every test that builds a direct provider, every test that walks the chat handler, and the resolver. Measured today, `cargo test -p avrig-gateway --lib -- --list` reports 56 names, and these suites account for 32 of them, leaving 24 in `antigravity::converter`, `antigravity::oauth`, and `antigravity::quota`. Those are not enumerated here because the change touches no converter, OAuth, or quota code. They are still guarded, by P2: record the full 56-name list before and after and require it to match, which is what catches an accidental edit outside the listed suites without making this table pretend to an authority it does not have.

One regression risk this table cannot express, and it needs saying because the design now touches it. `add_direct_provider` changes from five positional parameters to three plus a `DirectProviderOptions` value at six call sites, and `DirectProviderAccount` gains a field while still deriving `Clone` only. If the options struct or the new field loses `Clone`, the crate fails to compile rather than failing a test, so P1's `cargo check` is the gate and H13's green suites are the confirmation. The eight `direct_provider_session_header_tests` cases are the ones that would catch a mistake in moving `session_header` and `user_agent` into the options struct, which is why they are enumerated by name rather than counted.

### Free Model Verification

This section decides whether the release is worth making, because objective 4 is the user-visible win. Every expectation was measured on 2026-11-19 against `http://127.0.0.2:8000/v1`. Re-measure and quote observed values; do not copy these forward without re-running.

Body file for every curl in this section:

```powershell
$p = 'C:\Users\wwidj\AppData\Local\Temp\opencode\free.json'
$json = '{"model":"oc-composync/beam-free","messages":[{"role":"user","content":"reply with exactly: free-works"}],"max_tokens":64}'
[System.IO.File]::WriteAllText($p,$json,(New-Object System.Text.UTF8Encoding($false)))
```

`max_tokens: 64` and the "reply with exactly" instruction are both load-bearing. At `max_tokens: 16` these reasoning models spend the whole budget on `reasoning_content` and return `finish_reason: "length"` with empty `content`, which is a 200 that does not prove the model answered. Measured: `beam-free` at 16 tokens gave empty `content` and `finish_reason: "length"`; at 64 tokens it gave `content: "free-works"` and `finish_reason: "stop"`.

Send with `curl.exe -sS -o $out -w "%{http_code}" --max-time 90 -H "content-type: application/json" --data-binary "@$p" http://127.0.0.2:8000/v1/chat/completions`.

| ID | Model | Expected | Fail condition |
|---|---|---|---|
| H16a | `oc-composync/beam-free` | `200`; body contains `"choices"`; `choices[0].message.content` contains `free-works`; returned `model` is `beam-free`. Measured exactly this | Any non-200, missing `"choices"`, empty `content`, or a `model` other than `beam-free` |
| H16b | `oc-composync/longcat-2.5-free` | `200`; `"choices"` present; non-empty `content`; `model` is `longcat-2.5-free`. Measured 200 | As above. Do not require the literal `free-works`: this model phrases differently, so the assertion is non-empty content plus the model id |
| H16c | `oc-composync/hy4-flash-free` | `200`; `"choices"` present; non-empty `content`; `model` is `hy4-flash-free`. Measured 200 | As above |
| H16d | `oc-composync/beam-free` at `"max_tokens": 16`, everything else identical to H16a | `200` with `"choices"` present, even though `content` may be empty and `finish_reason` is `"length"`. Documents that a low cap is a client budgeting issue, not a gateway fault, so a future empty answer is not misread as a regression | Any non-200, or a missing `"choices"` |
| H17a | `oc-composync/iceman-contributor-free`, prefixed | **`502`** whose body contains both `trains on request data` and `https://opencode.ai/console/org_01M72468PMBQ51MKCPZFK55TVC/settings/privacy#training`. Measured exactly this. Both substrings are required so the test proves the actionable remedy reaches the caller instead of being swallowed by the error envelope. The 502 rather than 400 comes from `chat_completion_error_status` at `avrig-api/src/gateway.rs:316-331`, which maps a 400 to 404 only when the body names the model as unknown; this 400 does not, so it falls through to `(BAD_GATEWAY, "upstream_error")` | A missing substring, a different status, or a body that drops the console URL. A privacy-gate 502 is the documented result for this row, never a product failure |
| H17b | Direct to the Go path, bypassing the gateway: `curl.exe` against `https://opencode.ai/inference/go/v1/chat/completions` with `Authorization: Bearer <OPENCODE_COMPOSYNC_API_KEY>`, `x-opencode-session: ses_probe`, and body `{"model":"iceman-contributor-free",...}` | **`400`** with the same privacy text. Measured exactly this. Establishes that the missing session header is not the cause, and that the 502 in H17a is purely the gateway's error mapping | Any status other than 400, or a body without `trains on request data` |
| H17c | Conditional: the toggle-enabled case. Re-run H17a exactly | If it returns `200` with `"choices"`, the org toggle is on and the row PASSES on 200. If it returns the H17a 502 with `trains on request data`, the toggle is off and the row records **`SKIP (toggle off)`**, not FAIL. Detect state from the body alone: `trains on request data` means off, `"choices"` means on | A third outcome, for example a 200 without `"choices"` or a 502 with different text, is a genuine FAIL. Never report `SKIP` as either pass or failure; count it separately |
| H17d | Routing trap: bare `{"model":"iceman-contributor-free",...}` with no provider prefix, sent to `http://127.0.0.2:8000/v1/chat/completions` | **`502`** with `{"error":{"message":"Upstream HTTP 403: This service has been disabled in this account for violation of Terms of Service. Please submit an appeal to continue using this product.","type":"upstream_error"}}`. Measured exactly this. An unprefixed model that names no provider falls through to a default backend and produces an unrelated Terms of Service 403, so the row documents the missing-prefix trap and proves the prefix is mandatory | Any status other than 502, or a body without `disabled in this account`. Critically, this must not be confused with H17a: the privacy gate and the ToS block are different failures with different remedies |
| H18a | Real client: `cd D:\Cloud\OneDrive\AI\Agentic; opencode run --standalone -m avrig/oc-composync/beam-free "reply with exactly: free-works"` | Exit 0 and output contains `free-works`. Measured: exit 0, output line `free-works` | Non-zero exit, or output without `free-works`. Note that `opencode.exe` writes through PowerShell as a NativeCommandError record even on success, so judge on `$LASTEXITCODE` and the captured `Out-String`, never on the presence of stderr records |
| H18b | `opencode run --standalone -m avrig/oc-composync/longcat-2.5-free "reply with exactly: free-works"` | Exit 0 and output contains `free-works`. Measured: exit 0, match true | As above |
| H18c | `opencode run --standalone -m avrig/oc-composync/hy4-flash-free "reply with exactly: free-works"` | Exit 0 and output contains `free-works`. Measured: exit 0, match true | As above |
| H18d | `opencode run --standalone -m avrig/oc-composync/iceman-contributor-free "say ok"` | The row PASSES when the run reaches the privacy gate, meaning the output or resulting error names `trains on request data` or the console privacy URL. A non-zero exit is expected. This proves routing works and the only remaining blocker is an account setting. Measured through the gateway path: 502 with the privacy text | A model-unavailable error, an unknown-model error, or no mention of the privacy gate, any of which would mean the picker entry does not route |
| H19a | Gated model through the gateway: `oc-composync/deepseek-v4.1-flash-free` | **`404`** with `{"error":{"message":"Provider 'oc-composync' does not offer model 'oc-composync/deepseek-v4.1-flash-free'","type":"model_not_found"}}`. Measured exactly this. The model is absent from the Go catalogue, so `validate_direct_provider_model` rejects it locally before dispatch and no upstream call happens | Any other status, or a body that does not name the provider and model. This is the correct expected result, not a failure |
| H19b | The same model direct to the Go path: `https://opencode.ai/inference/go/v1/chat/completions` with `Authorization: Bearer <OPENCODE_COMPOSYNC_API_KEY>`, `x-opencode-session: ses_probe`, body `{"model":"deepseek-v4.1-flash-free",...}` | **`400`** with `{"error":{"type":"server_error","message":"Model deepseek-v4.1-flash-free isn't included in OpenCode Go. See the models it includes at https://opencode.ai/console/go."}}`. Measured exactly this. Proves the exclusion is upstream policy, not a gateway bug, and that the gateway's 404 is the tidier rendering of the same fact | Any status other than 400. This row is the evidence that closes objective 3 |
| H19c | Objective 3's actual subject, real client: `cd D:\Cloud\OneDrive\AI\Agentic; opencode run --standalone -m avrig/opencode/deepseek-v4.1-flash-free "reply with exactly: free-ds-works"` after the `st_` credential and `x-opencode-org-id` are configured | **`200`** and output containing `free-ds-works`. The caller is the real CLI, so the body shape is genuine and the credential is now `st_`. This is the row that proves the defect is fixed rather than documented. **This row additionally requires a picker entry that does not exist yet:** measured 2026-11-19, `.opencode/opencode.json` has `opencode/deepseek-v4.1-flash` at line 70 but no `opencode/deepseek-v4.1-flash-free` anywhere, and `opencode run -m avrig/opencode/deepseek-v4.1-flash-free` fails with `Error: Model unavailable: avrig/opencode/deepseek-v4.1-flash-free` and exit 1 before any HTTP request is made. So phase 8 is no longer verification-only: it must add this one key, or H19c records `BLOCKED (picker entry missing)` and objective 3 cannot be measured at all | Non-empty output without the marker, a non-zero exit, or a 429 in the log. A 429 here means the credential change did not take effect and is a genuine FAIL. `Model unavailable` is `BLOCKED`, not FAIL, because the gateway never saw the request |
| H19d | The same model through the gateway from a **hand-written minimal body**: `{"model":"opencode/deepseek-v4.1-flash-free","messages":[{"role":"user","content":"ok"}],"max_tokens":8}` sent with `--data-binary` to `http://127.0.0.2:8000/v1/chat/completions` | **`502`** carrying `FreeUsageLimitError`, and this is **PASS**. Measured verbatim on 2026-11-19 with the current deployed 0.3.0 binary and the existing `{env:OPENCODE_API_KEY}` credential: `{"error":{"message":"Direct provider upstream error: {\"type\":\"error\",\"error\":{\"type\":\"FreeUsageLimitError\",\"message\":\"Free usage limit reached. Free models work in OpenCode (https://opencode.ai); subscribe to OpenCode Go to keep going: https://opencode.ai/go\"}}","type":"upstream_error"}}`. Two things follow, both useful. The gate keys on body shape, so a synthetic body is refused by design, and this row can be run today without waiting for the credential change, which makes it the cheapest early check that the `opencode` route is alive at all. Separately it means a 502 here is not evidence that the credential fix failed, because this probe never used the `st_` token | A 200 here would be the surprising result: it would mean the gate is weaker than measured, or that something is fabricating content. Investigate rather than celebrate. Any 502 whose body omits `FreeUsageLimitError`, for example a connection or DNS error, is a genuine FAIL because it would mean the route itself broke |
| H20a | Health after deploy | `Invoke-RestMethod http://127.0.0.2:8000/v1/health` gives `ok: true` and the six provider names. Measured pre-change: `0.3.0`, six providers, `accounts_count` 6 | A missing provider, or `ok` not `true` |
| H20b | Version after deploy | `Invoke-RestMethod http://127.0.0.2:8000/v1/version` gives `semver` equal to the built version, `0.4.0` after phase 10 | A `semver` that does not match the tag |
| H20c | Config landed on Windows | `Select-String -Path D:\avrig\config\gateway.toml -Pattern "forward_headers","analyze_headers","user_agent"` | All three appear inside the `[gateway.providers.opencode]` block, proving `deploy.ps1` did not restore the old file over the new one | Any of the three missing, or present under a different provider |
| H20d | Config landed on WSL, per finding 11 | `Select-String -Path \\wsl.localhost\avrig-ai\opt\avrig\config\gateway.toml -Pattern "providers.oc-composync","forward_headers","analyze_headers"` | Every pattern that the plan's scope requires on that node is present. Measured today: the file exists and lists only `ollama`, `opencode`, and `composync`, with **no `oc-composync` block at all**, because `deploy.ps1` copies only the binary to Linux and never the config. Two acceptable outcomes, and the plan must state which: either `Infra` writes the block and all three patterns are found, or the plan declares the WSL node out of scope and this row records `N/A (WSL out of scope)` with that decision cited. | Patterns missing while the node is claimed in scope. A silently stale node passing as success is the failure this row exists to prevent |
| H21 | Streaming on a working Go model: `oc-composync/beam-free` with `{"model":"oc-composync/beam-free","messages":[{"role":"user","content":"reply with one word"}],"stream":true,"max_tokens":64}` via `curl.exe -sS -N --max-time 90` | The last two frames are a chunk whose `finish_reason` is non-empty (`stop` or `length`) and a terminal `data: [DONE]`. Measured pre-change on `oc-composync/deepseek-v4.1-flash`: `finish_reason: "length"` then `data: [DONE]` | An empty or missing `finish_reason`, or a missing `[DONE]` |
| H22a | Picker has exactly four free entries with `name` equal to key: `oc-composync/beam-free`, `oc-composync/longcat-2.5-free`, `oc-composync/hy4-flash-free`, `oc-composync/iceman-contributor-free`. Read `providers.avrig.models` and filter names matching `oc-composync/*free*` | Those four keys, each with `name` identical to the key. Measured today: already true | A missing entry, a `name` that differs from its key, or `iceman-contributor-free` omitted. Omitting it contradicts the user's 2026-11-19 decision |
| H22b | `oc-composync/deepseek-v4.1-flash-free` is deliberately absent from the picker | No key matching that string under `providers.avrig.models`. Measured today: absent | Present in any form. Listing it would be a dead entry with no actionable remedy |

`iceman-contributor-free` is listed on purpose, with its privacy toggle documented rather than hidden. H17a and H18d keep that decision verified: the entry must exist, and it must route to the real gate so the documented remedy is the one the user actually sees.

Independent re-verification, 2026-11-19, run while attaching this matrix against the deployed 0.3.0 binary. Recorded because a matrix that has only ever been written from the plan's prose is not evidence. Every row below reproduced its stated expectation exactly:

| Row | Observed | Matches |
|---|---|---|
| V16a | `200`, `model=beam-free`, `content=[free-works]`, `finish_reason=stop` | yes |
| V16b | `200`, `model=longcat-2.5-free`, `finish_reason=stop`, non-empty content | yes |
| V16c | `200`, `model=hy4-flash-free`, `finish_reason=stop`, non-empty content | yes |
| V16d | `200`, `choices` present, `finish_reason=length`, content length 0 | yes, and this is the point of the row |
| V17a | `502`, body contains both `trains on request data` and `settings/privacy#training` | yes |
| V17d | `502`, body contains `disabled in this account`, does **not** contain `trains on request data` | yes, and it confirms the two failures are distinguishable by body alone |
| V19a | `404`, body names the provider and model as `model_not_found` | yes |
| V19c | `Model unavailable: avrig/opencode/deepseek-v4.1-flash-free`, exit 1, no HTTP request | no, and that is a `BLOCKED`, not a gateway failure |
| V19d | `502`, body contains `FreeUsageLimitError` | yes |
| V22a | exactly four `oc-composync/*free*` entries, `name` equal to key for each | yes |
| V22b | no `deepseek-v4.1-flash-free` key under `oc-composync/` | yes |

These `V` identifiers are evidence about rows, not rows themselves, so they are deliberately outside the H numbering and the runner does not execute them.

Two consequences for the runner. The live rows that use the existing `oc-composync` credential are healthy right now, so a later failure there is a real regression rather than a pre-existing condition. And H19c is the only live row that cannot run today, for three independent reasons recorded in the amendments: no picker entry, no `{file:}` secret source, and no token file on disk. Fixing only one of the three will not move it.

The privacy-gate rows (H17a to H17d) and the working-model rows (H16a to H18c) must never be merged in reporting. A privacy-gate 502 is a documented result for the gated model and irrelevant to the three models that serve; a 200 on the gated model after the toggle is also not evidence for the others.

### Outbound Equivalence

`oc-composync` declares no passthrough, so its outbound header set must be identical before and after. Capture twice and diff. H14b covers the same property in Rust, but this manual capture is the only row that exercises the real config and the real key.

| ID | Layer | What it asserts | Method |
|---|---|---|---|
| H14a | equivalence | The `oc-composync` outbound header set is byte-identical before and after the change: same names in the same sorted order with the same values, with `authorization` compared through its fingerprint and credential length. Proven by E1 to E4 below | Manual capture diff, `Compare-Object` or `git diff --no-index` |

E1, before any edit, preserve the baseline binary. `New-Item -ItemType Directory -Force C:\Users\wwidj\AppData\Local\Temp\opencode\oc-equiv; Copy-Item D:\avrig\avrig.exe C:\Users\wwidj\AppData\Local\Temp\opencode\oc-equiv\baseline-avrig.exe`. The deployed 0.3.0 binary measured today is 40401920 bytes, `Get-FileHash` `8398A848DB6B4AF5140A733464F3C55080F0B07EC1AEF71066DA7D680EE21C08`. This run has already been performed: the baseline capture and `oc-composync-baseline.txt` are stored at `avrig-ai/lab/oc-equiv/`, and the seven observed header lines are quoted at the end of this section. Stored, not committed: `lab/` is git-ignored wholesale by the hygiene rule at `.gitignore` line 37, which is the correct default for a directory that has held live credentials. Re-run the capture only if the deployed binary differs from that hash.

E2, at baseline time, freeze one experiment config directory and reuse it unchanged for the candidate run. Build it once, here, and never rebuild it after any source edit.

```powershell
$tmp = 'C:\Users\wwidj\AppData\Local\Temp\opencode\oc-equiv\config'
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $tmp | Out-Null
Copy-Item -Path 'D:\avrig\config\*' -Destination $tmp -Recurse -Force
$override = @'
[gateway]
host = "0.0.0.0"
port = 8010

[gateway.providers.oc-composync]
base_url = "http://127.0.0.1:8899/v1"
'@
[System.IO.File]::WriteAllText("$tmp\zz-override.toml", $override, (New-Object System.Text.UTF8Encoding($false)))
```

`New-Item` before `Copy-Item` is not decoration. `Copy-Item 'D:\avrig\config\*' $tmp -Recurse` into a path that does not exist creates `$tmp\config\` and puts the files one level too deep, so the write of `zz-override.toml` fails with `DirectoryNotFoundException`. That was observed here.

Freezing matters because the candidate run must differ from the baseline in the binary only. If the directory were rebuilt after the source edit, a `gateway.toml` change could move a header and the diff would accuse the code. Record `Get-FileHash` of `gateway.toml` and `zz-override.toml` once, note it in the evidence, and confirm both hashes are unchanged before the candidate run. Measured today: `gateway.toml` `237C17079E1DB5D7288CF962484F25D25F9665084467680FBBDEC68682FCDA52`.

`load_config` (L1334 to L1388) reads every `*.toml` in the directory, sorts the file names, and deep-merges in that order, so `zz-override.toml` sorts last and wins on the keys it names. Because the merge recurses into tables, the `oc-composync` entry keeps its `enabled`, `api_key`, `session_header`, and `user_agent`, and only `base_url` changes. That matters: the capture must exercise the real session and User-Agent policy, because those are the headers whose stability is the claim. `port = 8010` leaves the production node on 8000 alone. Confirmed on this host: the overridden binary answered `200` on `http://127.0.0.2:8010/v1/chat/completions`, so the directory form of `--config` works with the deployed build.

E3, capture. The key must be in the process environment, and it is not where a first attempt usually looks.

```powershell
$env:OPENCODE_COMPOSYNC_API_KEY = [Environment]::GetEnvironmentVariable('OPENCODE_COMPOSYNC_API_KEY','Machine')
"key length in process: $($env:OPENCODE_COMPOSYNC_API_KEY.Length)"
powershell -NoProfile -Command 'if($env:OPENCODE_COMPOSYNC_API_KEY){$env:OPENCODE_COMPOSYNC_API_KEY.Length}else{0}'

$cap = 'C:\Users\wwidj\AppData\Local\Temp\opencode\oc-equiv\cap-baseline'
$sink = Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','D:\Cloud\OneDrive\AI\Agentic\avrig-ai\lab\capture-server.ps1','-BindAddress','127.0.0.1','-Port','8899','-MaxRequests','4','-MaxSeconds','60','-OutDir',$cap,'-Label','oc-base' -PassThru -WindowStyle Hidden -RedirectStandardOutput "$cap\sink.log"
Start-Sleep 4
$gw = Start-Process 'C:\Users\wwidj\AppData\Local\Temp\opencode\oc-equiv\baseline-avrig.exe' -ArgumentList '--config',$tmp,'gateway' -PassThru -WindowStyle Hidden -RedirectStandardOutput "$cap\gw.log"
Start-Sleep 8
```

Two traps, both hit on this host, both of which silently weaken the result rather than failing loudly.

`OPENCODE_COMPOSYNC_API_KEY` lives at **Machine** scope, not User. Reading it from `User` returns empty, `resolve_env_var` substitutes an empty string, the empty key is dropped, and the provider sends **no `authorization` header at all**. The capture still succeeds at `200`, so the run looks healthy while never exercising the header whose stability is the claim. Always read `Machine`, always print the length, and treat a length of `0` as a void run rather than a pass. Measured lengths today: `OPENCODE_COMPOSYNC_API_KEY` 51 at Machine, 0 at User.

`pwsh` is not installed on this host, and this shell is Windows PowerShell 5.1 running unelevated. `Start-Process pwsh` fails with "cannot find the file specified", and an `HttpListener`-based sink fails without a URL ACL reservation. The middle dot is literal in neither case: launch the sink with `powershell` and keep it on `TcpListener`, which is what `lab/capture-server.ps1` now does. Also check port 8899 is free first, because a sink left from an earlier run holds it and the new one exits with "Only one usage of each socket address". A stale listener produces the same `502 upstream_error` a real defect would, so clear it before interpreting any result.

Send, with every caller header spelled out so both runs are identical:

```powershell
$body = '{"model":"oc-composync/model-under-test","messages":[{"role":"user","content":"ping"}]}'
[System.IO.File]::WriteAllText("$env:TEMP\ping.json",$body,(New-Object System.Text.UTF8Encoding($false)))
curl.exe -sS -o "$cap\reply.out" -w "%{http_code}" --max-time 30 -H "content-type: application/json" -H "user-agent: opencode/latest/2.3.2/cli" -H "x-opencode-session: ses-equiv-fixed" -H "x-opencode-project: proj-equiv-fixed" -H "x-opencode-client: cli" --data-binary "@$env:TEMP\ping.json" http://127.0.0.2:8010/v1/chat/completions
```

Use `model-under-test`, not a real free model. `validate_direct_provider_model` treats a non-200 catalogue as `CatalogueState::Unavailable` and dispatches without validation, and the sink answers `GET /models` with `404` on purpose, so any name works and the sink never has to enumerate ids. That is why the sink is not required to serve a catalogue.

Pinning `user-agent` and `x-opencode-session` on the curl command is also load-bearing, for two independent reasons. Without a caller `user-agent`, curl sends `curl/8.x`, which `forward_policy` classifies as a library agent and replaces with the gateway default `opencode/1.0.0`, so the captured value would test the wrong branch. Without a caller session header, the gateway generates a fresh UUID v4 on every run, so two captures of identical code differ on `x-opencode-session` and H14a fails with no code change. Both were observed: the first baseline attempt captured `user-agent: opencode/1.0.0` and a random `3a07f776-...` session. Send it non-streaming so the sink answers plain JSON; the request head is identical either way, and H10b plus H21 cover streaming.

E4, normalise and diff. From the newest `captures/*-002.json` in each run directory, map each `headers[]` entry to `(name.ToLower(), value)` when `redacted` is false, and to `(name.ToLower(), sha256_16 + ':' + credential_length)` when true. Sort by name. Write `oc-composync-baseline.txt` and `oc-composync-candidate.txt`, then `Compare-Object` the two.

H14a passes only when the two normalised lists are identical line for line: same names, same sorted order, same values. `authorization` compares through its fingerprint and credential length, which is what the sink records, and the same key is used in both runs so the fingerprint matches. `host` and `content-length` are comparable because both runs use port 8010 and the same body. Any added, removed, or changed line fails H14a and routes to `be`.

A determinism check belongs here, before the change, and it was run today. Two baseline captures with the pinned headers produced `IDENTICAL` on all seven lines, so the procedure itself does not introduce drift. If two pre-change captures differ, the diff will not mean anything and the procedure is wrong, not the code.

The measured pre-change `oc-composync` outbound set, exported verbatim to `avrig-ai/lab/oc-equiv/oc-composync-baseline.txt`:

```text
accept: */*
authorization: fp=9bacf2091ce8424b len=58 scheme=Bearer
content-length: 74
content-type: application/json
host: 127.0.0.1:8899
user-agent: opencode/latest/2.3.2/cli
x-opencode-session: ses-equiv-fixed
```

Seven headers. `x-opencode-project` and `x-opencode-client` were sent by the caller and correctly do not appear, which is the property H14a protects. `authorization` is the gateway's own key, 58 bytes for a 51-character key plus `Bearer `, and its fingerprint is stable across runs.

E5, after the change, confirm H14b is green, which keeps the same property enforced without the manual capture.

### Reporting

| Row kind | Required evidence |
|---|---|
| Unit rows, new module and dispatch (H1a to H12d, H14b, H27b) | The exact test name, the command (`cargo test -p avrig-gateway --lib <name>`), and the verbatim `test result:` line |
| Handler rows (H1c, H24, H25, H25b) | The same, plus the rendered profile string or accessor value the assertion compared against |
| Config-source rows (H27a) | The test name, `cargo test -p avrig --bin avrig <name>`, and the verbatim result line. The fixture path must be a `$env:TEMP` file, never the real `D:/avrig/config/secrets/` path, so the test cannot pass or fail based on production state |
| Integration rows (H15, H15b, H15c) | The test name, `cargo test -p avrig --test gateway_integration_test`, and the captured stub header map printed with `{:#?}` so the wire truth is in the log, not only inside an assertion |
| Regression rows (H13a to H13i) | The suite name, the command, the count before and after from P2, and the verbatim result line |
| Free model rows (H16a to H19d, H22a, H22b) | The full command, the HTTP status, `choices[0].message.content`, the returned `model` field, and for H18a to H18d the `$LASTEXITCODE` plus the captured output. `SKIP` rows record the branch that produced the skip, namely the body containing `trains on request data` |
| Live rows (H20a to H20d, H21) | The command, the status, and the last two SSE frames or the health and version JSON copied verbatim |
| Equivalence rows (H14a, H14b) | Both capture file paths, both normalised lists, the diff output, and the `Get-FileHash` of both binaries |
| Profile rows (H25b) | The emitted log line verbatim, fingerprint retained, no raw value |

Any FAIL routes back to `be` with three things: the failing test name exactly as it appears in the output, the expected versus actual text, and the file and function under test. A unit, handler, or integration FAIL blocks phase 7 and therefore the release. A live FAIL blocks the same, with these exceptions, which are documented results and not failures: H17a's privacy-gate 502, H17b's 400, H17c's `SKIP (toggle off)`, H18d's non-zero exit carrying the privacy text, H19a's 404, H19b's 400, H19d's 502 carrying `FreeUsageLimitError`, and H20d's `N/A (WSL out of scope)` when the plan scopes that node out. Every one of those still requires its evidence recorded, because a documented result with no captured body is indistinguishable from a test nobody ran.

One status has no exemption and should not be granted one. If H19c returns a 429, that is a genuine FAIL, because a 429 on the free tier is precisely the symptom this plan exists to remove, and the row is written to prove the `st_` credential took effect. Do not add a 429 exemption to the list above without reopening objective 3.

`BLOCKED` is a third outcome, distinct from PASS and FAIL, and it applies only to H19c and H27a. It means the mechanism the row tests is absent rather than broken: the `st_` file missing, the `{file:}` source unimplemented, or the static `headers` map not wired. Report it as `BLOCKED` with the missing mechanism named, route it to `be` as an unimplemented design item, and block the release exactly as a FAIL would. The distinction exists so that "the gateway is wrong" and "the gateway is not finished" are never reported as the same thing.

Report the free-model section as six separate lines, never aggregated:

1. Three working `oc-composync` models PASS (`beam-free`, `longcat-2.5-free`, `hy4-flash-free`).
2. `oc-composync/iceman-contributor-free` as `SKIP (toggle off)` or `PASS`.
3. `oc-composync/deepseek-v4.1-flash-free` as an expected 404 plus its upstream 400, proving the Go path does not carry it.
4. `opencode/deepseek-v4.1-flash-free` from the real CLI as the 200 that objective 3 actually asks for.
5. The same model from a synthetic body, recorded as PASS on its documented 502, which is what stops line 4 being misread as body fabrication.
6. The missing-prefix trap as a distinct ToS 502.

An aggregated "free models: 4/5" line is exactly the reporting the plan's own evidence discipline rejects. Note the pre-log for line 4: if the `st_` token is absent or expired, or the `{file:}` source is unimplemented, line 4 records `BLOCKED (credential)` rather than `FAIL`, and that distinction is the difference between an unfinished design task and a broken gateway. `BLOCKED` blocks the release just as `FAIL` does, but it routes to `be` as a missing mechanism instead of a defect.

Seven amendments follow, each attached to a test row that fails if the gap is left unfixed. Two are closed (1 and 3), one is half-landed (2), and four are open (4, 5, 6, 7). Amendments 5, 6, and 7 are new with this revision, and they are the ones that matter, because the plan's root cause moved from "document the 502" to "make the 200 happen" and those three mechanisms do not exist yet. All three block the same single row, H19c.

1. **Closed.** H11 needs an apply-time `NEVER_RELAY` skip. The apply loop now calls `is_denied_name(name)` and `is_token_shaped(value)` in addition to the `user-agent` and session-header skips, so a relay set containing `authorization` cannot reach the wire even if a policy names it.
2. **Half-landed.** H25 needs a path for the flag to reach the handler. The design's answer is an account field plus an accessor, which is correct. But `DirectProviderOptions` as written at design section 4 (lines 301-309) declares only `session_header`, `user_agent`, and `forward_headers`; it does **not** declare `analyze_headers`. So `main.rs` has nowhere to pass `analyze_headers = true` from the config, and the accessor H25 asserts against would always return the default `false`. `be` must add `pub analyze_headers: bool` to `DirectProviderOptions` alongside the other three fields, and copy it onto `DirectProviderAccount` in `add_direct_provider`. H25 and the whole of objective 1 pass through that single missing field.
3. **Closed.** The token-shape length threshold is now `MIN_TOKEN_LIKE_LEN = 32`, with the predicate defined as strictly greater than the constant. H7e pins the boundary so a flipped comparison cannot pass.
4. **Open, owned by `be`.** The integration stub must be able to report inbound headers. The stub at `gateway_integration_test.rs` L180-217 parses only the request line and exposes nothing about headers, and `ChatResponse` ignores unknown fields, so a stub cannot answer a header assertion by echoing into its body. It must capture the request head and publish it to the test, for example through a shared `Arc<Mutex<Vec<(String,String)>>>` the test reads after `oneshot` returns. H15, H15b, and H15c depend on this, so it is part of the phase 5 scope rather than an optional cleanup.
5. **Open and it blocks objective 3, owned by `be`.** The design now requires a mechanism that is described in config but does not exist in the code path. `x-opencode-org-id` is declared as `headers = { "x-opencode-org-id" = "wrk_01..." }` on the `opencode` block, and design section 4 says a `headers` map must be added to `GatewayProviderConfig` because the current config has no way to express a static outbound header. Confirmed against source: `GatewayProviderConfig` at `avrig-api/src/main.rs:160-171` has `base_url`, `api_key`, `api_keys`, `enabled`, `session_header`, and `user_agent`, with no `headers`. It is absent from `DirectProviderOptions` too, and `direct_provider_request` applies only User-Agent, Authorization, the session header, and the relayed set, so even after the config field existed the value would never reach the wire. The config field, the options field, and the composer line are all required. H27b is the row that proves it landed. Without this, objective 3's 200 cannot be achieved, because the console provider requires that header.
6. **Open, owned by `be`, and it blocks objective 3 as well.** The `{file:PATH}` secret source does not exist. `resolve_env_var` at `avrig-api/src/main.rs:1154-1162` expands only `{env:VAR}` and otherwise returns the literal string, so `api_key = "{file:D:/avrig/config/secrets/opencode_console_token}"` would today be sent as a bearer token whose value is that literal path text. The failure mode is bad: the provider presents a nonsense credential, upstream answers 401 or 429, and it reads like the credential gate this plan set out to fix. Worse, `D:/avrig/config/secrets/` does not exist on this machine right now, so there is no token to read even once the source is implemented. H27a proves the source works and P6 measures whether the file is present.

7. **Open, owned by `fe`, and it also blocks objective 3.** The phase 8 note in the plan says the four picker entries already exist so the phase "needs verification, not editing". That is true for the four `oc-composync` entries and false for the one this plan's objective 3 needs. `.opencode/opencode.json` carries `opencode/deepseek-v4.1-flash` at line 70 and no `opencode/deepseek-v4.1-flash-free` at all. Measured: `opencode run --standalone -m avrig/opencode/deepseek-v4.1-flash-free "hi"` exits 1 with `Error: Model unavailable: avrig/opencode/deepseek-v4.1-flash-free`, before any request reaches the gateway. The same command with a nonsense model id fails identically, which confirms the failure is picker-side rather than upstream. So phase 8 must add one key: `"opencode/deepseek-v4.1-flash-free": { "name": "opencode/deepseek-v4.1-flash-free" }`. H19c records `BLOCKED (picker entry missing)` until it lands. Back up the file first, as the risk table already requires.

Two notes on feasibility rather than gaps.

`H12d` is the only row that distinguishes a correct duplicate guard from a lucky one, and it needs the caller-supplied session header to differ from `input.session_id`. The plan's data flow supports that, because `session_id_for(input)` and `forwarded_headers` are independent inputs, so the row is writable as designed.

`H17d` relies on an unprefixed model falling through to a default provider, which is current behaviour on the non-streaming path when Antigravity accounts exist and the prefix is absent. Design section 5b now clears `forwarded_headers` in that branch, which does not change the status this row measures but does mean H9b and H17d guard the same fallback from two directions: H9b asserts no header leaks into it, H17d asserts the observable error. If `be` removes the fallback entirely the row becomes a `404 model_not_found` instead of the ToS 502, which is still a valid result to record but must be recorded as a behaviour change rather than silently re-baselined.

One inconsistency in the design that H7c will catch, so it is recorded here rather than left to fail in the build. The doc comment on `header_profile` at design section 3 names five token prefixes (`sk-`, `oc_sk_`, `st_`, `ghp_`, `eyJ`) plus a separate `Bearer`-scheme clause, while the doc comment on `is_token_shaped` at design section 5 names seven (`Bearer `, `sk-`, `oc_sk_`, `st_`, `rt_`, `ghp_`, `eyJ`). The gap is `rt_`: it appears in the refusal predicate and nowhere in the profile predicate. H7c asserts all seven redact, so a `header_profile` implemented literally from its own doc comment fails on the `rt_` fixture. `be` should implement `header_profile` by calling `is_token_shaped` rather than restating the prefixes, which makes H7f a structural guarantee instead of a coincidence. H7d deliberately draws its six short fixtures from the non-`Bearer` prefixes, because `Bearer` is redacted on the scheme alone with no length condition.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Passthrough becomes a credential leak | deny at capture, deny again at apply, refuse token-shaped values by shape, test asserting `x-opencode-ticket` and `Authorization` never arrive |
| A wildcard pattern forwards `cookie` or `x-api-key` | shipped policy uses exact names only; `NEVER_RELAY` is re-checked at apply; prefixes under 3 chars or without `-` are rejected |
| Log volume from the header profile | one `info` line per request, at most 32 facts, behind a per-provider opt-in that only `opencode` enables |
| Adding a `ChatRequest` field breaks literals | 3 literals and 6 registrations enumerated; `build` fails fast if one is missed |
| Header policy drift between the two dispatch paths | one `direct_provider_request` composer, so the deny logic has a single home |
| Caller headers reach a provider the model never named | `forwarded_headers` cleared in the fallback branch, asserted by a stub test |
| A live credential leaks into `lab/` artifacts again | `.gitignore` ignores `lab/` wholesale; scripts redact credential-shaped values; `tester` greps for `st_`, `oc_sk_`, `sk-` before release |
| The WSL node silently runs a stale config | plan scopes the feature to the Windows node and says so, so the stale node is a stated boundary rather than a surprise |
| The retry is read as a promise the gated model will work | objective 3 measures; objective 4 carries the user-visible win |
| Editing the live client config breaks the picker | back up `opencode.json` first, verify `name` equals key convention, confirm with `opencode models` |
| Two gateway config files diverge and deploy reverts the change | both files edited; H20a, H20b, and H20c run after deploy |

## Decision Log

| Decision | Choice | Reason |
|---|---|---|
| New field vs generalize `session_id` | new `forwarded_headers` | zero risk to the shipped Go path |
| Capture all vs capture per provider | capture at edge, filter at provider | one request serves providers that want nothing; policy stays in config |
| Default passthrough posture | deny, opt in per provider | no provider changes behaviour silently |
| Deliver free models via | `oc-composync` picker entries | already working, verified 200 and end to end |
| `iceman-contributor-free` | list it, document the privacy toggle | user decision; surfacing the toggle beats hiding the model |
| Root cause of the free-tier 429 | `oc_sk_` credentials are refused on free models; the console OAuth `st_` token is required | measured: same body, `st_` gives 200 and `OPENCODE_API_KEY` gives 429 |
| `opencode` provider credential | console OAuth `st_` token via a new `{file:PATH}` source | the correct credential is not in the environment and rotates |
| `x-opencode-org-id` | static config header, not caller passthrough | it is a fixed tenant id declared by the console provider config |
| Body shape | forward the caller's body unchanged | the gate keys on the real CLI shape; padding it would fabricate requests |
| Gated free model | expect 200 from the real client, 502 from a synthetic body | the two callers are genuinely different and both results are correct |

## Open Questions

1. **Token rotation.** The `st_` console token expires 2026-12-15. Options A (`{file:...}` refreshed by hand), B (read from the client credential store and refresh on 401), and C (device-code OAuth in the gateway) are compared under "Open design question: token rotation". Recommendation is A now, B if the token must outlive the client login. This needs a decision before implementation, because shipping a token that dies in 26 days repeats the defect being fixed.
2. Should `lab/` eventually be committed as reproducible evidence, now that it is gitignored wholesale and stripped of credential artifacts? The safe default is in place; a commit decision can follow once the plan lands.
3. `analyze_headers` is a per-provider config flag rather than an environment variable, because it is opt-in by nature and only `opencode` enables it. Confirm that granularity if another provider ever needs it.
4. `iceman-contributor-free` is listed per the user decision and its privacy toggle is documented. Should the picker entry carry a user-facing hint, or is the plan-documented console link enough?
5. `x-opencode-org-id` is now sent as a **static config header** rather than caller passthrough, and it is on `NEVER_RELAY` so caller-supplied values cannot override it. This resolves the earlier open question by measurement: the console provider config declares it as a fixed tenant id, not caller state.

## Review Findings

Audited 2026-11-19 against the current revision (header targets `0.5.0`, tester matrix attached). Checked against source in `avrig-api` and `avrig-lib/crates/avrig-gateway`, both lockfiles, the live gateway on `http://127.0.0.2:8000/v1`, both deployed config trees, and the live client config. Line numbers below were re-read from source, not copied from the plan. I re-measured the unit-test counts myself with `cargo test -- --list` rather than trusting P2.

**Verdict: `blocked`.** Two blockers, both security, both a few lines to fix. The measurement work in this revision is genuinely good: the honest negative result on the gated model, the four-way disambiguation of privacy gate / ToS block / catalogue miss / upstream 400, and the count correction at line 458 are all verified accurate. Do not change that. Fix the two blockers and the plan is executable.

### Findings

| # | Severity | Concerns | Finding | Fix |
|---|---|---|---|---|
| 1 | blocker | Security, objective 2, lines 157-161 and 303-309 | `NEVER_RELAY` does not contain `x-opencode-ticket`, `x-api-key`, `x-auth-token`, `api-key`, `x-goog-api-key`, or `www-authenticate`. The plan records at line 43 that the CLI sends `x-opencode-ticket` carrying a live `st_` console token, and the shipped policy is `x-opencode-*`. That header therefore survives capture, matches the prefix, is not skipped at apply (it is neither `user-agent` nor the session header), and is relayed to `opencode.ai`. Objective 2 and Security Note line 341 both assert credentials can never be relayed, and both are false for the one credential header the plan itself names. Exposure is loopback-scoped, but the shipped design contradicts its own stated invariant. | Add the six names to `NEVER_RELAY`, and add a rule that any `x-opencode-*ticket*` name is refused. Add H11b: a captured `x-opencode-ticket` never appears in `select_relayable` output for the shipped policy. |
| 2 | blocker | Objective 5, `lab/` commit, line 290 and Open Question 1 | `avrig-ai/lab/serve-trace.err` holds 115 KB of unredacted `Authorization: Bearer st_<redacted>-...` material. `lab/` is entirely untracked today (`git status` reports `?? lab/`), the only relevant ignore rule is `*.log` at `.gitignore:14`, and the plan proposes committing the scripts while ignoring `captures/` and "lab backups". That would stage `serve-trace.err` plus 61 `.txt`, 112 `.json`, and `.jsonl/.backup/.pid/.native/.deadport` artifacts under `lab/replay-*/`. Credential material in git history cannot be withdrawn. | Invert the rule: ignore `lab/*` first, then `!lab/README.md` and `!lab/*.ps1`. At minimum add `*.err`, `lab/serve-trace.err`, `lab/replay*/`, `*.jsonl`, `*.backup`, `*.pid`, `*.native`. Add a pre-commit scan of `lab/` for `st_`, `sk-`, `oc_sk_` before anything is staged. |
| 3 | major | Version, line 6 and phase 10 | `version_target: 0.5.0` and "SemVer `minor` to 0.5.0" cannot both hold. HEAD is `0.3.0` in `avrig-api/Cargo.toml:3` and `avrig-ai/Cargo.toml:12`, and both repositories tag only up to `0.3.0`. A minor bump from 0.3.0 is 0.4.0. 0.5.0 skips a version. | Set the target to `0.4.0` (or state which 0.4.0 release carried what), and correct H20b's expected `semver`. |
| 4 | major | Objective 3, test coverage | Objective 3's actual subject, `opencode/deepseek-v4.1-flash-free` through the gateway, has no row in the matrix. H19a covers `oc-composync/deepseek-v4.1-flash-free` (404) and H19b covers the direct Go endpoint (400), but neither exercises the model and path objective 3 is about. I measured it: `502` with body `Direct provider upstream error: {... "FreeUsageLimitError" ...}`. Without that row objective 3 is unfalsifiable. | Add H19c: `opencode/deepseek-v4.1-flash-free` through `http://127.0.0.2:8000/v1`, expect `502` whose body contains `FreeUsageLimitError`, and record `server-timing` if present. Rewrite objective 3 to name 502 explicitly, since `chat_completion_error_status` at `gateway.rs:316-331` cannot emit the upstream 429. |
| 5 | major | Line 60, measurement table | The table says `oc-composync/deepseek-v4.1-flash-free` returns 400 "isn't included in OpenCode Go" through the gateway. Measured now: `404` with `{"error":{"message":"Provider 'oc-composync' does not offer model 'oc-composync/deepseek-v4.1-flash-free'","type":"model_not_found"}}`, because `validate_direct_provider_model` rejects it locally before dispatch (`client.rs:496-520`). The 400 is the direct Go endpoint's answer, which H19b already records correctly. | Change line 60's gateway column to 404 `model_not_found` and keep the 400 attributed to the direct path only. Line 333 already gets this right, so the two places disagree. |
| 6 | major | Objective 1, lines 198 and 345 | `analyze_headers` emits `tracing::debug!`, but both deployed configs run at `info`: `D:\avrig\config\config.toml` and `/opt/avrig/config/config.toml` both set `[logging] level = "info"`, consumed at `avrig-api/src/main.rs:802-809`. As designed the analysis half of objective 1 produces no output in production, so H25b can pass in tests and the capability still be dead on the node. Log volume and rate limiting are also unaddressed on the busiest route, with up to 32 facts per request. | Either state that enabling the profile requires `level = "debug"` and add that to the deployment step, or emit one rate-limited `info!` line (for example one per 10 s per provider) so it works at the deployed level. Add a risk row for log volume and name the limiter. |
| 7 | major | Security, lines 244-256 and 592 | The apply-time guard still skips only `user-agent` and the session header, so it is not a deny list. Any name absent from `NEVER_RELAY` and matched by a policy is relayed, including a `Bearer` or `st_` value sitting in an unexpected name, and any prefix shorter than the namespace (for example `x-*`) matches `x-api-key` and `x-auth-token`. The tester's amendment 1 already requires the `NEVER_RELAY` re-check; that amendment must land in the design section, not only in the amendment list. | Re-check `NEVER_RELAY` inside the apply loop, and refuse token-shaped values (`Bearer `, `st_`, `sk-`, `oc_sk_`, long `eyJ`) regardless of name, reusing the same predicate `header_profile` needs. Reject prefixes shorter than 3 characters that contain no `-`. |
| 8 | major | Design completeness, lines 284 and 575 | Nothing in the design section says how `analyze_headers` reaches `handle_chat_completions`. `GatewayState` (`gateway.rs:23-28`) carries only `client`, `local_only`, and `pending_oauth`, and the flag lives on `GatewayProviderConfig` (`main.rs:159-171`), which the handler cannot see. Amendment 2 identifies this but the design and target-file tables do not. Seven `GatewayState` literals need updating: `main.rs:1177`, `1220`, `1449`; `gateway.rs:509`; `gateway_integration_test.rs:56`, `130`, `230`. | Fold amendment 2 into section 4: give the account `analyze_headers: bool`, register it through the same call, expose it via an accessor, and list the seven literals in the target-file table. |
| 9 | major | Line 147, compile | The `HeaderPattern` snippet has no derive. `DirectProviderAccount` derives `Clone` only (`client.rs:41`) and is cloned out of the map on every dispatch through `find_direct_provider` (`client.rs:160-170`), so a non-`Clone` field makes the crate fail to compile. | Restore `#[derive(Clone, Debug, PartialEq, Eq)]`. Consider `enum HeaderPattern { Exact(String), Prefix(String) }`, which removes the `prefix` plus `Option<String>` state that can represent an impossible value. |
| 10 | major | Fallback paths, lines 240-256 | The relay loop is described as applying in both dispatch functions unconditionally, which includes the empty-antigravity fallback where the provider is `directs.values().next()` (`client.rs:664-674` non-stream, `731-737` stream). HashMap order is arbitrary, so a caller's `x-opencode-project`, session ids, and trace context can be sent to a provider the model string never named. Finding 1 makes this worse. | Apply the relay only when dispatch came from an explicit model prefix, or require fallback providers to declare an empty `forward_headers` and assert it. Add an H9b row for the fallback path. |
| 11 | major | Deployment, lines 286-287 and 358 | Two config files are named, three exist. `deploy.ps1:96-103` copies the repo file over `D:\avrig\config\gateway.toml`, but the Linux branch (`deploy.ps1:139-147`) copies only the binary and never touches `/opt/avrig/config/gateway.toml`, which today lacks `[gateway.providers.oc-composync]` entirely. Phase 7 claims "deploy both targets" and H20c only greps the Windows file. | Add `/opt/avrig/config/gateway.toml` to the edited list with the copy step that applies it, or make `deploy.ps1` sync config on both targets. Add an H20d that reads the WSL file. |
| 12 | major | Objective 4, phase 8, line 289 | Objective 4 is already delivered. `.opencode/opencode.json` already contains all four entries with `name` equal to key: `oc-composync/beam-free` (line 38), `hy4-flash-free` (line 51), `iceman-contributor-free` (line 53), `longcat-2.5-free` (line 58). P7 records the same. Phase 8 and the edited-files row therefore edit a live client config for no behaviour change, which is risk without benefit. | Reframe objective 4 as verification (H22 already does exactly that) and delete phase 8 and the `opencode.json` row, or replace objective 4 with work that does not yet exist. Do not book shipped behaviour as a deliverable. |
| 13 | minor | Line 232 | "Five call sites" for `add_direct_provider` is wrong. There are six: `main.rs:1141`, `client.rs:2155`, `2407`, `2627`, `gateway_integration_test.rs:38`, `222`, with the definition at `client.rs:228`. | Correct to six. Finding 8 makes it six sites gaining two arguments, not one. |
| 14 | minor | Lines 130-137, 593 | Of the ten `ChatRequest` sites listed, seven need no edit. `client.rs:1866`, `2418`, `2638` and `converter.rs:985`, `1079`, `1337`, `1415` are all `serde_json::from_value`, and `#[serde(skip)]` defaults the field during deserialization. Only three true literals exist: `gateway_integration_test.rs:97`, `143`, `main.rs:2509`. | Mark the seven as "no change required" and change the risk row to "3 literals, 6 registrations". |
| 15 | minor | Line 226 versus 230 | The parameter is typed `Vec<HeaderPattern>` while normalization is said to mirror `client.rs:236-251`, which normalizes inside the method. Those conflict: parsing must then happen in `main.rs` and in five test helpers, not in one place as the house style does for `session_header` and `user_agent`. | Take `Vec<String>` and parse inside `add_direct_provider`, dropping blanks and unparseable patterns there. Invalid patterns then degrade to "not forwarded" per the existing style. |
| 16 | minor | Lines 240-254, H10b | The loop is duplicated into `execute_direct_provider_non_stream` (`client.rs:1535-1544`) and `execute_direct_provider_stream` (`1566-1575`), two blocks already identical for UA, auth, and session. A fourth concern in both guarantees drift, and H10b exists only because of that duplication. | Extract one `fn direct_request_headers(req, direct, input) -> reqwest::RequestBuilder` composing UA, authorization, session, and relay, and call it from both. The deny logic then has one home. |
| 17 | minor | Line 218-227 | A sixth positional parameter, four of them optional once amendment 2 lands, reads `None, None, Vec::new(), false` at every call site. | Introduce `DirectProviderOptions { session_header, user_agent, forward_headers, analyze_headers }` with `Default` and take one argument. Call sites then survive future growth. |
| 18 | minor | Line 208 | `analyze_headers: Option<bool>` is tri-state for a boolean; `None` and `Some(false)` behave identically but force an unwrap in the wiring. | `#[serde(default)] pub analyze_headers: bool`, which parses `analyze_headers = true` unchanged. |
| 19 | nit | Line 22 versus 316-321 | Objective 4 says "three free models", the Configuration block lists four (including `iceman-contributor-free`), and line 323 says all four are listed. | Make objective 4 read four, or three plus the separately documented `iceman` entry. |
| 20 | nit | Lines 156-161, naming | `NEVER_RELAY` carries no per-entry rationale, and the house style explains the why (`client.rs:236-251`, `gateway.rs:301-304`). `headers.rs` and `profile` are vague for a policy plus redaction module and a function that returns facts. | Group the constant with one comment per class (credentials, framing, hop-by-hop), rename the module to `header_policy.rs` and `profile` to `header_profile`. |
| 21 | nit | Amendment 1, line 573 | The claim that `reqwest::RequestBuilder::header` calls `headers_mut().append(...)` could not be verified locally (no vendored reqwest source). The conclusion is still right, because H11 asserts wire behaviour rather than internal semantics. | Drop the internals citation or verify it against `reqwest` docs, and let H11 carry the argument. |

### Disposition

The plan was revised after this audit. Every finding is accounted for below.

| # | Severity | Disposition |
|---|---|---|
| 1 | blocker | **Closed.** `NEVER_RELAY` now carries `x-opencode-ticket`, `x-api-key`, `api-key`, `x-auth-token`, `x-goog-api-key`, `www-authenticate`, `x-opencode-org-id`, grouped by class with a per-group comment. The shipped `opencode` policy switched from `x-opencode-*` to eight exact names, which removes the wildcard-over-a-credential-namespace problem at its root rather than relying on the deny list alone. |
| 2 | blocker | **Closed.** `lab/` is gitignored wholesale. A cleanup pass deleted the credential-bearing logs and `replay-*` artifacts and confirmed nothing reached git history, since the directory was never tracked. Scripts that logged raw headers are patched to redact by name and by value shape. |
| 3 | major | **Closed.** `version_target` and phase 10 both read `0.4.0`, and H20b expects `0.4.0`. |
| 4 | major | **Closed, then superseded.** H19c was added as the audit asked, but the root cause found afterwards changed its expectation: it now expects `200` from the real client, and H19d carries the documented `502` for a synthetic body. Objective 3 was rewritten to match. The finding that objective 3 was untestable stands, and the fix went further than the audit proposed because the credential was the real defect. |
| 5 | major | **Closed.** Line 60's gateway column now reads `404 model_not_found`, with the 400 attributed to the direct Go path only, and the two are reconciled against `validate_direct_provider_model`. |
| 6 | major | **Closed.** `analyze_headers` emits at `info`, matching the deployed `level = "info"`, one line per request capped at 32 facts. The risk table gained a log-volume row. |
| 7 | major | **Closed.** The apply loop gained `is_denied_name` and `is_token_shaped` guards, both shared with `header_profile` so redaction and refusal cannot drift. Prefix patterns under three characters or without a `-` are rejected at registration. |
| 8 | major | **Closed.** `analyze_headers` is resolved as a per-provider config flag surfaced through the provider account, constructed via `DirectProviderOptions` rather than a positional chain. The `GatewayState` literal sites are noted for the implementer. |
| 9 | major | **Closed.** `HeaderPattern` derives `Clone, Debug, PartialEq, Eq`. |
| 10 | major | **Closed.** New section 5b: `forwarded_headers` is cleared in the fallback branch so a provider the model never named receives nothing, asserted by a stub test. |
| 11 | major | **Closed by scoping.** New Deployment Target Note states the feature is Windows-node only, matching the 0.3.0 decision that the gateway role is Windows-only, so the stale WSL config is a stated boundary rather than a latent surprise. |
| 12 | major | **Closed.** Objective 4 reframed as verification, phase 8 changed to confirm rather than edit, and the `opencode.json` edited-files row removed. |
| 13 | minor | **Closed.** Corrected to six registration sites. |
| 14 | minor | **Closed.** The seven `from_value` sites are marked no-change; only three true literals need the field. |
| 15 | minor | **Closed.** `add_direct_provider` takes `Vec<String>` and parses inside the method, matching the `session_header` precedent. |
| 16 | minor | **Closed.** One `direct_provider_request` composer called from both dispatch paths, so the deny logic has a single home. |
| 17 | minor | **Closed.** `DirectProviderOptions` with `Default` replaces the positional chain. |
| 18 | minor | **Closed.** `#[serde(default)] pub analyze_headers: bool`. |
| 19 | nit | **Closed.** Objective 4 names all four entries including `iceman-contributor-free`. |
| 20 | nit | **Closed.** `NEVER_RELAY` is grouped with per-class rationale; module renamed `header_policy.rs`, function `header_profile`. |
| 21 | nit | **Closed.** The reqwest internals citation is dropped; H11 carries the argument on wire behaviour. |

One finding was partly overtaken by events: the audit's own measurement of `oc-composync/deepseek-v4.1-flash-free` returning 404 is what the plan now records, which supersedes the earlier 400 claim in both places.

### Verified correct

Each item below was checked against source, live system state, or a measured run, not against the plan's own prose.

- `#[serde(skip)]` on `pub forwarded_headers: Vec<(String, String)>` compiles without an explicit `Default` bound: `skip` implies `Default` on deserialize and `Vec` is unconditionally `Default`. The precedent at `antigravity/types.rs:192-197` works identically.
- `add_direct_provider` really does take five parameters today (`client.rs:228-235`) and is called from exactly six places, as listed in finding 13. `DirectProviderAccount` is constructed in exactly one place (`client.rs:255`) and derives `Clone` only (`client.rs:41`), so finding 9 is a real compile concern.
- The three true `ChatRequest` literals are `gateway_integration_test.rs:97`, `143`, and `main.rs:2509`; `avrig-ai/test/src/antigravity/types.rs:168` is a genuinely independent struct and is correctly excluded.
- Shared-type claim holds: one `http` 1.5.0 in `avrig-api/Cargo.lock:1167-1174` and `avrig-lib/Cargo.lock:371-379`; `axum 0.8.9` (`Cargo.lock:246-247`) and `reqwest 0.12.28` (`Cargo.lock:2488-2489`) both depend on it. `avrig-api/src/gateway.rs:10` already imports `axum::http::HeaderMap`. Relying on unification is sound rather than fragile, because any drift becomes a compile error at the call site rather than a silent mismatch. No conversion boundary needed.
- `GatewayProviderConfig` has no `deny_unknown_fields` (`main.rs:159-171`), so the TOML block at lines 296-310 parses as written: `Option` fields need no `#[serde(default)]` and the trailing comma in the array is valid TOML 1.0.
- `deploy.ps1:96-103` does overwrite `D:\avrig\config\gateway.toml` from the repo, exactly as stated. The omission is the WSL file (finding 11).
- No retry, backoff, or second-attempt path exists in `client.rs`, so `forwarded_headers` cannot be applied twice or to a rotated key. One attempt per call at `client.rs:621` and `:707`. Finding 10 is the only unintended-destination risk.
- SIWC and antigravity ignore `forwarded_headers`: `siwc/client.rs:165-179` sets its own four headers and the converter never touches transport headers. No leak through the shared `ChatRequest`.
- Live free-model results reproduce the plan's central win: `oc-composync/beam-free`, `longcat-2.5-free`, and `hy4-flash-free` all return 200; `/v1/models` lists exactly four `oc-composync/*-free` ids; `/v1/health` returns `ok: true`, six providers, `semver 0.3.0`, `accounts_count 6`.
- The four-way failure disambiguation is accurate, and I reproduced every branch: `iceman-contributor-free` with prefix gives 502 wrapping `trains on request data` plus the console URL; without the prefix gives 502 with `disabled in this account for violation of Terms of Service`; `oc-composync/deepseek-v4.1-flash-free` gives 404 `model_not_found`; `deepseek-v4.1-flash-free` direct to Go gives 400 "isn't included in OpenCode Go". These are genuinely distinct failures with distinct remedies, and keeping them separate in reporting is the right call.
- The count correction at line 458 is correct and I confirmed it independently: `cargo test -p avrig-gateway --lib -- --list` reports **56 tests**, of which **8** are `direct_provider_session_header_tests`, and all eight names in H13a exist. `cargo test -p avrig --lib -- --list` reports **15** `gateway::` tests including **5** `gateway::session_header_tests`, matching P2 and H13h. Resolving the "ten" in favour of measurement was the right judgement.
- The suite locations in H13a to H13i match source: `client_contract_tests:1817`, `usage_stream_tests:1940`, `direct_stream_relay_tests:2087`, `direct_provider_catalogue_tests:2364`, `direct_provider_session_header_tests:2552`.
- P1's `--exclude avrig-desktop` is correct: `avrig-desktop` is a member of the `avrig-ai` workspace only (`avrig-ai/Cargo.toml:3-9`, name at `apps/desktop/src-tauri/Cargo.toml:2`), while `avrig-lib` and `avrig-api` are separate single-workspace builds.
- P3's warning is well founded: `127.0.0.1:8000` is the WSL node, whose `/opt/avrig/config/gateway.toml` has no `oc-composync` block at all, so results there would be meaningless for these models.
- The `iceman` picker entry and its toggle documentation are a defensible product decision, and H17c's `SKIP (toggle off)` vocabulary is better than either pass or fail. `name` equals key across all four entries today, so H22a is writable as specified.

### Effect on the goal set

Yes, and three of the changes are load bearing.

Findings 1 and 7 mean objective 2's guarantee, "the gateway's own `Authorization`, `Host`, and framing headers are never overridable by passthrough", is not met by the shipped policy. The goal stays, the design does not. Both must be closed before `be` starts, because they change the module's constants, its apply loop, and its test list.

Finding 6 makes objective 1 conditional on a log level the deployment does not use, so objective 1 as written cannot be demonstrated on the node. It needs an explicit level decision or a rate-limited `info` emission named in the plan.

Findings 4 and 5 reshape objective 3 from "a 200 with content passes, otherwise a documented result" into "record 502 with `FreeUsageLimitError` for the OpenAI path, 404 for the same model on the Go path, and 400 direct to Go". That is more precise than the current wording and is what the measurements actually support.

Finding 12 removes objective 4 as a deliverable, since all four picker entries and all three 200s already exist. The honest phrasing is verification of shipped behaviour, which H22 and P7 already do.

The remainder are implementation corrections that do not move the target. The plan's measurement discipline, its refusal to claim the gated model works, and its separation of privacy gate from ToS block are the strongest parts of this document and should survive the revision unchanged.
