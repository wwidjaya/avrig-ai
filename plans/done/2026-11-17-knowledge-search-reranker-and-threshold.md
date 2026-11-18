---
title: "Plan: Wire Knowledge Search to the Reranker and Add a Default Relevance Threshold"
status: completed
created: 2026-11-17
author: avrig-ai
tags:
  - plan
  - backend
  - configuration
  - knowledge-assistant
---

# Plan: Wire Knowledge Search to the Reranker and Add a Default Relevance Threshold

## Objective

Make knowledge search return only passages that are actually relevant to the query. Two defects showed up in the live test of `what is the purpose of life` on the WSL `avrig-api` runtime:

1. `[reranker] base_url` is unset, so retrieval returns raw vector order. The runtime logs `no reranker base_url configured; document search returns vector order only`.
2. Because `threshold` is only applied when reranking happened, an irrelevant `sample.csv` chunk (p95 latency table) is returned and cited for every query, including nonsense queries, and `count` is never below the row count of the table.

Both must be fixed together: reranking without a threshold still returns weak matches, and a threshold without reranking is inert.

## Measured Evidence

Reranker scores produced by the Windows reranker service (`POST http://172.26.0.1:8000/reranker`, model `bge-reranker-v2-m3`, raw cross-encoder logits) for the two indexed chunks:

| Query | `meaning-of-life.md` | `sample.csv` |
|---|---|---|
| what is the purpose of life | **+1.47** | -11.04 |
| what is the capital of France | -10.85 | -10.98 |
| what is the airspeed velocity of an unladen swallow | -8.17 | -8.05 |

A default threshold of `0.0` logits (sigmoid `0.5`) cleanly separates the relevant passage from every irrelevant one, and matches the documented scale in the vault: raw logits are unbounded and `0.0` corresponds to probability `0.5`. Because the whole observed spread sits above roughly `-11.5`, a threshold of `-11.5` is the widening check that keeps both chunks, while `-5.0` keeps nothing extra.

## Design

### Configuration surface

- `ServerConfig` (in `avrig-api/src/main.rs`, under `[server]` in `server.toml`) gains `search_threshold: Option<f32>` with a neutral code default of `None`. The behavioural value (`0.0`) lives in configuration: `avrig-api/config/server.toml` (source baseline) and `/opt/avrig/config/server.toml` (deployment).
- Why the neutral default: TOML has no `null`, so a code default of `Some(0.0)` would leave no clean way to switch the filter off except a magic negative sentinel, and it would silently change behaviour for every existing config that predates the key. `None` in code keeps the knob explicit, reversible by removing the key, and consistent with `RerankerConfig::base_url`, where absence already means "feature off, deployment decides".
- The threshold is a search-behaviour default, not reranker infrastructure, so it belongs under `[server]` next to `answer_model` rather than in `RerankerConfig`: the standalone reranker role never reads it, and search stays configurable on a node that constructs no reranker client. Do not duplicate the knob in both sections (single source of truth).
- The field doc comment must state the unit and the coupling: the value is compared against raw cross-encoder logits from `[reranker] model`, calibrated on `bge-reranker-v2-m3` where `0.0` equals sigmoid `0.5`; the scale is unbounded, values are never clamped, and changing the reranker model requires re-validating the threshold.
- Precision over recall is deliberate: the reranker docs note that even the best candidate of a weak result set can score negative, so a corpus-wide weak match now returns nothing instead of citing an unrelated passage. The trade-off is reversible through configuration with no code change.
- Request-level `threshold` in `SearchRequest` and `SearchQueryParams` keeps precedence: an explicit client value always wins.
- A configured non-finite value is rejected during `load_config`, after the merged `Config` is deserialized, with an error naming `server.search_threshold` and the offending value. Startup fails and the value is never clamped, because `NaN` would make every comparison false and silently drop the entire result set.
- `[reranker] base_url` is deployment topology, so it is configured in `reranker.toml` only, never hardcoded.

### Behaviour

- Effective threshold = request threshold, else configured `search_threshold`, else `None`. Resolve it once per request in the two search pipelines, `execute_search` and `execute_search_stream`, which are the only places that call `rank_search_hits`. Every route funnels through them: `GET/POST /v1/documents/search`, `GET/POST /v1/search`, `GET/POST /api/v1/documents/search`, `POST /v1/documents/search/stream`, and `POST /api/v1/documents/search/stream`.
- Existing semantics stay intact: the threshold only filters when reranking produced scores, because vector similarity and reranker logits are different scales. A reranker timeout or error therefore drops the filter as well; the threshold is not a fallback cutoff for vector order.
- SSE event names and payload shapes do not change. `count` and the `citations` payload simply reflect the filtered result set.

