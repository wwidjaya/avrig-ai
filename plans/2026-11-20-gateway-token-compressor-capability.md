---
title: "Gateway Token Compressor Capability, Isolated First Stage"
status: awaiting-approval
created: 2026-11-20
owner: plan (authoring), tester (verification), analyst (review), be (implementation)
plan_id:
project_indicator: AVRIG
branch:
candidate_tags: []
release_version:
tags:
  - gateway
  - token-compression
  - avrig-lib
  - staged-delivery
---

# Gateway Token Compressor Capability, Isolated First Stage

## Goals and Objectives

1. Add a standalone, reusable compressor capability under `avrig-lib/crates/avrig-gateway/src/compressor/` with distinct input and output entry points.
2. Keep the first implementation isolated: do not invoke it from gateway request handling, provider adapters, response conversion, or streaming code.
3. Define and measure the transformation contract for the selected initial strategy, `exact-dedupe-v1`. Validate it in this isolated stage with deterministic injected byte and token measurers; make no real-provider savings claim until a compatible tokenizer is selected and verified later.
4. Gate any later integration into the running gateway on review and passing isolated tests. Gateway wiring is a separate follow-up stage and is outside this plan's implementation scope.

## Key Detailed Design

### Program Design

The target crate is `avrig-lib/crates/avrig-gateway`, a Rust 2024 library crate. Its root exports modules through `src/lib.rs`. Existing request and response contracts reside in `src/antigravity/types.rs`; provider processing and usage stream handling reside in `src/client.rs`; Antigravity conversion is in `src/antigravity/converter.rs`. Existing usage fields are provider-reported `prompt_tokens`, `completion_tokens`, and `total_tokens`; the crate has no general tokenizer or compressor today.

#### Compression objectives and terminology

The design distinguishes three different measures:

1. **Byte reduction**: smaller UTF-8 or serialized payload. This can reduce network/storage use, but does not establish fewer model tokens.
2. **Input-token reduction**: fewer tokens in the prompt sent to an upstream model. This can lower prompt cost and context occupancy only when measured with that provider/model's tokenizer or confirmed by upstream usage.
3. **Downstream-context reduction**: fewer tokens in a model response after it is returned, so a later agent or model call can consume less context. Post-response compression cannot reduce tokens already generated or billed by the provider.

Every result must identify which measure it reports. Do not label byte savings as token savings, and do not report post-response shortening as provider generation savings.

#### Proposed module boundaries

Keep the implementation as a pure library with no network, filesystem, model calls, persistence, or gateway state. The module should have four conceptual pieces:

- `types`: direction (`Input` or `Output`), content units, policy, measurements, and structured errors.
- `input`: input planning and transformation over ordered content units.
- `output`: output planning and transformation over ordered content units.
- `strategy`: the compression strategy interface and strategy metadata. A strategy declares whether it is lossless or semantic/lossy, which content kinds it accepts, and what measurement it can produce.

The compressor must be deterministic for identical content, policy, and strategy. Strategy implementations may be added independently later, but this initial module should ship only strategies with explicit quality and safety contracts. Avoid hidden provider selection, implicit global settings, and mutable cross-request state.

#### Content and preservation model

The initial API should operate on ordered, typed content units rather than raw serialized HTTP bodies. A unit carries a stable id, a kind, text or opaque structured payload, and a protection class. Initial kinds should include plain text, code, structured data, tool call, tool result, and opaque/unknown. Protection classes should distinguish required, preserve-if-possible, and compressible content. `exact-dedupe-v1` additionally requires an explicit duplicate-safe marker and caller-supplied deduplication group. A group names a set of interchangeable context entries within one compression operation, not merely entries with a shared role or source. Group ids must be non-empty; units marked duplicate-safe without a group fail validation. The caller asserts that exact repetition inside that group is redundant.

The compressor must treat unknown and opaque content as protected and pass it through unchanged. It must not reorder units or cross unit boundaries. Structured tool calls and their matching results remain atomic and unchanged unless a future strategy explicitly supports them and has dedicated validation. System and developer instructions are protected by default. User content can be compressed only under an explicit policy. The implementation must retain provenance from each output unit to the source unit(s), so callers can inspect what was removed or rewritten.

