---
title: "Plan: Standardize and Expose /v1/health and /v1/documents/search Endpoints"
status: done
completed: 2026-11-18
created: 2026-11-17
author: avrig-ai
tags:
  - plan
  - backend
  - axum
  - api
  - healthcheck
  - search
  - knowledge
  - frontend
  - chat
  - infra
---

# Plan: Standardize and Expose /v1/health and /v1/documents/search Endpoints

## 1. Objective

Standardize the central API endpoints under the `/v1/` namespace without the `/api/` prefix to align with OpenAI and avrig design standards:
1. Expose `GET /v1/health` (while maintaining backward compatibility for `GET /api/v1/health` and `GET /health`).
2. Expose `POST /v1/documents/search` and `POST /v1/search` (while maintaining backward compatibility for `POST /api/v1/documents/search`).
3. Connect the Web Command Center (`apps/web`) to query the knowledge search backend endpoint directly in the redesigned console screen / chat interface using `ApiClient`.

---

## 2. Implementation Phases & Subagent Assignments

### Phase 1: Backend Route Expansion & Standardization (`Assignee: be`)
1. **Mount Endpoints in `avrig-api/src/main.rs`**:
   - Healthcheck routes:
     ```rust
     .route("/v1/health", get(|| async { "ok" }))
     .route("/api/v1/health", get(|| async { "ok" }))
     .route("/health", get(|| async { "ok" }))
     ```
   - Search & Document routes (supporting both standard `GET` with query params and `POST` with JSON):
     - Query parameters for `GET`: `?q=...&limit=...&threshold=...` (or `?query=...`)
     ```rust
     .route(
         "/v1/documents/search",
         get(search_documents_get).post(search_documents),
     )
     .route(
         "/v1/search",
         get(search_documents_get).post(search_documents),
     )
     .route(
         "/api/v1/documents/search",
         get(search_documents_get).post(search_documents),
     )
     ```
   - Implement `search_documents_get` handler parsing query parameters `SearchQueryParams { q: Option<String>, query: Option<String>, limit: Option<usize>, threshold: Option<f32> }` into `SearchRequest`.
2. **Update Integration Tests (`avrig-api/tests`)**:
   - Assert `GET /v1/health` returns `200 OK` with payload `"ok"`.
   - Assert `GET /v1/documents/search?q=test` returns `200 OK` with `SearchResponse`.
   - Assert `POST /v1/documents/search` accepts `SearchRequest` JSON and returns `SearchResponse`.
   - Run `cargo test -p avrig-api` and ensure 0 failures.

### Phase 2: Compilation & WSL Service Deployment (`Assignee: be` & `Assignee: Infra`)
1. Compile release binary:
   ```bash
   cargo build --release -p avrig-api
   ```
2. Copy binary to `/opt/avrig/avrig` on WSL distribution `avrig-ai` with executable permissions.
3. Configure and verify systemd service `avrig.service` on WSL `avrig-ai` listening on `127.0.0.1:8000`.
4. Verify via curl:
   ```bash
   curl -k -i https://api.avrig.ai/v1/health
   curl -k -i -X POST https://api.avrig.ai/v1/documents/search -H "Content-Type: application/json" -d '{"query":"test"}'
   ```

### Phase 3: Web Console Chat & Knowledge Query Screen Redesign (`Assignee: fe`)
1. **Connect `ApiClient` to Knowledge Search**:
   - In `apps/web/src/shared/api/client.ts` or helper:
     Expose typed `searchDocuments(query: string, limit?: number)` calling `POST /v1/documents/search` (or `/v1/search`) with the user's bearer token.
2. **Redesign Console Screen / Chat Interface**:
   - In `apps/web/src/modules/knowledge/` (or new chat component):
     - Interactive Chat / Query interface where the user can query the knowledge base.
     - Display user questions and assistant responses with grounded citations / document references retrieved from the `/v1/documents/search` endpoint.
     - Include loading states, error handling, token inspection, and source snippets.
3. **Build & Verify Frontend**:
   - Run `pnpm --filter @avrig/web typecheck`
   - Run `pnpm --filter @avrig/web build`
4. **Deploy Frontend Build to WSL**:
   - Sync `apps/web/dist` to `/var/www/web.avrig.ai/` and verify live.

---

## 3. Verification Criteria
- [ ] `GET https://api.avrig.ai/v1/health` returns `200 OK` `"ok"`.
- [ ] `GET https://api.avrig.ai/v1/documents/search?q=...` returns semantic vector/hybrid results via standard HTTP GET query parameters.
- [ ] `POST https://api.avrig.ai/v1/documents/search` accepts JSON queries for long/complex prompts.
- [ ] Backward compatibility endpoints (`/api/v1/health`, `/api/v1/documents/search`) remain functional.
- [ ] Web console chat screen queries knowledge base backend via `GET /v1/documents/search?q=...` and renders citations.
- [ ] Automated tests pass across both backend and frontend.
