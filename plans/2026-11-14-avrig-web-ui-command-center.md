---
title: "Plan: avrig Web UI Command Center with Universal OIDC and Runtime Configuration"
type: canonical
status: active
source-of-truth: true
domain: engineering
subdomain: architecture
category: implementation-plan
topic: web-command-center
created: 2026-11-14
updated: 2026-11-14
author: avrig-ai
tags:
  - plan
  - architecture
  - frontend
  - react
  - oidc
  - keycloak
  - authentik
  - rauthy
  - runtime-config
  - vite
  - tailwindcss
---

# Plan: avrig Web UI Command Center with Universal OIDC and Runtime Configuration

**Status:** Active Implementation Plan  
**Parent Documents:** `[[design/System-Architecture|System Architecture]]`, `[[design/Technology-Architecture|Technology Architecture]]`, `[[development/Repository|Repository Architecture]]`, `[[03-knowledge/programming/react-js/React-Runtime-Config|React Runtime Configuration]]`  
**Target Codebases:** `avrig-ui` (`D:\Cloud\OneDrive\AI\Agentic\avrig-ui`), `avrig-ai` (`D:\Cloud\OneDrive\AI\Agentic\avrig-ai`)  
**Scope:** Architecture, component library setup, runtime dynamic configuration (`/config.json`), universal OIDC client integration (supporting Rauthy, Keycloak, Authentik), and core Command Center domain modules (Office OS, Meeting Deliberation, SDLC Pipeline, Knowledge Traceability).

---

## 1. Executive Summary & Architectural Goals

The **avrig Web UI** is the browser-based Command Center of the virtual autonomous engineering organization. It provides the human Founder and operational leaders with real-time visibility and governance over AI agents, meeting deliberations, organizational departments, and the 16-stage canonical SDLC.

Key Architectural Directives:
1. **Separation of Presentation and Application:**
   - Pure UI component primitives, design tokens, and theme styles reside in the `avrig-ui` repository, published as `@avrig/ui` with zero domain business logic.
   - The multi-target application shell resides in `avrig-ai` (`apps/web` and `frontend/`).
2. **Runtime Configuration (`React-Runtime-Config` Pattern):**
   - No build-time inlining of environment variables (`VITE_*`).
   - The compiled React bundle fetches `GET /config.json` at startup with `{ cache: "no-store" }`.
   - The exact same compiled artifact runs across local dev, staging, WSL testing, and production without rebuilding.
3. **Universal OpenID Connect (`[IAM]`):**
   - Uses standard-compliant OpenID Connect Core 1.0 and OAuth 2.1 with PKCE (`oidc-client-ts` and `react-oidc-context`).
   - Universal compatibility across **Rauthy**, **Keycloak**, and **Authentik** driven entirely by standard OIDC discovery endpoints configured via `config.json`.
4. **Real-Time Streaming & Event Bus:**
   - Axum API Gateway REST integration paired with WebSocket client connections for live meeting transcripts, spatial presence, and SDLC stage updates.

---

## 2. System Architecture & Component Topology

```text
┌────────────────────────────────────────────────────────────────────────┐
│                         BROWSER / CLIENT STARTUP                       │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Download index.html + immutable React bundle (Vite SPA)            │
│ 2. Top-level bootstrap: GET /config.json (no-store cache)              │
│    - API Gateway URL                                                   │
│    - WebSocket Hub URL                                                 │
│    - Universal OIDC Authority & Client ID                              │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Initialize Universal OIDC Client (oidc-client-ts)                   │
│    - Query {authority}/.well-known/openid-configuration                │
│    - Authenticate user via PKCE (Rauthy / Keycloak / Authentik)        │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Mount React Root (<App />)                                          │
│    - ConfigContext: supplies runtime settings                          │
│    - AuthContext: supplies JWT access token & user claims              │
│    - QueryClientProvider: TanStack Query v5 cache                      │
│    - ApiClient & WsManager: Bearer token injection                     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        CORE APPLICATION MODULES                        │
├──────────────────┬──────────────────┬──────────────────┬───────────────┤
│  Office & Org    │  Deliberations   │   SDLC Board     │  Knowledge &  │
│  Hierarchy [OG]  │  Rooms [MT]      │   16-Stage [SD]  │  Trace [KM]   │
│  - Departments   │  - Speaker queue │   - Gate review  │  - RAG search │
│  - AI employees  │  - Live speech   │   - Hash verify  │  - AGE graph  │
│  - Status cards  │  - Voting record │   - Baseline sign│  - Lineage    │
└──────────────────┴──────────────────┴──────────────────┴───────────────┘
```

