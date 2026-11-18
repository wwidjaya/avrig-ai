---
title: Knowledge Search on opencode/big-pickle with a Single /api/v1/knowledge/search Endpoint
status: superseded
superseded_by: 2026-11-18-release-0.3.0-consolidated.md
created: 2026-11-18
revised: 2026-11-18 (single endpoint, legacy routes removed, 410 tombstones)
canonical_path: avrig-ai/plans/2026-11-18-document-search-opencode-big-pickle.md
owner: plan
repos:
  - avrig-api
  - avrig-ai
  - avrig-lib
tags:
  - knowledge-search
  - gateway
  - routing
---

# Knowledge Search on opencode/big-pickle with a Single /api/v1/knowledge/search Endpoint

## Goals and Objectives

1. Knowledge search answers are synthesized by the `opencode` direct provider using `big-pickle`, addressed as `opencode/big-pickle`, inheriting `[gateway.providers.opencode]` and authenticating with `OPENCODE_API_KEY`.
2. Exactly one search endpoint exists: `GET` and `POST` `/api/v1/knowledge/search`. The `stream` option (body field on POST, query parameter on GET) selects SSE versus JSON. There is no `/api/v1/knowledge/search/stream` route.
3. The legacy routes `/api/v1/documents/search`, `/api/v1/documents/search/stream`, `/v1/documents/search`, `/v1/documents/search/stream`, and `/v1/search` are removed. They answer `410 Gone` with a JSON hint naming the new endpoint, so no caller silently receives the SPA HTML.
4. Both runtime nodes serve the same effective answer model through `<exec dir>/config/server.toml`: `D:\avrig\config\server.toml` and `/opt/avrig/config/server.toml`.
5. Deployment stays repeatable: `make deploy` propagates the answer model without clobbering per-node `config.toml`, credential files, or listener bindings.
6. Verification is measurable: a live request with `stream: true` returns `metadata`, `answer_delta`, `citations`, and `done`, a request with `stream: false` returns `SearchResponse` JSON, removed paths return `410`, and logs name `provider=opencode` with no `SubModelNotFound`.
7. Release rides on the open 0.3.0 release plan (`avrig-ai/plans/2026-11-18-release-0.3.0.md`, version sources currently `0.2.1`, tags published only up to `0.2.1`). This work is added to that release instead of opening a second bump; if 0.3.0 has already shipped by execution time, the bump becomes the next minor (`0.4.0`). Tag `X.Y.Z` in `avrig-ai`, `avrig-api`, `avrig-lib`, and `avrig-ui`.

## Key Detailed Design

### Program Design

**Route table after the change (avrig-api)**

```text
GET  /api/v1/knowledge/search   -> knowledge_search_get   JSON or SSE, chosen by ?stream=
POST /api/v1/knowledge/search   -> knowledge_search       JSON or SSE, chosen by body.stream

410  /api/v1/documents/search
410  /api/v1/documents/search/stream
410  /v1/documents/search
410  /v1/documents/search/stream
410  /v1/search
```

Document management routes stay untouched: `/api/v1/documents/by-hash/{sha256}`, `/api/v1/documents/upload`, `/api/v1/documents/{id}/sources`.

**Why explicit 410 tombstones.** `src/web.rs` (`static_asset_handler`, L12-31) serves `index.html` with `200` for any unknown path that contains no dot. If the search routes were simply deleted, a stale caller would get HTML with a 200 and fail inside `response.json()` with a parse error. Registering the five removed paths to a single handler that returns `StatusCode::GONE` plus `{"error": "..."}` makes the break explicit and greppable in logs.

```rust
async fn search_endpoint_moved() -> (StatusCode, axum::Json<serde_json::Value>) {
    (
        StatusCode::GONE,
        axum::Json(serde_json::json!({
            "error": "This search endpoint was removed. Use /api/v1/knowledge/search; pass stream: true or Accept: text/event-stream for SSE."
        })),
    )
}

// before with_state
for path in [
    "/api/v1/documents/search",
    "/api/v1/documents/search/stream",
    "/v1/documents/search",
    "/v1/documents/search/stream",
    "/v1/search",
] {
    app = app.route(path, axum::routing::any(search_endpoint_moved));
}
```