#### Input path

The input path accepts a sequence of content units plus an explicit policy and a target budget. It produces a compression report and the candidate sequence. Its internal steps are:

1. Validate policy values, units, content size, and the target measurement capability.
2. Mark protected units and calculate a baseline using the configured measurement provider.
3. Ask the chosen strategy for a deterministic candidate plan. The strategy may not modify protected units.
4. Measure the candidate with the same measurement provider and compare it with the target.
5. Return the candidate and a report containing before/after bytes, before/after tokens when available, savings, strategy id/version, protected-unit counts, modified-unit provenance, and a no-op reason when it cannot safely help.

The compressor does not make a request fit by deleting protected units. If the target cannot be met safely, it returns the best candidate with an explicit `BudgetUnmet` status, or an error if the configured policy requires strict enforcement. The caller chooses whether to reject or send the original request.

#### Output path

The output path accepts complete response content units and a downstream context budget. It must never run on streaming chunks in this stage. It uses the same measurement/report concepts but has a separate policy and strategy entry point, because response content has different preservation requirements. The default policy preserves code blocks, structured payloads, tool calls/results, citations, and explicit constraints; semantic compression of ordinary prose must be opt-in and marked lossy. Its report labels the benefit as `DownstreamContext` and must not expose it as upstream generation or billing savings.

The returned output must remain a content value, not a serialized HTTP/SSE response. This avoids accidental mutation of protocol framing. Later integration must separately define streaming behavior and pass-through fallback.

#### Suggested API shape

Exact Rust names may be refined by the implementer, but keep the contract equivalent to:

```rust
pub struct CompressionRequest<'a> {
    pub units: &'a [ContentUnit],
    pub policy: &'a CompressionPolicy,
    pub budget: Option<MeasurementBudget>,
}

pub trait TokenMeasurer {
    fn metadata(&self) -> MeasurerMetadata;
    fn measure(&self, units: &[ContentUnit]) -> Result<Measurement, CompressionError>;
}

pub trait CompressionStrategy {
    fn metadata(&self) -> StrategyMetadata;
    fn compress(&self, request: &CompressionRequest<'_>, measurer: &dyn TokenMeasurer)
        -> Result<CompressionCandidate, CompressionError>;
}

pub fn compress_input(
    request: &CompressionRequest<'_>,
    strategy: &dyn CompressionStrategy,
    measurer: &dyn TokenMeasurer,
) -> Result<CompressionResult, CompressionError>;
pub fn compress_output(...); // same dependencies, output-specific policy validation
```

`MeasurementBudget` contains a maximum and an explicit unit, either bytes or model tokens. `Measurement` identifies the unit and measurer. Token measurements include tokenizer/encoding identity and version, and provider/model when known. A byte measurer cannot satisfy a token budget. Strategy selection is explicit; the orchestration layer measures original and candidate with the same measurer and rejects mismatched measurement kinds.

The implementation should avoid making async work necessary for these interfaces. If a future strategy calls a remote model, it belongs behind a separate async adapter and is not part of the first isolated core.

#### Measurement and algorithm decision

The crate has no tokenizer dependency, and different providers tokenize the same text differently. Keep token measurement injectable. A byte-only measurer may be used for transport metrics but must identify its unit as bytes and must not satisfy a token budget. A token budget operation requires a provider/model-specific `TokenMeasurer`; if none is supplied, token-budget compression must fail clearly or return an explicitly unverified result according to policy.

The first strategy decision is a pre-implementation gate. Before approval, `be` must propose a concrete strategy with algorithm/version, lossless or lossy contract, supported content kinds, target tokenizer or explicit byte-only scope, quality measure and threshold, fallback behavior, and dependency rationale. The analyst and tester then update the plan's review and strategy-specific test matrix. Only after those updates should the plan return to `awaiting-approval`. Approval authorizes only the named strategy and bounded isolated implementation. A change of strategy or lossy handling of protected content requires renewed review and approval. Do not silently add a remote compression call, tokenizer, or model dependency.

#### Initial strategy proposal: `exact-dedupe-v1`

