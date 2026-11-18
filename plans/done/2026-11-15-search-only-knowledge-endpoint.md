---
title: "Search-Only Knowledge Endpoint with Reranking"
status: done
created: 2026-11-15
completed: 2026-11-15
---

# Search-Only Knowledge Endpoint with Reranking

## Objective

Implement a search-only knowledge endpoint in `avrig-api`. It retrieves and ranks knowledge passages, then returns them with provenance. It does not classify intent, generate a chat response, or invoke agents. A separate chat-completion endpoint may consume these results.

## Endpoint contract

- Extend the existing `POST /api/v1/documents/search` endpoint rather than add a duplicate, unless route review identifies a compatibility reason.
- Accept a search query, result limit, and optional `threshold` representing the minimum reranker score.
- Apply `threshold` after reranking, retaining results where `score >= threshold`. If omitted, do not filter by score.
- Confirm the reranker score scale before defining threshold bounds or a default.
- Return ranked passages with document provenance and scores.
- Use the configured reranker service route `/reranker`, with its base URL supplied by runtime configuration.

## Implementation steps

1. Review the current search handler, authentication and scope requirements, vector query, result schema, and existing project plans. Preserve unrelated working-tree changes. **Assignee: be**
2. Finalize request validation for query, result limit, and optional threshold. Confirm the reranker score contract before restricting threshold values. **Assignee: be**
3. Retrieve vector-search candidates and pass the query plus passages to the configured `/reranker` service. Return the highest-ranked results with their document provenance. Follow the KM retrieval baseline of reranking an initial candidate set to a smaller result set where supported by the current implementation. **Assignee: be**
4. Apply the optional minimum reranker-score threshold after ranking. When threshold is omitted, retain the normal top-ranked results without score filtering. **Assignee: be**
5. Handle reranker errors safely and fall back to vector ranking when the reranker is unavailable. Do not expose internal error details. **Assignee: be**
6. Preserve document read authorization. Keep this endpoint search-only: no JEV intent classification, answer generation, or agent invocation. **Assignee: be**
7. Add offline tests for request validation, threshold filtering, ranking, provenance, authorization failures, and reranker fallback. Run formatter, tests, and build checks. **Assignee: be**
8. Verify runtime connectivity to the Windows-hosted reranker and configure the service base URL. Do not restart or deploy without approval. **Assignee: Infra**

## Out of scope

- Chat-completion response generation.
- Intent classification or execution of search results.
- Database schema changes.
- Production deployment or service restart without approval.

## References

- Project Knowledge Management baseline: `02-projects/avrig-ai/design/Knowledge-Management.md`
- Existing document/vector schema plan: `plans/done/2026-11-14-edm-document-vector-and-reference-entities.md`