`any` is required, not `get`, because stale callers used both `GET` and `POST` and the response must be identical for all methods. The tombstone sits inside the authenticated surface but returns before any auth work, which is deliberate: a `410` is a routing fact, not a data leak.

**Request contract**

```text
POST /api/v1/knowledge/search
{ "query": "cryptographic signed lifecycle",
  "limit": 5,
  "threshold": 0.1,
  "stream": true }

GET /api/v1/knowledge/search?q=cryptographic+signed+lifecycle&limit=5&threshold=0.1&stream=true
```

| Field | Type | Default | Notes |
| :--- | :--- | :--- | :--- |
| `query` | string | required | `q` or `query` accepted on GET; existing validation rules (`MAX_SEARCH_QUERY_CHARS`, `MAX_SEARCH_LIMIT`, finite threshold) unchanged |
| `limit` | integer | 5 | 1..=MAX_SEARCH_LIMIT |
| `threshold` | float | absent, falls back to `server.search_threshold` | unchanged |
| `stream` | bool, optional | absent | `Some(true)` forces SSE, `Some(false)` forces JSON, absent defers to `Accept` |

**Stream resolution rule**

```rust
fn resolve_stream(requested: Option<bool>, headers: &HeaderMap) -> bool {
    requested.unwrap_or_else(|| {
        headers
            .get(header::ACCEPT)
            .and_then(|v| v.to_str().ok())
            .is_some_and(|v| v.to_ascii_lowercase().contains("text/event-stream"))
    })
}
```

`Option<bool>` (not `bool`) is deliberate: only an explicit `false` must override an `Accept: text/event-stream` header, and an absent field must fall back to header negotiation. Existing stream clients already send `Accept: text/event-stream`, so they keep working even before they add `stream: true`.

**Handler decomposition (src/main.rs)**

The current code duplicates the whole auth, embed, retrieve, rerank, and rank path in `execute_search` (L2352-2414) and `execute_search_stream` (L2515-2567). Merging the endpoints collapses that duplication:

```text
struct SearchOutcome { query: String, count: usize, reranked: bool, results: Vec<SearchHit> }

retrieve_search(&AppState, &HeaderMap, &SearchRequest) -> Result<SearchOutcome, (StatusCode, String)>
    bearer auth when oidc is configured (unchanged messages and status codes)
    payload.validate()
    embedder.embed(query)
    search_candidates.search_vectors(candidate_limit)
    request_rerank(...)
    rank_search_hits(..., threshold)

render_json(SearchOutcome) -> Response        // axum::Json(SearchResponse)
render_sse(AppState, SearchOutcome) -> Response  // existing Sse stream builder, moved verbatim

knowledge_search(State, HeaderMap, Json<SearchRequest>) -> Result<Response, (StatusCode, String)>
    let outcome = retrieve_search(...)?;
    if resolve_stream(payload.stream, &headers) { Ok(render_sse(...)) } else { Ok(render_json(...)) }

knowledge_search_get(State, HeaderMap, Query<SearchQueryParams>) -> Result<Response, (StatusCode, String)>
    builds SearchRequest { query, limit, threshold, stream } from params, then the same two-step path
```

Delete `execute_search`, `execute_search_stream`, `search_documents`, `search_documents_stream`, and `search_documents_get` once their bodies live in the new helpers. `SearchQueryParams` gains `pub stream: Option<bool>`; `SearchRequest` gains `#[serde(default)] stream: Option<bool>`. The SSE event payload types (`SseMetadata`, `SseAnswerDelta`, `SseCitations`, `SseDone`, `SseError`) and `build_grounded_chat_request` are unchanged.

Two mechanics decide whether this compiles cleanly:

1. **Ownership.** `render_sse` destructures `SearchOutcome` by value so `metadata` serializes from borrowed fields and then `results` moves into `SseCitations`. `state.gateway.clone()` and `state.answer_model` are read before the `async_stream` block, as today.
2. **Direct call sites in tests.** `stream_returns_empty_answer_when_no_hits` (L4552) and `stream_citations_match_metadata_count_with_mixed_scores` (L4593) call the handler function directly. They become `knowledge_search(..., axum::Json(SearchRequest { stream: Some(true), .. }))` and parse the SSE body from the returned `Response`. Every other `SearchRequest { .. }` literal gains `stream: None`.

**Answer model resolution (unchanged mechanics, new value)**