The backend proposal recommends deterministic exact duplicate-unit elimination. It removes a later unit only when it is plain text, marked `Compressible`, explicitly marked duplicate-safe by the caller, and byte-identical to an earlier unit in the same deduplication group. It retains the first occurrence and preserves the order of remaining units. It does not summarize, rewrite, split, merge, or infer that similar text is redundant. Requiring caller opt-in matters because repeated user text can be meaningful.

This is a lossy sequence transformation because a duplicate unit is removed. The original input remains caller-owned and unmodified. Provenance records the removed unit id and retained source unit id without copying text. Protected, unknown, code, structured, tool-call, and tool-result units pass through byte-identically. The strategy claims no paraphrase or summarization quality.

Acceptance threshold: accept a candidate only if the selected configured measurement strictly decreases and all protection rules hold. In this isolated stage, token and byte behavior are validated only with injected deterministic fake measurers. With a token measurer, token count must decrease. Byte measurement applies only to byte budgets and transport reporting. Otherwise return a no-op. The technology baseline identifies `tiktoken-rs` for context token budgeting, but provider tokenization varies. Keep the measurer injectable, report encoding/provider/model identity, and do not add a tokenizer dependency in this isolated stage without a demonstrated supported mapping. Real provider savings remain unverified until a compatible tokenizer is selected and later integration is measured.

#### Error and fallback behavior

Errors should distinguish invalid policy, missing or incompatible measurer, malformed structured content when parsing is explicitly requested, input-size and unit-count limits, and strategy failure. Unknown units are preserved opaquely by default and are not errors. A strategy that cannot handle a known kind must leave it unchanged; rejection is allowed only in strict policy mode and must identify the unit id.

Best-effort mode accepts a strategy candidate only if it preserves every protected unit, stays within resource limits, and improves the selected measurement. Otherwise it returns original units with a no-op or budget-unmet result. Strict mode returns `BudgetUnmet` if the target remains unmet and never silently substitutes a partial candidate. Strategy or measurement failures remain explicit errors. Candidate selection is deterministic: validate invariants, compare using the same measurement provider, accept only a strict improvement that preserves protected-content rules, otherwise keep the original.

#### Resource bounds and privacy

The API must accept explicit maximum input bytes and unit counts. Initial defaults are 1 MiB total UTF-8 payload and 10,000 units, configurable by the caller. Test exactly-at-limit and limit-plus-one inputs. The over-limit fixture must fail before the strategy is invoked, proving limits are checked before intermediate copies. The API must not log or retain prompt contents. Measurement reports contain counts, strategy identifiers, and unit ids only, not text.

Every output unit carries source unit ids. The report represents unchanged, rewritten, and removed units with a reason code and strategy id, without copying source text. Lossless strategies must support byte-exact restoration or explicitly declare restoration unavailable; lossy strategies must provide provenance for every change.

#### Later gateway integration contract

The follow-up integration plan should wrap the pure module at the gateway boundary. For input, it will decide which providers/models have compatible token measurers, apply compression before request conversion, and preserve the original request for fallback/audit according to configured policy. For output, it will distinguish returned content from provider usage and will not rewrite provider-reported usage fields. Streaming remains a separate design: no chunk-by-chunk semantic compression is allowed without explicit buffering, latency, finish-reason, tool-call, and SSE framing rules. Integration should be opt-in per provider/model at first, observable through metrics that exclude content, and disabled by default until verified.

No Axum routes, HTTP models, gateway config, or EDM changes are required. There are no database entities, migrations, foreign keys, or persistence needs for this isolated library capability.

### Target Program Files (Mandatory)

Repository: `D:\Cloud\OneDrive\AI\Agentic\avrig-lib`

- Create `crates/avrig-gateway/src/compressor/mod.rs` for module exports and shared orchestration.
- Create `crates/avrig-gateway/src/compressor/types.rs` for content units, policies, measurement/report types, strategy contracts, and errors.
- Create `crates/avrig-gateway/src/compressor/input.rs` for input-side planning and transformation.
- Create `crates/avrig-gateway/src/compressor/output.rs` for output-side planning and transformation.
- Create `crates/avrig-gateway/src/compressor/strategy.rs` for strategy interface and strategy metadata.
- Edit `crates/avrig-gateway/src/lib.rs` to export `pub mod compressor;`.
- Do not edit `crates/avrig-gateway/src/client.rs`, `src/antigravity/converter.rs`, `src/antigravity/types.rs`, application code in `avrig-api`, or dependency manifests unless the approved design decision justifies a dependency and the scope is amended.

