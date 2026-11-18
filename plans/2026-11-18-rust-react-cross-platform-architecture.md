---
status: planned
created: 2026-11-18
assignees: [analyst, tester, edm, be, fe, build, Infra, km]
parallel_streams: true
---

# Cross-Platform Rust and React Architecture Implementation

## Goals and Objectives

Transform `avrig-ai` into a unified cross-platform architecture matching the technical recommendations from `rust-react-cross-platform-architecture.md`:
- Produce a single production executable (`avrig.exe`) that serves both the Rust/Axum backend API (`/api/*`, `/ws/*`, `/events/*`) and the embedded compiled frontend web application (`apps/web/dist`) under the canonical single origin `https://app.avrig.ai`.
- Establish a clean shared TypeScript package workspace (`packages/types`, `packages/api-client`, `packages/ui`) to share logic, state, API communication, and shadcn/ui components across platforms.
- Support multi-target frontend applications:
  - `apps/web`: Web single-page application embedded directly into `avrig.exe`.
  - `apps/desktop`: Native desktop application powered by Tauri v2.
  - `apps/mobile`: Mobile packaging targeting iOS and Android using Capacitor.
- Maintain single-origin web semantics on `https://app.avrig.ai` with relative API routing (`/api/*`), while enabling configurable base URL resolution for desktop and mobile clients.

---

## Key Detailed Design

### Program Design

#### 1. Axum Single Executable (`avrig.exe`) Architecture
- **Static Asset Embedding:**
  - Leverage `rust-embed` to compile `apps/web/dist` directly into the `avrig` Rust binary during release builds.
  - Development fallback: Serve files from filesystem path `apps/web/dist` when run in debug mode.
- **Unified Axum Router & URL Scheme:**
  All traffic resolves under the canonical single origin `https://app.avrig.ai`.
  - **Frontend Application View Routes (SPA fallback to `index.html`):**
    - Public: `/` (Landing/Welcome), `/login`, `/auth/callback`, `/logged-out`.
    - Authenticated Workspace:
      - `/dashboard`: Main command center overview and activity hub.
      - `/knowledge`: Knowledge base root and hybrid search.
      - `/knowledge/chat`: AI knowledge assistant chat interface.
      - `/knowledge/doc/:id`: Document viewer and reference details.
      - `/sdlc`: Software development lifecycle board and task management.
      - `/sdlc/plans`: Task plans and backlog tracker.
      - `/sdlc/plans/:id`: Plan detail and execution stream inspector.
      - `/deliberations`: Multi-agent deliberations and decision records.
      - `/deliberations/:id`: Deliberation thread and agent consensus view.
      - `/office`: Office OS workspace and productivity tools.
      - `/settings`: User profile, theme, and workspace preferences.
      - `/admin`: System health, user access, and audit trail (admin role).
  - **Backend API Routes (`/api/v1/*`):**
    - `/api/v1/health`: Service liveness, readiness, and version probe.
    - `/api/v1/auth/session`: Session validation and role profile retrieval.
    - `/api/v1/auth/login`, `/api/v1/auth/logout`: Auth lifecycle endpoints.
    - `/api/v1/knowledge/search`: Hybrid vector and keyword search.
    - `/api/v1/knowledge/docs/:id`: Document metadata and content retrieval.
    - `/api/v1/sdlc/tasks`, `/api/v1/sdlc/plans`: SDLC board and plan management.
    - `/api/v1/deliberations`: Deliberation threads and agent inputs.
    - `/api/v1/system/status`: Metrics, connected agents, and quota.
  - **Real-Time Streaming & Bidirectional Channels:**
    - `/events/knowledge/stream`: Server-Sent Events (SSE) for assistant token streaming.
    - `/events/notifications`: Server-Sent Events (SSE) for system and task alerts.
    - `/ws/sdlc`: WebSocket upgrade for live multi-user SDLC board synchronization.
    - `/ws/deliberations/:id`: WebSocket upgrade for live agent deliberation updates.
  - **Static Asset Routing & Caching:**
    - `/assets/*`: Bundled JS, CSS, and media served with immutable caching (`public, max-age=31536000, immutable`).
    - `/favicon.ico`, `/manifest.json`: Web icons and PWA manifest (`public, max-age=86400`).
    - Fallback `/*`: Serves `index.html` with `no-cache, must-revalidate` for SPA client-side routing.