```text
model string        opencode/big-pickle
provider prefix     opencode  (registered direct provider, case-insensitive)
base model          big-pickle (forwarded upstream unchanged)
upstream            POST https://opencode.ai/inference/openai/v1/chat/completions
auth                Authorization: Bearer $OPENCODE_API_KEY
precedence          registered direct provider wins over Antigravity
validation          GET {base_url}/models; big-pickle is present, so it passes
catalogue outage    request forwarded unchecked (degrade, not fail)
missing API key     dispatch fails, SSE emits the existing fallback delta
```

No change is needed in `avrig-lib/crates/avrig-gateway/src/resolver.rs` or `client.rs`; `opencode` is already a builtin prefix and the direct-provider path is generic.

**API key unification**

`config/gateway.toml` resolves `{env:OPENCODE_API_KEY}` through `resolve_env_var`. The separate OpenCode passthrough adapter (`src/opencode.rs`, used only by `/v1/chat/completions`, `/api/v1/chat/completions`, and `/api/v1/opencode/chat/completions`) defaults to `OPENCODE_CONSOLE_API_KEY`. Align it to `OPENCODE_API_KEY` so one key name serves both paths.

**Config propagation (deployment)**

`load_config` deep-merges every `*.toml` in `<exe dir>/config` alphabetically, so each node reads its own directory:

```text
D:\avrig\config\config.toml    node.id = vault-watcher, roles = watcher,reranker,gateway
/opt/avrig/config/config.toml  node.id differs, roles = server
/opt/avrig/config/server.toml  host = 127.0.0.1 (loopback only, must not widen)
D:\avrig\config\               currently has no server.toml (falls back to the compiled default)
```

The deploy step therefore patches only the `answer_model` line of `server.toml` per target, creating the file from a minimal safe template when absent. It never copies `config.toml`, never rewrites `host` or `port`, and never touches `antigravity*.json` or `chatgpt*.json`.

**Callers that must move with the endpoint**

| Caller | File | Current path | New call |
| :--- | :--- | :--- | :--- |
| Web JSON search | `apps/web/src/shared/api/client.ts` L110-114 | `GET /api/v1/documents/search` | `GET /api/v1/knowledge/search` |
| Web SSE search | `apps/web/src/shared/api/client.ts` L116-145 | `POST /api/v1/documents/search/stream` | `POST /api/v1/knowledge/search` with `stream: true` |
| Package JSON search | `packages/api-client/src/index.ts` L157-161 | same | same |
| Package SSE search | `packages/api-client/src/index.ts` L164-197 | same | same |
| Ingest smoke script | `avrig-api/scripts/test_ingest.sh` L32-53 | `POST /api/v1/documents/search` | `POST /api/v1/knowledge/search` |
| UI components | `apps/web/src/modules/knowledge/KnowledgeChat.tsx` | via client methods | no edit, both methods keep their signatures and response shapes |

Reference calls after the change, useful for `tester` and for the README rewrite:

```bash
# JSON
curl -sS -X POST https://app.avrig.ai/api/v1/knowledge/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"cryptographic signed lifecycle","limit":3}'

# SSE
curl -sS -N -X POST https://app.avrig.ai/api/v1/knowledge/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"query":"cryptographic signed lifecycle","limit":3,"stream":true}'

# Removed path
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST https://app.avrig.ai/api/v1/documents/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"test"}'   # expect 410
```

### Target Program Files (Mandatory)

**avrig-api**

| File | Change |
| :--- | :--- |
| `src/main.rs` | Replace the five search routes with a single `/api/v1/knowledge/search` route (GET + POST) and `any(search_endpoint_moved)` tombstones for the removed paths. Add `retrieve_search`, `render_json`, `render_sse`, `resolve_stream`, `knowledge_search`, `knowledge_search_get`. Add `stream: Option<bool>` to `SearchRequest` and `SearchQueryParams`. Change `default_answer_model()` to `opencode/big-pickle`. Retarget the two direct handler calls in tests (L4552, L4593) and add `stream: None` to every other `SearchRequest { .. }` literal. Rewrite `server_health_and_search_routes_respond` for the new surface plus `410` assertions. Update pinned default-model test assertions. |
| `config/server.toml` | `answer_model = "opencode/big-pickle"`. |
| `config/opencode.toml` | `api_key_env = "OPENCODE_API_KEY"`. |
| `src/opencode.rs` | `default_api_key_env()` returns `OPENCODE_API_KEY`. |
| `scripts/deploy.ps1` | Propagate the answer model into `D:\avrig\config\server.toml` and `/opt/avrig/config/server.toml` for `-Target all` and each single target. |
| `scripts/test_ingest.sh` | Point the four search curls at `/api/v1/knowledge/search`. |
| `README.md` | Document the single endpoint, the `stream` option, the 410 tombstones, and that answers route through the `opencode` provider. |