---

## 3. Universal OIDC & Runtime Configuration Specification

### 3.1 `config.json` Contract

The public deployment artifact contains `config.json` alongside compiled static assets:

```json
{
  "apiBaseUrl": "https://api.avrig.ai:8000",
  "wsBaseUrl": "wss://api.avrig.ai:8000",
  "auth": {
    "authority": "https://auth.avrig.ai",
    "clientId": "avrig-web-ui",
    "scope": "openid profile email",
    "redirectUri": "https://web.avrig.ai/auth/callback",
    "postLogoutRedirectUri": "https://web.avrig.ai/",
    "responseType": "code",
    "automaticSilentRenew": true
  },
  "features": {
    "spatialCanvas": true,
    "experimentalGraph": true
  }
}
```

### 3.2 Multi-IdP Compatibility Matrix

| Identity Provider | Example `authority` Value in `config.json` | Discovery Endpoint Queried Automatically |
|---|---|---|
| **Rauthy** | `https://auth.avrig.ai` | `https://auth.avrig.ai/.well-known/openid-configuration` |
| **Keycloak** | `https://sso.example.com/realms/avrig` | `https://sso.example.com/realms/avrig/.well-known/openid-configuration` |
| **Authentik** | `https://authentik.example.com/application/o/avrig/` | `https://authentik.example.com/application/o/avrig/.well-known/openid-configuration` |

### 3.3 Bootstrap Implementation (`src/main.tsx` & `src/shared/config/`)

```ts
// src/shared/config/types.ts
export interface OidcConfig {
  authority: string;
  clientId: string;
  scope?: string;
  redirectUri?: string;
  postLogoutRedirectUri?: string;
  responseType?: string;
  automaticSilentRenew?: boolean;
}

export interface AppConfig {
  apiBaseUrl: string;
  wsBaseUrl: string;
  auth: OidcConfig;
  features: Record<string, boolean>;
}

export async function loadConfig(): Promise<AppConfig> {
  const response = await fetch("/config.json", {
    cache: "no-store",
    headers: {
      "Accept": "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to load runtime configuration: ${response.status} ${response.statusText}`);
  }

  return response.json();
}
```

```tsx
// src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { loadConfig } from "./shared/config/loadConfig";
import { ConfigContext } from "./shared/config/ConfigContext";
import { UniversalAuthProvider } from "./shared/auth/UniversalAuthProvider";
import { App } from "./app/App";
import "./styles/globals.css";

async function bootstrap() {
  try {
    const config = await loadConfig();

    createRoot(document.getElementById("root")!).render(
      <StrictMode>
        <ConfigContext.Provider value={config}>
          <UniversalAuthProvider>
            <App />
          </UniversalAuthProvider>
        </ConfigContext.Provider>
      </StrictMode>
    );
  } catch (err) {
    renderBootstrapError(err);
  }
}