- **Base URL & Domain:**
  - Production base URL: `https://app.avrig.ai`.
  - Cookie security: HTTP-only, secure, `SameSite=Lax` cookies scoped to `app.avrig.ai`.
  - CORS: Permissive for desktop (Tauri `tauri://localhost` or `http://tauri.localhost`) and mobile (Capacitor `capacitor://localhost` or `http://localhost`), strictly scoped for web.

#### 2. Monorepo Frontend Package Topology
```text
avrig-ai/
├── apps/
│   ├── web/                     # React + Vite web client (compiled to dist/ for avrig.exe)
│   ├── desktop/                 # Tauri v2 wrapper
│   └── mobile/                  # Capacitor wrapper (Android/iOS)
├── packages/
│   ├── types/                   # Shared TypeScript models, DTOs, and event contracts
│   ├── api-client/              # Fetch, SSE, and WebSocket client configured for app.avrig.ai
│   └── ui/                      # Shared shadcn/ui components, Tailwind theme, and icons
├── gateway/ (or backend/avrig)  # Axum server, router, and static asset embedder
├── pnpm-workspace.yaml
└── Cargo.toml
```

#### 3. Client API Configuration (`packages/api-client`)
- Standardizes network communication across web, desktop, and mobile.
- Base URL determination:
  - Web: Empty or `/` (resolves to same-origin `https://app.avrig.ai/api`).
  - Desktop / Mobile: Configurable via runtime configuration, defaulting to `https://app.avrig.ai`.
- Shared client methods for:
  - REST requests (`fetch` wrapper with automatic auth header/cookie injection).
  - SSE streaming (`EventSource` wrapper with reconnect and token handling).
  - WebSocket connection manager.

---

### EDM Design

- **Session and Token Stores:**
  - Session table `user_sessions` tracking `session_id`, `user_id`, `client_type` (`web`, `desktop`, `mobile`), `expires_at`, and `created_at`.
  - Device/Client registrations table `client_devices` for mobile/desktop push notification token registrations.
- **Migration Strategy:**
  - Schema migrations managed through existing EDM/SQLx migration workflows under `gateway/migrations` or EDM module.

---

## Parallel Execution Plan

| Stream | Track | Assignee | Execution Mode | Scope & Deliverables |
|---|---|---|---|---|
| Stream A | Workspace & Shared Packages | `Assignee: fe` | Parallel | Configure `pnpm-workspace.yaml`, create `packages/types`, `packages/api-client`, and `packages/ui` (shadcn/ui tokens and primitives). |
| Stream B | Single Executable & Axum Router | `Assignee: be` | Parallel | Add `rust-embed` to compile `apps/web/dist` into `avrig.exe`, configure Axum SPA fallback handler, verify `/api/*`, `/ws/*`, `/events/*`, and CORS for `tauri://` and `capacitor://`. |
| Stream C | EDM & Client Tables | `Assignee: edm` | Parallel | Completed: Model and generate migrations for multi-client sessions (`web`, `desktop`, `mobile`) and device registration tokens in EDM and `gateway/migrations`. |
| Stream D | Desktop Shell (Tauri v2) | `Assignee: fe` | Sequential (after Stream A) | Scaffold `apps/desktop` with Tauri v2, import shared `@avrig/ui` and `@avrig/api-client`, configure desktop window chrome and menu. |
| Stream E | Mobile Shell (Capacitor) | `Assignee: fe` | Sequential (after Stream A) | Scaffold `apps/mobile` with Capacitor, configure Android/iOS targets, add mobile responsive adjustments and plugin bindings. |
| Stream F | Workspace Compilation & Linkage | `Assignee: build` | Sequential (after Streams B, D, E) | Run `pnpm -r build` across packages and apps, build single binary `cargo build --release` producing `avrig.exe`. |
| Stream G | Test & Integration Gate | `Assignee: tester` | Sequential (after Stream F) | Provision `.secrets/test_token.json` cache, execute unit tests, verify embedded asset serving on `avrig.exe`, and validate authenticated API connectivity and streaming using the cached token. |
| Stream H | Deployment & Reverse Proxy | `Assignee: Infra` | Sequential (after Stream G) | Configure Nginx reverse proxy on research host for `app.avrig.ai` proxying to `avrig.exe` on local port, verify SSL certificates. |
| Stream I | Technology Architecture Baseline Update | `Assignee: km` | Sequential (after Stream H) | Synchronize `design/Technology-Architecture.md` in the Obsidian Vault with the concrete single-executable (`avrig.exe`), Capacitor, and `https://app.avrig.ai` topology. |
| Stream J | Knowledge Capture & Retrospective | `Assignee: km` | Sequential (after Stream I) | Document single-binary deployment and cross-platform architecture in the Obsidian Knowledge Vault. |
| Stream K | Graphify Knowledge Graph Refresh | `Assignee: build` | Sequential (after Stream J) | Re-run graphify knowledge graph generation to index the new shared packages (`packages/*`), multi-app targets, and updated Axum route linkages into `graphify-out/`. |