## Implementation Phases

### Phase 1: Backend configuration and threshold plumbing

**Assignee: be**

1. Add `search_threshold: Option<f32>` with `#[serde(default)]` (absence yields `None`) to `ServerConfig`. Add the same field to `AppState` and to its production construction site (`main.rs:807`), then update the `search_test_state` helper and every other `AppState` literal in the test module (10 sites). There are no `ServerConfig { .. }` literals in tests, so none need editing.
2. Reject a non-finite configured value in `load_config`, after the merged `Config` is deserialized: return an error naming `server.search_threshold` and the value (`bail!` or `context`, no panic, no clamp). Placing it there covers every role, including nodes that never serve search.
3. Resolve `let threshold = search.threshold.or(state.search_threshold);` and pass it to `rank_search_hits` in `execute_search` (`main.rs:2287`) and `execute_search_stream` (`main.rs:2451`). Do not add per-route plumbing: `search_documents`, `search_documents_get`, and `search_documents_stream` are thin wrappers and inherit the behaviour. Confirm with a grep that these are the only two production call sites.
4. Keep `SearchRequest::validate` and `SearchQueryParams` behaviour unchanged, including the `NonFiniteThreshold` request rule.
5. Log the effective default at startup (value, or explicitly "disabled") so the deployed behaviour is verifiable from the journal without reading the config file.
6. Set `search_threshold = 0.0` under `[server]` in `avrig-api/config/server.toml`, with a comment covering the logit unit, the `bge-reranker-v2-m3` calibration, and that removing the key disables filtering.

### Phase 2: Tests

**Assignee: be**

1. Config parsing: empty TOML yields `None`; `search_threshold = 0.0` yields `Some(0.0)`; a negative finite value parses unchanged.
2. Startup validation through `load_config` on a temp directory (pattern: `loads_and_merges_config_directory`): `search_threshold = nan`, `inf`, and `-inf` each fail with an error naming `server.search_threshold`.
3. Handler-level override: state with `search_threshold: Some(0.0)` and a stub `/reranker` (pattern: `spawn_reranker_stub`) returning one positive and one negative score. `POST /v1/documents/search` returns `count: 1` and `reranked: true`; the same request with `threshold: Some(-5.0)` returns `count: 2`; with `threshold: Some(5.0)` returns `count: 0`.
4. GET parity: `search_documents_get` with the same state and stub returns the same counts, proving the query-parameter path inherits the configured threshold instead of bypassing it.
5. Fallback: configured threshold `Some(0.0)` plus a stub returning `503`. Both entry points keep vector order, report `reranked: false`, leave `rerank_score` null, and apply no filtering. This is the handler-level counterpart to the existing `rank_search_hits` unit tests.
6. Stream contract: when every candidate scores below the threshold, the `metadata` event reports `count: 0` and `reranked: true`, the answer delta equals `No relevant documents found in knowledge base.`, and `citations.results` is empty. With mixed scores, `citations.results` length equals `count`.
7. Update the `AppState` test literals for the new field.
8. Gates: `cargo fmt --check`, `cargo clippy --all-targets` with no new warnings, and `cargo test -p avrig`. Leave the release build to the deploy phase so each target is built once and never concurrently.

**Test seam decision (2026-11-17, Plan Agent).** Items 3 to 6 are only reachable if candidate retrieval can be substituted, and it cannot today: `AppState.db` is a concrete `db::DbRepository` whose `search_vectors` opens a Postgres connection inside the call. Approved: add exactly one seam, a one-method `VectorIndex` trait in `src/db.rs` with a dyn-compatible `Pin<Box<dyn Future<Output = Result<Vec<SearchResult>>> + Send + 'a>>` method, implemented for `DbRepository`, and held on `AppState` as `Arc<dyn VectorIndex>` wired to the same repository in production. `db` stays concrete for writes and nothing else moves. Keep the trait next to the repository rather than in `main.rs`, document that it exists so the search pipelines can be exercised without a live database, and reuse the production implementation so behaviour cannot diverge. Two supporting constraints: no `#[ignore]` tests, since a gate that never runs is not a gate; and no second seam, because the `503` fallback is produced by pointing the existing concrete gateway client at an unreachable address. Handler tests also need a local embeddings stub, since the query is embedded before retrieval.

### Phase 3: Runtime configuration

**Assignee: Infra**