bootstrap();
```

---

## 4. Work Breakdown Structure & Subagent Assignments

Per the project governance mandates in `AGENTS.md`, all activities are explicitly assigned to their designated subagent (`fe`, `Infra`, `edm`, or primary orchestrator):

### Phase 1: Shared Component Library (`avrig-ui`)
- **Assigned Agent:** `fe` (Frontend Specialist Subagent)
- **Repository:** `D:\Cloud\OneDrive\AI\Agentic\avrig-ui`
- **Tasks:**
  1. Initialize workspace with pnpm and TypeScript (`tsconfig.base.json`).
  2. Configure Tailwind CSS v4 design tokens in `packages/tokens` (colors, semantic variables, dark/light themes).
  3. Implement accessible UI primitives in `packages/ui` based on Radix UI / shadcn patterns:
     - `Button`, `Dialog`, `Sheet`, `DropdownMenu`, `Card`, `Badge`, `Tabs`, `Table`, `Avatar`, `ScrollArea`.
  4. Implement composite shell widgets:
     - `CommandPalette` (fuzzy action quick launcher).
     - `DataTable` (sortable, paginated, filterable grid).
  5. Configure build and package exports under the package name `@avrig/ui`.
- **Pre-execution Gate:** Propose component structure and design token schema to user; obtain confirmation before writing files.

### Phase 2: Web Application Shell & Universal Auth (`avrig-ai`)
- **Assigned Agent:** `fe` (Frontend Specialist Subagent)
- **Repository:** `D:\Cloud\OneDrive\AI\Agentic\avrig-ai`
- **Tasks:**
  1. Setup Vite application structure in `apps/web` with React 19 and `@avrig/ui` linkage.
  2. Implement runtime config loader (`/config.json`) and resilient bootstrap screen.
  3. Implement Universal OIDC authentication wrapper (`react-oidc-context` + `oidc-client-ts`):
     - Login, callback routing, and silent token renewal.
     - Protected route boundary component.
  4. Implement API and WebSocket infrastructure:
     - Axios/fetch client with dynamic `baseURL` and Bearer token interceptor.
     - Resilient WebSocket connection manager handling reconnection and channel subscriptions.
  5. Implement root layout: Responsive collapsible sidebar, top status bar, active actor badge, and global search trigger.
- **Pre-execution Gate:** Propose `config.json` schema, layout wireframe, and OIDC client configuration to user; obtain confirmation before writing files.

### Phase 3: Domain Modules Development
- **Assigned Agent:** `fe` (Frontend Specialist Subagent)
- **Module 1: Office Operating System (`[OG]`, `[WF]`):**
  - Department organization tree with executive reporting lines.
  - AI Employee roster view with status badges (Idle, Thinking, Working, Deliberating).
  - Employee detail drawer with skill profiles, assigned roles, and current task trace.
- **Module 2: Meeting Deliberation Rooms (`[MT]`):**
  - Active and scheduled meeting rooms dashboard.
  - Live deliberation room viewport:
    - Speaker turn queue and active speaker indicator.
    - Real-time speech transcript feed over WebSocket.
    - Consensus / voting panel and formal resolution recorder.
- **Module 3: Agentic SDLC Board (`[RE]` through `[TE]`):**
  - 16-stage pipeline board with stage health indicators.
  - Stage detail view showing active work items and baseline status.
  - Stage Gate review modal: checklist validation, cryptographic SHA-256 baseline diff, and Founder sign-off button.
- **Module 4: Knowledge Management & Traceability (`[KM]`, `[TR]`):**
  - Epistemic hybrid search bar (lexical and vector results).
  - Traceability graph explorer visualizing links between requirements, decisions, tasks, and artifacts.
- **Pre-execution Gate:** Present module mockups and state integration contracts to user before implementation.

### Phase 4: Verification, Hardening & Deployment
- **Assigned Agents:** `fe` (Client Verification & UI Tests) & `Infra` (Nginx Reverse Proxy & OIDC Client Registration on Rauthy)
- **Tasks:**
  1. `Infra`: Ensure OIDC client `avrig-web-ui` with redirect URI `https://web.avrig.ai/auth/callback` is registered in Rauthy and Nginx reverse proxy serves `web.avrig.ai`.
  2. `fe`: Verify seamless authentication against Rauthy (`https://auth.avrig.ai`).
  3. `fe`: Verify switching to Keycloak and Authentik by simply modifying `config.json` without recompilation.
  4. `fe`: Validate graceful behavior when `config.json` is missing or contains malformed values.
  5. `fe`: Verify automatic token refresh and WebSocket reconnection after network drops.
  6. `fe`: Lighthouse audit targeting 95+ score for accessibility, best practices, and performance.

---

## 5. Acceptance Criteria

1. **Build Immutability:** A single compiled production build of `avrig-ai/apps/web` runs in different environments purely by changing `config.json`.
2. **Universal OIDC Verification:** The client logs in, obtains claims, and refreshes tokens against standard OIDC discovery endpoints for Rauthy, Keycloak, and Authentik.
3. **Zero Secrets in Client:** No client secrets or private credentials are included in the bundle or `config.json`.
4. **Clean Layer Separation:** `avrig-ui` contains zero API or domain invariants; `avrig-ai` consumes components purely through `@avrig/ui` props.
5. **Real-Time Responsiveness:** Deliberation room speech transcripts and stage status updates render via WebSocket events with sub-second latency.