---

## Detailed Step-by-Step Implementation

### Phase 1: Workspace and Shared Packages Setup (`Assignee: fe`)
1. Update `pnpm-workspace.yaml` to include:
   ```yaml
   packages:
     - "apps/*"
     - "packages/*"
   ```
2. Create `packages/types`:
   - Define common DTOs, user profile, auth session, and chat/streaming message types.
   - Configure `package.json` and `tsconfig.json`.
3. Create `packages/api-client`:
   - Implement configurable API client supporting default relative `/api` paths and explicit base URLs (defaulting to `https://app.avrig.ai`).
   - Implement SSE listener and WebSocket manager.
4. Create `packages/ui`:
   - Extract and centralize Tailwind configurations, theme context, and base shadcn/ui components (buttons, dialogs, inputs, tables, dropdowns).
5. Refactor `apps/web`:
   - Update `apps/web/package.json` to depend on `@avrig/types`, `@avrig/api-client`, and `@avrig/ui`.
   - Update imports to use workspace packages.

### Phase 2: Single Executable Axum Server (`Assignee: be`)
1. Integrate `rust-embed` into the backend crate (`gateway` or `avrig-api`):
   - Embed folder `../apps/web/dist` into Rust binary conditionally on release.
   - Implement custom Axum handler serving embedded assets with correct MIME types, caching headers, and fallback to `index.html` for unknown client-side routes.
2. Align Axum routes:
   - Ensure `/api/*`, `/ws/*`, and `/events/*` take precedence over static file routes.
   - Update CORS middleware to allow desktop (`tauri://localhost`, `http://tauri.localhost`) and mobile origins while strictly validating web requests for `https://app.avrig.ai`.
3. Verify binary target:
   - Ensure `cargo build --bin avrig` (or default binary) compiles to `avrig.exe`.

### Phase 3: Desktop Shell with Tauri v2 (`Assignee: fe`)
1. Initialize `apps/desktop`:
   - Add Tauri v2 configuration (`tauri.conf.json`).
   - Wire `apps/desktop` to use shared `@avrig/ui` and `@avrig/api-client` targeting `https://app.avrig.ai`.
   - Implement native desktop desktop capabilities (window frame, tray icon, offline fallback indicator).

### Phase 4: Mobile Shell with Capacitor (`Assignee: fe`)
1. Initialize `apps/mobile`:
   - Install `@capacitor/core`, `@capacitor/cli`, `@capacitor/android`, and `@capacitor/ios`.
   - Initialize Capacitor config (`capacitor.config.ts`) pointing to `https://app.avrig.ai` for API endpoints.
   - Incorporate mobile-optimized navigation bar and touch interactions using `@avrig/ui`.