1. Reconcile with the committed baseline before inventing an address. `avrig-api/config/reranker.toml` already sets `base_url = "https://api.avrig.ai"`, and `Infrastructure.md` documents that nginx exposes an exact `POST /reranker` for loopback callers and proxies it to the Windows reranker. Deploy that file to `/opt/avrig/config/reranker.toml`, unless the pre-flight probe shows the proxy path is broken.
2. Resolve the documented port discrepancy before writing any URL. The committed config sets `[reranker] port = 8000` and `[gateway] port = 8000`, so the Windows node runs the unified daemon on 8000, while `Infrastructure.md` still documents the reranker on 8001 with nginx proxying to `172.26.0.1:8001`. Confirm the real listener and firewall rule, then correct whichever side is stale. If the direct address is used instead of the proxy, record why in the file; a WSL-only `172.26.0.1` literal is not a valid default for other hosts, so keep the committed baseline generic.

   **Resolved 2026-11-17 (Plan Agent).** The baseline wins and no new URL is invented. `Get-NetTCPConnection -State Listen` on the Windows host shows exactly one listener in the 8000 to 8010 range: `0.0.0.0:8000`, owned by the unified `avrig` daemon. Nothing listens on 8001, so the `Infrastructure.md` port 8001 reference is the stale side. `/etc/nginx/sites-enabled/api.avrig.ai.conf` on WSL defines `location = /reranker` with `allow 127.0.0.1; deny all;` and `proxy_pass http://172.26.0.1:8000/reranker`. `api.avrig.ai` resolves to `127.0.0.1` inside the distribution, and a probe of `https://api.avrig.ai/reranker` returned HTTP 200 with scores `1.35` (relevant) and `-10.97` (irrelevant) for the meaning-of-life query. Deploy the committed `avrig-api/config/reranker.toml` unchanged, and correct the 8001 reference in `Infrastructure.md` as part of the deploy note.
3. Check for conflicting sections first: `load_config` merges every `*.toml` in the directory in filename order and deep-merges them, so a `[reranker]` or `[server]` key in another file is silently overridden. Run `grep -rn "\[reranker\]\|\[server\]" /opt/avrig/config` before adding files.
4. Add `search_threshold = 0.0` under `[server]` in `/opt/avrig/config/server.toml`, alongside the already-applied `answer_model = "agy/gemini-3.8-flash-low"`, with the same explanatory comment as the repo baseline.
5. Confirm the effective reranker model on the Windows node is `bge-reranker-v2-m3`: the `0.0` calibration is model specific.
6. Keep the newly created `answer_model` switch backup (`server.toml.bak-*-switch-agy`) in place.

### Phase 4: Build and deploy

**Assignee: Infra**

1. Back up the current WSL binary `/opt/avrig/avrig` and the live config files with timestamped names.
2. Build the Linux binary inside WSL as user `avrig` using the existing toolchain at `/home/avrig/.cargo` (cargo 1.99.1, `x86_64-unknown-linux-gnu`), from the shared source tree. Never build the Windows and WSL targets concurrently.
3. Deploy to `/opt/avrig/avrig` with owner `avrig:avrig`, mode `0755`; install the config files with owner `avrig:avrig` and mode `0644`; restart `avrig.service` and confirm the unit is `active`.
4. Do not rebuild the Windows binary. The new field is read only by the server role, and a binary built from the previous source ignores the unknown key. Record that reasoning in the deployment note.

### Phase 5: Verification

**Assignee: Infra**

1. Pre-flight: from WSL, prove the reranker route works before touching the service, for example a probe request to the configured `/reranker` endpoint plus a check that the Windows reranker task is running. A blocked port would otherwise look like a threshold bug.
2. Obtain the OIDC bearer token the client uses. Every search route runs the OIDC validator, so an unauthenticated call returns `401` and proves nothing.
3. Confirm the startup log contains the reranker client initialisation line with the configured endpoint, no longer contains `no reranker base_url configured`, and shows the effective `search_threshold`.
4. `POST /v1/documents/search/stream` for `what is the purpose of life`: expect `"reranked": true`, `count: 1`, a grounded answer citing `meaning-of-life.md` only.
5. Same endpoint for `what is the capital of France` and `what is the airspeed velocity of an unladen swallow`: expect `count: 0`, `"reranked": true`, the exact `No relevant documents found in knowledge base.` answer delta, and an empty `citations.results` array.
6. `POST /v1/documents/search`, `GET /v1/documents/search`, `POST /v1/search`, and `GET /v1/search` for the same three queries must agree with the SSE counts.
7. Explicit request threshold still overrides. With the measured scores, `{"threshold": -5.0}` changes nothing (one result for the purpose query, zero for the other two), so use `{"threshold": -11.5}` as the widening check: it returns `count: 2` for all three queries.

## Verification Criteria