These exact paths are based on the crate structure confirmed in `avrig-lib`; its `src/lib.rs` currently exports `antigravity`, `client`, `resolver`, `siwc`, and `types`, and has no `compressor` directory. The shared `graphify-out` graph in `avrig-ai` does not index the separate `avrig-lib` checkout, so crate-specific target paths were confirmed by direct inspection after graphify established the workspace's gateway references.

### EDM Design

Not applicable. The compressor is an in-memory library capability with no persistence, schema, table, or migration requirements.

### Explicit Scope Boundary and Follow-up Gate

This plan ends when the standalone module has an agreed contract, implementation, focused unit coverage, crate-level verification, and review. It does not change production behavior. A separate integration plan may later connect input compression before outbound provider requests and output compression after response conversion, including non-streaming and streaming behavior, only after the isolated results are reviewed and accepted.

## Parallel Execution Plan

| Workstream | Assignee | Execution | Dependency / output |
|---|---|---|---|
| Crate discovery and target mapping | explore, completed | Sequential | Confirmed crate location, existing types, usage surfaces, and absence of compressor/tokenizer. |
| Plan standards audit | analyst, completed 2026-11-20 | Immediately after draft, before approval | Verdict: revise before approval. Findings are recorded below and the plan workflow metadata has been corrected. |
| Test specification | tester, completed 2026-11-20 | Parallel with analyst review | Isolated validation matrix and execution detail attached below. |
| Initial strategy proposal | be, completed 2026-11-20 | Sequential, before final approval presentation | Proposed `exact-dedupe-v1`, injected fake measurers for isolated verification, deferred provider tokenizer mapping, explicit eligibility, strict-improvement threshold, and no new dependency. |
| Strategy-specific review and test update | tester and analyst, passed 2026-11-20 | Parallel, after proposal | Tester passed the concrete matrix; analyst passed the design audit after the API/test contract was reconciled. |
| Findings confirmation and approval | Architect | Sequential hard gate | Present findings, matrix, strategy proposal, and remaining clarifications. Then set `awaiting-approval`; allocate no work-item number until approval. |
| Standalone module implementation | be | Sequential | Implement the typed, isolated compressor API and tests only in the listed paths. |
| Crate verification | tester | Sequential | Run focused module tests and `cargo test -p avrig-gateway` in `avrig-lib`; report results. |
| Review gate | analyst | Sequential | Check scope isolation, claimed savings evidence, and test outcomes. |
| Gateway integration | Separate future plan | Deferred | Begins only after explicit acceptance of isolated capability and test results. |

No parallel code implementation is recommended because the algorithm and API contract must be chosen before input and output behavior can be made consistent.

## Test Specification and Validation Matrix

Authored by tester before implementation. Tests apply only to the standalone module; do not add gateway request/response wiring in this stage. The proposed `exact-dedupe-v1` has an exact eligibility and strict-measurement-decrease acceptance threshold; reviewer sign-off is required before implementation.