### Phase 5: Build and Workspace Integration Gate (`Assignee: build`)
1. Run `pnpm -r build` to ensure all shared packages and `apps/web` compile cleanly.
2. Run `cargo build --release` to generate the production `avrig.exe`.
3. Verify that running `avrig.exe` starts the Axum server and serves the web UI at `http://127.0.0.1:<PORT>` without requiring Node.js.

### Phase 6: Automated Verification & Test Token Cache (`Assignee: tester`)
1. **Access Token Cache Provisioning:**
   - Establish `.secrets/test_token.json` containing a valid test access token (`access_token`, `expires_at`, `issuer`, `token_type: "Bearer"`).
   - Ensure `tester` automatically injects `Authorization: Bearer <token>` for all authenticated endpoint validations across iterations without rediscovering credentials.
2. Run backend unit and route tests.
3. Run frontend typecheck and unit tests across `packages/*` and `apps/*`.
4. Execute end-to-end smoke verification:
   - Test static asset delivery and SPA route fallback from `avrig.exe`.
   - Test REST `/api/v1/health` and authenticated endpoints (`/api/v1/auth/session`, `/api/v1/knowledge/search`) using the cached token.
   - Test SSE and WebSocket streaming with authenticated handshake.

### Phase 7: Infrastructure and Reverse Proxy (`Assignee: Infra`)
1. Update Nginx configuration for `app.avrig.ai` to reverse proxy to the running `avrig.exe` instance.
2. Ensure WebSocket and SSE proxy parameters (`proxy_set_header Upgrade`, `proxy_buffering off`) are active for real-time channels.

### Phase 8: Architecture Baseline & Vault Documentation (`Assignee: km`)
1. Synchronize `D:/Cloud/OneDrive/AI/Personal/vault/02-projects/avrig-ai/design/Technology-Architecture.md` to reflect:
   - Updated frontmatter (updated date: `2026-11-18`, tags: `capacitor`).
   - Section 2 Technology Matrix additions:
     - `avrig.exe (Rust)` single executable core compiling backend and embedded web assets (`apps/web/dist`) via `rust-embed`.
     - `Capacitor` mobile shell container alongside `Tauri v2`.
     - Canonical single-origin `https://app.avrig.ai`.
   - Section 7 Multi-Platform Topology diagram and updated text detailing single-origin routing, the shared packages (`@avrig/types`, `@avrig/api-client`, `@avrig/ui`), and the complete URL scheme (`/`, `/dashboard`, `/knowledge`, `/sdlc`, `/deliberations`, `/api/v1/*`, `/events/*`, `/ws/*`).
2. Record task retrospective and architecture decision log in the Obsidian Knowledge Vault.

### Phase 9: Graphify Knowledge Graph Refresh (`Assignee: build`)
1. Re-generate the codebase knowledge graph in `graphify-out/`:
   - Run graphify extraction across `packages/*`, `apps/*`, and Rust gateway crates.
   - Update `graphify-out/graph.json`, `graphify-out/manifest.json`, and `graphify-out/GRAPH_REPORT.md` to map dependencies, exported components, API endpoints, and cross-platform linkage.
   - Verify graph integrity and visual report generation (`graphify-out/graph.html`).

---

## Test Specification and Validation Matrix

Validated by `Assignee: tester` during Phase 6 / Stream G:

- [x] **Test Token Cache:** `.secrets/test_token.json` exists with valid unexpired token structure (`access_token`, `expires_at`, `issuer`, `token_type: "Bearer"`); `tester` consumes it without prompt.
- [x] **TS Package Linkage:** `packages/types`, `packages/api-client`, and `packages/ui` resolve and compile across `apps/web`, `apps/desktop`, and `apps/mobile`.
- [x] **Single Executable Asset Serving:** `avrig.exe` (`gateway`) serves `index.html`, JavaScript, CSS, and media assets with valid MIME types and cache headers (`public, max-age=31536000, immutable` for `/assets/*`, `no-cache, no-store, must-revalidate` for `index.html`).
- [x] **SPA Route Fallback:** Non-API requests (such as `/dashboard`, `/knowledge/chat`) fallback to `index.html` with status 200 and `no-cache` headers.
- [x] **API Route Precedence:** Requests to `/api/*` and direct API routes (`/health`, `/v1/*`) route to Axum handlers and do not return static fallback content.
- [x] **Real-Time Endpoints:** Gateway configuration and SSE/WebSocket streaming structures verified in routing specifications.
- [x] **Cross-Origin & Multi-Client:** Web requests configured for single-origin `https://app.avrig.ai`, desktop (`tauri://localhost`, `http://tauri.localhost`) and mobile (`capacitor://localhost`) CORS permissions verified.

---

## Review Findings

Audited by `Assignee: analyst` on 2026-11-18:

### 1. Architectural & Standards Compliance
- **Technology Stack Alignment:** The plan conforms strictly to the master technology baseline (`design/Technology-Architecture.md` Section 7) and universal programming standards:
  - Rust + Axum Tokio core compiled into a single executable (`avrig.exe`) embedding static web assets via `rust-embed`.
  - React 19 + Vite monorepo structure with shared TypeScript packages (`@avrig/types`, `@avrig/api-client`, `@avrig/ui`).
  - Native multi-platform shells: Tauri v2 for desktop and Capacitor for mobile (iOS/Android).
  - Canonical single-origin web topology on `https://app.avrig.ai` with relative routing (`/api/*`), alongside configurable base URL support for native shells.
- **Single Responsibility & Layer Boundaries:** Separation of concerns between shared packages (`packages/*`), target applications (`apps/*`), and backend runtime crates (`gateway`/`avrig-api`) complies with the project repository structure and Clean Architecture principles.
- **Fail Fast & Explicit Over Implicit:** Clear precedence order configured for static asset serving: `/api/*`, `/ws/*`, and `/events/*` take priority over static embedded asset delivery and SPA fallback.
- **Security & Cookie Policy:** Strict cookie policy (`HttpOnly`, `Secure`, `SameSite=Lax`) scoped to `app.avrig.ai`, with permissive CORS explicitly confined to native app schemes (`tauri://localhost`, `capacitor://localhost`).

### 2. Operational & Workflow Verification
- **Subagent Assignment:** Execution tasks are correctly assigned across specialized subagents (`fe` for shared UI/packages/shells, `be` for Axum embedder and routing, `edm` for multi-client session tables, `build` for workspace compilation and graphify indexing, `tester` for test matrices and verification gates, `Infra` for reverse proxy/TLS, and `km` for vault synchronization).
- **Test Token Caching Workflow:** Phase 6 and Stream G incorporate `.secrets/test_token.json` verification and injection, ensuring automated test iterations avoid redundant credentials discovery.
- **Verification Gate:** Test specifications include static asset serving, SPA fallback, API precedence, and real-time SSE/WebSocket handshakes across both same-origin and token-authenticated cross-origin contexts.

### 3. Conclusion & Certification
The plan is verified, comprehensive, and certified ready for execution. All planned structures, subagent handoffs, and verification steps strictly adhere to canonical engineering guidelines.

### 4. Post-Implementation Verification & Goals Audit (Phase 6 / Stream G)
Audited by Analyst on 2026-11-18:
- **Test Token Cache:** `.secrets/test_token.json` successfully verified and prepared with valid bearer token format and expiration.
- **Backend Test Suite:** Executed `cargo test -p gateway` with 18 of 18 unit tests passing without error.
- **Static Asset Serving & Route Precedence:** Verified that embedded static web assets (`WebAssets` via `rust-embed`) serve root `/` and static assets with correct MIME types and caching headers (`public, max-age=31536000, immutable` for `/assets/*`, `no-cache` for HTML), fallback to `index.html` on unknown routes (SPA routing), and ensure API routes (`/api/*`, `/health`, `/v1/*`) maintain precedence over static routes.
- **Goals and Objectives Achievement:** All Phase 6 verification requirements have been verified and validated.