- [ ] Search results are rerank-ordered on the WSL runtime.
- [ ] Irrelevant passages are dropped by default, so `count` reflects genuine relevance.
- [ ] Unsupported questions return the no-results path with no citations, and the event still reports `reranked: true`.
- [ ] The threshold is explicit in configuration, not hidden in a code default, and removing the key disables filtering.
- [ ] Request-level `threshold` still overrides the configured default.
- [ ] Non-finite configured threshold is rejected at startup with an error naming `server.search_threshold`.
- [ ] Existing SSE contract and JSON search contract unchanged.
- [ ] Renderer endpoint, port, firewall rule, and model configuration agree across the repo baseline, the vault infrastructure note, and the live WSL and Windows runtimes.
- [ ] `cargo fmt --check`, `cargo clippy --all-targets`, and `cargo test -p avrig` are clean, and both runtimes are healthy after deploy.

## Rollback

- Config: `systemctl stop avrig`, restore the timestamped `server.toml`, remove `reranker.toml` if it was added, then `systemctl start avrig`. Removing only the `search_threshold` key restores the previous unfiltered behaviour with no binary rollback.
- Binary: `systemctl stop avrig && cp -a <backup> /opt/avrig/avrig && chown avrig:avrig /opt/avrig/avrig && chmod 755 /opt/avrig/avrig && systemctl start avrig`.

## Plan Audit

### Analyst Review

Verdict: ready for execution after the corrections folded in above. The design is sound: `ServerConfig` is the right home (search behaviour, single consumer, available without a reranker client), `0.0` is a defensible calibration for `bge-reranker-v2-m3`, and failing startup on a non-finite value matches the existing request-level `NonFiniteThreshold` rule and the fail-fast principle. Four defects were corrected:

1. The plan claimed three search entry points. In fact `rank_search_hits` has exactly two production call sites (`execute_search` at `main.rs:2287`, `execute_search_stream` at `main.rs:2451`); the GET path and both POST paths are thin wrappers. Applying the threshold per route would have risked double resolution and a missed path.
2. A code default of `Some(0.0)` is not disableable in TOML, which has no `null`, and would silently change behaviour for existing configs. The default is now `None` in code with `0.0` set explicitly in the source and deployed `server.toml`. The unusable "`null` disables the default" test is replaced with the real case.
3. The widening check `{"threshold": -5.0}` is arithmetically wrong against the measured scores: both passages score below `-5.0` for the France and swallow queries, and only one is above `-5.0` for the purpose query. Replaced with `-11.5`, which is expected to return two results for all three queries.
4. Runtime configuration assumed a bare `http://172.26.0.1:8000`, contradicting both the committed `base_url = "https://api.avrig.ai"` baseline and the vault note documenting nginx proxy plus port 8001. The phase now reconciles the baseline, the port discrepancy, and the deep-merge behaviour of the config directory before writing files.

Tests were also strengthened: GET parity, handler-level fallback semantics, and the zero-result stream contract were missing, and the claim about "existing `ServerConfig` test literals" was wrong (the literals that need editing are the `AppState` ones).

## Completion

Deployed to the WSL runtime only on 2026-11-17.

- `/opt/avrig/avrig` SHA-256 `ca6beb8a328900230271a3e0ff95fc02c0660265332e61f58bdc98dc322723b9`, 51,885,624 bytes, built in WSL with cargo 1.99.1 in 75 s. Pre-deploy backup `/opt/avrig/avrig.bak-20261117-162252-threshold`.
- `/opt/avrig/config/reranker.toml` added, byte-identical to the committed baseline (`base_url = "https://api.avrig.ai"`). `/opt/avrig/config/server.toml` gained `search_threshold = 0.0` and kept `answer_model = "agy/gemini-3.8-flash-low"`.
- Startup log confirms `reranker client configured` with endpoint `https://api.avrig.ai/reranker` and `search_threshold: 0.0`; no `no reranker base_url configured` line.
- Verified with a real OIDC token across the stream, POST and GET routes: purpose query `count: 1` citing `meaning-of-life.md`; France and swallow queries `count: 0` with the exact no-results delta and empty citations; `{"threshold": -11.5}` widens all three to `count: 2`.
- Tests: 4 lib, 69 bin, 3 integration, all passing. `cargo fmt --check` clean, clippy unchanged at 15 pre-existing warnings.

Two follow-ups were raised and left out of scope:

1. `/opt/avrig/config/oidc.toml` is mode `0644`, so the client secret is world-readable on that host.
2. Every rerank call takes 16.6 to 19.0 s for two short passages against `request_timeout_ms = 60000`, while the query embedding takes 30 ms, making end-to-end search reranker bound. The nginx comment claiming about 160 ms warm does not hold and the cause needs its own investigation.

