---
title: "Plan: Fix API Connection Port and CORS Preflight for Knowledge Search"
status: completed
created: 2026-11-17
author: avrig-ai
tags:
  - plan
  - bugfix
  - cors
  - nginx
  - runtime-config
  - api
  - infra
---

# Plan: Fix API Connection Port and CORS Preflight for Knowledge Search

## 1. Problem Diagnosis

The Web UI reports:
> `Error connecting to knowledge search endpoint: Failed to fetch. Please verify that the API service is reachable and your authentication token is valid.`

Two root causes were identified:
1. **Port Mismatch in Runtime Config (`config.json`)**:
   - `apps/web/public/config.json` and `/var/www/web.avrig.ai/config.json` configure `apiBaseUrl` as `"https://api.avrig.ai:8000"`.
   - Nginx listens on standard HTTPS port **443**. Port 8000 is internal loopback (`127.0.0.1:8000`) inside WSL where `avrig.service` runs, causing the browser's fetch to fail (`ERR_CONNECTION_REFUSED` / timeout).
2. **Missing CORS Preflight (`OPTIONS`) Headers**:
   - Frontend is hosted on origin `https://avrig.ai`, while API is on `https://api.avrig.ai`.
   - The browser automatically issues a CORS preflight `OPTIONS` request before sending `GET /v1/documents/search` with the `Authorization: Bearer <token>` header.
   - Currently, testing `OPTIONS https://api.avrig.ai/v1/documents/search` returns `405 Method Not Allowed` because neither Nginx nor Axum handles preflight requests.

---

## 2. Implementation Phases & Subagent Assignments

### Phase 1: Configure CORS Preflight & Headers in Nginx (`Assignee: Infra`)
1. In `/etc/nginx/sites-available/api.avrig.ai.conf` on WSL distribution `avrig-ai`:
   - Add CORS handling for origins `https://avrig.ai`, `https://web.avrig.ai`, and `http://localhost:3000`.
   - Intercept `$request_method = 'OPTIONS'` and return `204 No Content` with:
     - `Access-Control-Allow-Origin: $http_origin`
     - `Access-Control-Allow-Methods: GET, POST, OPTIONS, HEAD`
     - `Access-Control-Allow-Headers: Authorization, Content-Type, Accept, Origin, X-Requested-With`
     - `Access-Control-Allow-Credentials: true`
   - Apply matching `Access-Control-Allow-Origin` and `Access-Control-Allow-Credentials` headers on responses.
2. Test Nginx configuration (`sudo nginx -t`) and reload (`sudo systemctl reload nginx`).

### Phase 2: Update Web App Runtime Configuration (`Assignee: fe` & `Assignee: Infra`)
1. In `apps/web/public/config.json`:
   - Update `apiBaseUrl` to `"https://api.avrig.ai"`.
   - Update `wsBaseUrl` to `"wss://api.avrig.ai/ws"`.
2. Sync the updated `config.json` to `/var/www/web.avrig.ai/config.json`.
3. Rebuild frontend if needed to update default bundle fallback.

### Phase 3: Verification & Live Testing (`Assignee: Infra`)
1. Test CORS preflight via curl:
   ```bash
   curl -k -i -X OPTIONS https://api.avrig.ai/v1/documents/search \
     -H "Origin: https://avrig.ai" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: authorization"
   ```
   Assert: Returns `HTTP/1.1 204 No Content` with `Access-Control-Allow-Origin: https://avrig.ai`.
2. Test knowledge search query from the browser UI at `https://avrig.ai/#console` under Knowledge Chat.
3. Verify that results/citations render cleanly.

---

## 3. Verification Criteria
- [x] `OPTIONS https://api.avrig.ai/v1/documents/search` returns `HTTP 204 No Content` with proper CORS headers.
- [x] `/var/www/web.avrig.ai/config.json` points to `https://api.avrig.ai` without port 8000.
- [x] Browser fetches from `https://api.avrig.ai/v1/documents/search?q=...` succeed without `Failed to fetch`.
- [x] Knowledge Chat renders search results and citations correctly.