| Area | Validation | Expected result |
|---|---|---|
| Input transformation | Empty text, multilingual Unicode, nested JSON, code, tool-call-like content, repeated text, high-entropy text, and a fixed 1 MiB fixture represented as typed units. | Remove only later byte-identical plain-text units sharing a deduplication group and duplicate-safe marker; protected units remain byte-identical and in order. |
| Output transformation | Same fixtures through output operation, including citations and explicit constraints. | Apply the same eligibility rules; citations, constraints, protected units, and remaining order stay unchanged. |
| Size accounting | Repeated text and high-entropy fixtures; compare exact input/output byte counts. | Reported values equal measured byte counts; no savings are claimed if output grows. Token behavior uses deterministic fake token and byte measurers; no real-provider claim is made in this isolated stage. |
| Round trip | Compress and restore content where the selected method promises losslessness. | Lossless mode restores byte-for-byte. Lossy mode must specify measurable preservation thresholds after algorithm selection before tests are finalized. |
| Limits and malformed data | Test 1 MiB maximum, maximum plus one byte, 10,000 units, unit maximum plus one, and invalid configuration. Test malformed encoding only if encoded payloads are accepted. | Limit violations fail before strategy invocation; explicit errors, no panic or silent corruption. |
| Configuration | Defaults, valid settings, and invalid settings. | Defaults are documented; invalid values follow the API contract and are rejected where unsafe. |
| Determinism and isolation | Repeat operations and invoke separate configurations. | Stable results with no state leaking across calls. |
| Content safety | Prompt-like text, delimiters, metadata-like content, code, structured content, paired tool calls/results, unknown units, and explicit constraints. | Protected/unknown units pass through byte-identically; no reordering, cross-unit merging, or invented claims. |
| Token claims | Use deterministic fake token measurers only in this isolated stage. | Compressor behavior is reproducible under the fake; no real-provider token reduction is claimed. Byte/character reduction alone is never presented as token reduction. |
| Measurer contract | Use fake token and byte measurers; use byte measurement with a token budget; verify before/after counts and measurer identity. | Incompatible measurement fails clearly; measurements identify unit and measurer. The public API requires an explicit measurer, so absence is prevented by the call contract. |
| Fallback and budget | Test best-effort and strict modes where protected units prevent meeting the target. Test worse candidates and strategy errors. | Best-effort preserves original on no improvement with no-op/budget-unmet status; strict returns `BudgetUnmet`; strategy failures stay errors. |
| Provenance | Exercise unchanged and removed compressible units. | Each removed unit id maps to the retained duplicate id; report contains ids and reason only, with no source text. Rewrites are outside `exact-dedupe-v1`. |
| Exact deduplication eligibility | Same bytes in same group, same bytes across different groups, near-duplicate text, missing duplicate-safe marker, and protected duplicate units. | Only exact eligible duplicates are removed; all other cases are no-ops. |
| Non-improving candidate | Same-group eligible duplicates with fake measurer reporting equal or greater after-count. | Return original units with no-op provenance/status; strict mode reports `BudgetUnmet` when a requested budget remains unmet. |
| Output benefit classification | Compress repeated eligible output units and inspect report. | Savings are labeled downstream-context only, never generation-token or provider-billing savings. |
| Integration boundary | Inspect public module call sites and run crate tests. | No production gateway flow invokes the compressor in this phase. |

Validation commands and working directory: from `D:\Cloud\OneDrive\AI\Agentic\avrig-lib`, run `cargo test -p avrig-gateway compressor::` for focused tests, then `cargo test -p avrig-gateway`. Capture byte measurements and fake-measurer token measurements. For `exact-dedupe-v1`, require identical eligible duplicate units to be removed only when the selected measurement strictly decreases; require protected-unit byte identity and order. Cover incompatible measurers, strict/best-effort budget-unmet behavior, provenance, exact eligibility, and pre-allocation size limits. No deployment or live-provider checks are in scope.

## Review Findings

Audited by analyst on 2026-11-20 after the concrete `exact-dedupe-v1` strategy and API/test alignment. Verdict: pass, with the required plan update completed. The plan separates bytes, input-token savings, and downstream-context savings; uses explicit strategy and measurer dependencies; defines eligibility, provenance, deterministic no-op behavior, bounded resource checks, and fake-measurer-only validation. The analyst confirmed the `MeasurementBudget` unit matches the API and tests, and that the strategy contract is bounded and coherent.

Tester audit on 2026-11-20: pass. The matrix tests same-group duplicate eligibility, strict measured improvement, equal/greater measurement no-op, strict `BudgetUnmet`, downstream-context reporting, source-id provenance without text retention, measurer compatibility, and resource limits. The `compressor::` filter is valid if unit tests are nested under that module; implementation must adjust the filter if names differ.

The concrete strategy is `exact-dedupe-v1`: remove later, byte-identical plain-text units only when the caller marks them `Compressible`, duplicate-safe, and assigns them to the same non-empty equivalence group. No rewriting or semantic quality claim is made. Tests use deterministic injected fake measurers. Real provider-token savings remain unverified until a provider-compatible tokenizer is selected and validated in the later integration stage. This plan remains isolated and does not authorize gateway wiring.