**avrig-ai**

| File | Change |
| :--- | :--- |
| `apps/web/src/shared/api/client.ts` | Both helpers target `/api/v1/knowledge/search`; the stream helper sends `stream: true` and keeps `Accept: text/event-stream`. |
| `packages/api-client/src/index.ts` | Same two edits, including the `baseUrl` branch of the stream helper. |
| `apps/web/dist/` | Rebuilt by `pnpm --filter @avrig/web build` (embedded at Rust build time via `rust-embed`). |
| `packages/api-client/dist/` | Rebuilt declaration output, no hand editing. |

**avrig-lib**

No source changes. Read-only reference: `crates/avrig-gateway/src/resolver.rs` (builtin prefixes) and `crates/avrig-gateway/src/client.rs` (direct provider dispatch and catalogue validation).

**Deployed runtime targets**

| Path | Change |
| :--- | :--- |
| `D:\avrig\config\server.toml` | Created or patched with `answer_model = "opencode/big-pickle"`. |
| `/opt/avrig/config/server.toml` | Patched; `host`, `port`, and `search_threshold` preserved; owner `avrig:avrig`, mode `0644`. |
| `D:\avrig\avrig.exe`, `/opt/avrig/avrig` | Replaced by `make deploy` with the newly compiled binaries. |

### EDM Design

No schema, column, constraint, or migration change. The search pipeline continues to read existing vector tables through `state.search_candidates`; only the answer model and the HTTP surface change.

## Parallel Execution Plan

| Phase | Stream | Owner | Work | Depends on |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Design | plan | Route merge, stream negotiation rule, tombstone decision, deploy patch strategy | none |
| 2a | Backend | be | Handler refactor, single route, 410 tombstones, `default_answer_model`, opencode key defaults, tests | Phase 1 |
| 2b | Frontend | fe | Two client files, web build, api-client build | Phase 1 |
| 2c | Scripts and docs | be | `scripts/test_ingest.sh`, `README.md`, `scripts/deploy.ps1` answer-model propagation | Phase 1 |
| 3 | Gate | analyst | Audit the plan against coding principles before implementation merges | Phase 1 |
| 4 | Build gate | build | `cargo test -p avrig`, `cargo build --release` (Windows and Linux via WSL), web and api-client builds | 2a, 2b, 2c |
| 5 | Deploy | Infra | `make deploy` to `D:\avrig` and `/opt/avrig`, restart both services, confirm config values in place | Phase 4 |
| 6 | Verify | tester | Live verification matrix, then ask `analyst` to audit goal achievement | Phase 5 |
| 7 | Release | build | Fold into `2026-11-18-release-0.3.0.md`: build, deploy, verify live, then `scripts/release.ps1 minor -NoPush`, tag `0.3.0`, push branch and tag to all four repos | Phase 6 |
| 8 | Retrospective | km | Record the provider switch, the endpoint merge, and the SPA fallback trap in the Vault | Phase 7 |

Streams 2a, 2b, and 2c touch disjoint files and run concurrently. Phase 5 is sequential against Phase 4 because both act on the compiled binary.

## Test Specification and Validation Matrix

To be authored and attached by `tester` before implementation begins. Planned coverage:

| ID | Layer | Check |
| :--- | :--- | :--- |
| T1 | Unit | `default_answer_model()` returns `opencode/big-pickle`. |
| T2 | Unit | Router matches `GET` and `POST` `/api/v1/knowledge/search`. |
| T3 | Unit | Removed paths (`/api/v1/documents/search`, `/api/v1/documents/search/stream`, `/v1/documents/search`, `/v1/documents/search/stream`, `/v1/search`) return `410` with a JSON `error` naming the new endpoint. |
| T4 | Unit | `resolve_stream` truth table: `Some(true)` true, `Some(false)` false even with an SSE `Accept`, absent plus SSE `Accept` true, absent plus JSON `Accept` false. |
| T5 | Unit | `build_grounded_chat_request` places `opencode/big-pickle` in the `model` field. |
| T6 | Unit | `OpenCodeConfig` default `api_key_env` is `OPENCODE_API_KEY`. |
| T7 | Unit | JSON branch of the merged handler returns `Content-Type: application/json` with `query`, `count`, `reranked`, `results` using the stubbed reranker fixture. |
| T8 | Unit | SSE branch returns `Content-Type: text/event-stream` with `metadata`, `answer_delta`, `citations`, `done` in that order. |
| T9 | Config | `D:\avrig\config\server.toml` and `/opt/avrig/config/server.toml` both report `opencode/big-pickle`; `/opt/avrig` keeps `host = 127.0.0.1`. |
| T10 | Integration | Authenticated `POST /api/v1/knowledge/search` with `stream: true` and a live token emits the four events. |
| T11 | Integration | Authenticated `POST /api/v1/knowledge/search` with `stream: false` returns `SearchResponse` JSON. |
| T12 | Integration | Authenticated `GET /api/v1/knowledge/search?q=...&stream=true` emits SSE; the same GET without `stream` returns JSON. |
| T13 | Integration | Unauthenticated request returns `401` on both methods. |
| T14 | Observability | Service log records `provider=opencode` for the request, with no `SubModelNotFound`. |
| T15 | Frontend | Built bundle references `/api/v1/knowledge/search` and contains no `/api/v1/documents/search` string. |
| T16 | Regression | `scripts/test_ingest.sh` completes against the new path with `200` on each search. |

## Definition of Done

The plan closes only when all of the following hold on the deployed system:

```text
[ ] grep -R "documents/search" avrig-api/src avrig-api/scripts avrig-ai/apps/web/src avrig-ai/packages/api-client/src returns nothing
[ ] grep -R "knowledge/search/stream" across the same trees returns nothing
[ ] POST /api/v1/knowledge/search            -> 200 application/json, SearchResponse with query, count, reranked, results
[ ] POST /api/v1/knowledge/search stream:true -> 200 text/event-stream with metadata, answer_delta, citations, done
[ ] GET  /api/v1/knowledge/search?q=...       -> 200 application/json
[ ] GET  /api/v1/knowledge/search?q=...&stream=true -> 200 text/event-stream
[ ] all five removed paths                    -> 410 with a JSON error naming /api/v1/knowledge/search
[ ] unauthenticated request                   -> 401 on both methods
[ ] /opt/avrig/config/server.toml             -> answer_model = "opencode/big-pickle", host stays 127.0.0.1
[ ] D:\avrig\config\server.toml               -> answer_model = "opencode/big-pickle"
[ ] journalctl -u avrig | grep provider=opencode shows the request, no SubModelNotFound
[ ] browser Knowledge Chat answers with citations from the opencode provider
[ ] version bumped per the open 0.3.0 release plan and tag pushed to all four remotes
```

## Review Findings

To be populated by `analyst` after verification, recording goal achievement against the seven objectives.

## Risks and Rollback

| Risk | Mitigation |
| :--- | :--- |
| A stale caller hits a removed route and receives SPA HTML with `200` | Explicit `410 Gone` tombstones with a JSON hint, asserted by T3. |
| Removed routes break an external consumer | This is a deliberate break, released as `minor` on a pre-1.0 line; the tombstone message tells the caller exactly where to go. Roll back by restoring the previous binary and config backups. |
| Content negotiation bug (for example `stream: false` still streaming) | `Option<bool>` semantics plus the T4 truth table. |
| OpenCode catalogue rejects `big-pickle` | Verified present before planning; if it disappears the request fails with `SubModelNotFound` and SSE degrades to the existing fallback message. Roll back by restoring the backed-up `server.toml`. |
| `OPENCODE_API_KEY` absent on a node | Windows user and machine scopes verified present; `/etc/systemd/system/avrig.service` sets it for WSL. |
| Deploy widens `/opt/avrig` exposure | Patch only `answer_model`; never copy the repo `config.toml` or `host = "0.0.0.0"`. |
| Version drift across repos | Release script synchronizes `avrig-ai/Cargo.toml`, `avrig-ai/apps/web/package.json`, and `avrig-api/Cargo.toml` before tagging. |
