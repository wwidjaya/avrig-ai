---
status: completed
created: 2026-11-18
assignees: [analyst, tester, be, fe, build, Infra, km]
parallel_streams: true
---

# Plan: Normalize Rerank Score to Percentage Across API, Configuration, and UI

## Goals and Objectives
Convert cross-encoder rerank scores from raw unbounded logits (such as `1.47`, `-6.85`) to direct percentage values between `0.0%` and `100.0%` using standard Sigmoid normalization:
$$\text{percentage} = \frac{100.0}{1 + e^{-\text{logit}}}$$

Reflect this percentage representation across:
1. Public API response models (`SearchResult.rerank_score` and `SearchResult.score`).
2. Server configuration (`search_threshold` in `server.toml` expressed as a percentage between `0.0` and `100.0`, where `-7.0` logit maps to `0.091%` or rounded default `0.1%`).
3. Web Command Center UI (`apps/web` Knowledge Assistant view) displaying clean percentage badges for document citations and search hits.

## Key Detailed Design

### Program Design

#### 1. Normalization Function (`avrig-api`)
In `avrig-api/src/reranker.rs` (or `src/main.rs`):
```rust
pub fn logit_to_percentage(logit: f32) -> f32 {
    100.0 / (1.0 + (-logit).exp())
}

pub fn percentage_to_logit(percentage: f32) -> f32 {
    let p = (percentage / 100.0).clamp(1e-7, 1.0 - 1e-7);
    (p / (1.0 - p)).ln()
}
```

- When the reranker client returns raw scores from `bge-reranker-v2-m3`, convert them via `logit_to_percentage`.
- In `rank_search_hits`, apply threshold filtering against the percentage scale:
  - If `search_threshold` is configured as a percentage (e.g. `0.1` for `0.1%`), candidates with `percentage_score < threshold` are filtered out.
- Update `SearchResult` fields:
  - `rerank_score`: `Some(logit_to_percentage(raw_logit))`
  - `score`: Updated to match the normalized percentage score when reranking is active.

#### 2. Configuration (`config/server.toml`)
- Express `search_threshold` under `[server]` as a percentage in `[0.0, 100.0]`:
  ```toml
  [server]
  # Minimum reranker relevance percentage required to return a passage.
  # 0.1 corresponds to ~0.1% (equivalent to raw logit -7.0 on bge-reranker-v2-m3).
  search_threshold = 0.1
  ```
- Deployment configuration `/opt/avrig/config/server.toml` on WSL instance will be updated to match.

#### 3. Frontend UI Display (`apps/web`)
- Inspect citation rendering in `apps/web/src/modules/knowledge/KnowledgeChat.tsx` and related components:
  - Format scores with one decimal point and percentage symbol: `${hit.score.toFixed(1)}%` or `${hit.rerank_score.toFixed(1)}%`.
  - Add color-coded visual indicator badges:
    - High match (`>= 70.0%`): Green/emerald badge
    - Moderate match (`30.0% - 69.9%`): Amber/yellow badge
    - Low/cross-lingual match (`< 30.0%`): Zinc/slate badge

### EDM Design
No database schema changes, table alterations, or migrations required.

## Parallel Execution Plan

| Stream | Assignee | Execution Mode | Scope |
| :--- | :--- | :--- | :--- |
| **Stream A** | `be` | Sequential (Step 1) | Implement `logit_to_percentage` in `avrig-api`, update `rank_search_hits` to filter and return percentage values, update `config/server.toml` threshold to `0.1`, and update unit test assertions in `avrig-api/src/main.rs`. |
| **Stream B** | `fe` | Parallel (with Stream A) | Update `apps/web` Knowledge Assistant chat and citation display to render percentage badges with color thresholds. |
| **Stream C** | `tester` | Parallel (with Stream A/B) | Update test suites to assert that returned rerank scores fall within `[0.0, 100.0]` and author test cases for sigmoid conversions. |
| **Stream D** | `analyst` | Parallel | Audit plan and API contract conformance. |
| **Stream E** | `build` | Gate | Run `cargo check --bin avrig`, `cargo test --bin avrig`, and `pnpm build` in `apps/web`. |
| **Stream F** | `Infra` | Sequential (Post Build) | Recompile binary, deploy updated binary and `server.toml` to WSL instance, deploy web build artifacts, and restart `avrig.service`. |
| **Stream G** | `tester` | Sequential (Post Deploy) | Run live functional verification on `POST /v1/documents/search` and `POST /v1/documents/search/stream` asserting percentage values and UI rendering. |
| **Stream H** | `km` | Sequential (Final) | Author a lesson learned retrospective note in the Obsidian Knowledge Vault documenting score normalization, threshold calibration, and multi-language reranker behaviors. |

## Test Specification and Validation Matrix

### 1. Math and Conversion Unit Tests (`tester` / `be`)
- Exact Sigmoid values:
  - Logit `0.0` &rarr; `50.0%`
  - Logit `-7.0` &rarr; `0.0911%` (passes `0.1%` boundary or rounds accordingly)
  - Logit `1.47085` &rarr; `81.32%`
  - Logit `4.82178` &rarr; `99.20%`
- Invariance: Monotonically increasing order is strictly preserved.

### 2. Search Pipeline & Threshold Unit Tests
- Assert that `SearchResult.rerank_score` and `SearchResult.score` are bounded in `[0.0, 100.0]`.
- Assert that `search_threshold = 0.1` keeps cross-lingual hits scoring `~0.105%` (e.g. logit `-6.85`) while dropping hits scoring `< 0.1%`.

### 3. Frontend Component Tests
- Ensure citation badges render `${score.toFixed(1)}%` cleanly without `NaN` or raw unformatted floats.

### 4. End-to-End Live Functional Tests (`tester`)
- Run `POST /v1/documents/search/stream` with:
  1. `"What is the purpose of life"` &rarr; `count == 1`, citation score `~81.3%`, grounded English answer.
  2. `"apa arti kehidupan"` &rarr; `count == 1`, citation score `~0.1%`, grounded Indonesian answer.

### 5. Knowledge Management Deliverable (`km`)
- Publish a lesson learned note in `D:\Cloud\OneDrive\AI\Personal\vault` covering:
  - Mathematical Sigmoid normalization from cross-encoder logits to direct percentages.
  - Multi-lingual passage retrieval dynamics and logit threshold boundaries (cross-lingual scoring at `0.1%` vs native at `~80%+`).
  - Frontend badge rendering patterns for RAG citation relevance.
  - Testing lesson: expanding tester mandate to functional/E2E testing and passing explicit execution context to avoid redundant discovery loops.

## Review Findings
Audited by `analyst`:
- Sigmoid transformation is mathematically sound, continuous, and preserves relative ranking.
- Expressing scores as percentages bounded in `[0.0, 100.0]` improves human readability and UI presentation without altering the underlying vector or reranking model.
