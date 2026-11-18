---
title: "Plan: Unified avrig Executable with Multi-Role Daemon, TOML Config, and Rauthy OIDC"
type: canonical
status: completed
source-of-truth: true
domain: engineering
subdomain: architecture
category: implementation-plan
topic: unified-avrig-runtime
created: 2026-11-13
updated: 2026-11-13
author: avrig-ai
tags:
  - plan
  - architecture
  - rust
  - axum
  - notify
  - oidc
  - rauthy
  - toml
  - cross-platform
---

# Plan: Unified avrig Executable with Multi-Role Daemon, TOML Config, and Rauthy OIDC

**Status:** Active Implementation Plan  
**Parent Documents:** `[[design/System-Architecture|System Architecture]]`, `[[design/Technology-Architecture|Technology Architecture]]`, `[[design/Knowledge-Management|Knowledge Management]]`, `[[development/Repository|Repository Architecture]]`  
**Primary Target Binaries:** Windows (`avrig.exe`), Linux (`avrig`)  
**Scope:** Architecture, configuration layout, concurrency model, REST endpoints, and verification steps for a single multi-role executable supporting API server, directory-watching agent, hash-based pre-flight deduplication, and Rauthy OIDC authentication.

---

## 1. Executive Summary & Core Requirements

This plan defines the concrete implementation of the unified, cross-platform `avrig` executable. The binary operates across both Windows and Linux, consolidating server listeners, background worker threads, and folder-watching ingestors into a single, cohesive binary.

Key requirements:
1. **Single Executable:** A single binary name (`avrig.exe` on Windows, `avrig` on Linux).
2. **Multi-Role Concurrency:** A single running process can activate one or multiple roles concurrently (for example, server and watcher).
3. **TOML Configuration System:** All operational settings are defined in TOML files located by default in a `config/` subfolder next to the executable, with multi-file composition support and command-line override capability.
4. **Clean API & CLI Namespaces:** Neither the CLI commands nor the HTTP service endpoints include `km` in their naming. Resource paths use clean standard conventions (such as `/api/v1/documents/*` and `/api/v1/search/*`).
5. **Pre-Flight Hash Deduplication:** The directory-watching agent computes streaming SHA-256 hashes for detected local files and performs a remote pre-flight check before initiating uploads. Identical content is skipped without transferring file binaries.
6. **Rauthy OIDC Integration:** Authentication is strictly anchored to the existing Rauthy IAM deployment (`https://iam.avrig.ai/auth/v1/`). Interactive users utilize Authorization Code with PKCE; background watcher daemons utilize OAuth 2.1 Client Credentials.

---

## 2. Process Architecture & Concurrency Model

A single `avrig` process hosts an asynchronous Tokio runtime capable of spawning independent task supervisors per activated role.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        avrig / avrig.exe                               │
│              Single Process / Multi-Role Daemon Runtime                │
├────────────────────────────────────────────────────────────────────────┤
│                     Tokio Multi-Threaded Runtime                       │
│                                                                        │
│   ┌──────────────────────────────┐    ┌────────────────────────────┐   │
│   │         SERVER ROLE          │    │        WATCHER ROLE        │   │
│   │     (tokio::spawn task)      │    │    (tokio::spawn task)     │   │
│   ├──────────────────────────────┤    ├────────────────────────────┤   │
│   │ • Axum Gateway (port 8000)   │    │ • Folder monitor (notify)  │   │
│   │ • /api/v1/documents/*        │    │ • Streaming SHA-256 calc   │   │
│   │ • /api/v1/search/*           │    │ • Pre-flight hash check    │   │
│   │ • Context Engine             │    │ • In-process or HTTP dispatch│ │
│   └──────────────┬───────────────┘    └──────────────┬─────────────┘   │
│                  │                                   │                 │
│                  └─────────────────┬─────────────────┘                 │
│                                    ▼                                   │
│                     Coordinated Shutdown Supervisor                    │
│                 (CancellationToken on SIGINT / SIGTERM)                │
└────────────────────────────────────────────────────────────────────────┘
```

### Role Activation
- **Combined Mode:** `avrig.exe run` with `roles = ["server", "watcher"]` in `config/config.toml`. Both roles execute in the same process. When co-located, the watcher can invoke the document service directly in memory without network latency.
- **Standalone Server Mode:** `avrig.exe serve` selects the server role and uses server settings from TOML.
- **Standalone Watcher Mode:** `avrig.exe watch` selects the watcher role and uses watcher settings from TOML to connect to a remote or local API server over HTTPS.

---

## 3. Configuration Discovery & TOML Composition

All configuration settings are maintained in TOML files.

### 3.1 Resolution Precedence
The configuration loader uses TOML files as the source of all operational settings:
1. **Explicit CLI Path (`-c`, `--config`):** Overrides default locations. If pointing to a file, that file is loaded; if pointing to a directory, all `*.toml` files in that directory are loaded and merged.
2. **Default Executable Directory Discovery:** Resolves `<exe_dir>/config/config.toml`. If `<exe_dir>/config/` exists, all other `*.toml` files in that directory are discovered and merged in alphabetical order.
3. **CLI Role Selection:** Commands such as `serve`, `watch`, and `run` select active roles. Configuration values such as ports, paths, endpoints, and timeouts remain in TOML and are not overridden by environment variables or individual runtime flags.

### 3.2 Modular Configuration Structure
```text
<exe_dir>/config/
├── config.toml           # Core node identity and default active roles
├── server.toml           # HTTP listen ports, PostgreSQL, Garage S3 bindings
├── watcher.toml          # Directory watch targets, include/exclude rules
├── oidc.toml             # Rauthy OIDC discovery and validation parameters
└── secrets.toml          # Vault Transit ciphertext only
```

#### `config/config.toml` (Global Settings)
```toml
[node]
id = "node-alpha"
roles = ["server", "watcher"]

[logging]
level = "info"
format = "full"
```

#### `config/server.toml` (Server Role)
```toml
[server]
host = "127.0.0.1"
port = 8000
database_url = "postgresql://avrig@127.0.0.1:5432/avrig"
garage_endpoint = "http://127.0.0.1:3900"
```

#### `config/secrets.toml` (Vault-Encrypted Secret Values)
```toml
[vault]
address = "https://vault.avrig.ai"
transit_mount = "transit"
transit_key = "avrig-config"
# Vault authentication uses a platform-approved local agent or machine identity.
# Do not put a Vault token or plaintext secret in this file.

[secrets.database]
password_ciphertext = "vault:v1:<ciphertext>"

[secrets.watcher_oidc]
client_secret_ciphertext = "vault:v1:<ciphertext>"
```

Secret values may be stored in TOML only as ciphertext produced by Vault Transit. The runtime decrypts them through Vault. The Vault authentication credential itself must be supplied through a protected machine identity or local agent, not embedded in TOML. Protect TOML file access with platform file permissions.

#### `config/oidc.toml` (Authentication & Security)
```toml
[oidc]
issuer_url = "https://iam.avrig.ai/auth/v1/"
discovery_url = "https://iam.avrig.ai/auth/v1/.well-known/openid-configuration"
audience = "avrig-api"
required_scopes = ["documents:read", "documents:write"]
jwks_refresh_interval_seconds = 300
clock_skew_seconds = 60

[auth_client]
token_endpoint = "https://iam.avrig.ai/auth/v1/oidc/token"
client_id = "avrig-watcher-agent"
# Client secret ciphertext is stored in secrets.toml and decrypted through Vault Transit.
```

#### `config/watcher.toml` (Watcher Role)
```toml
[watcher]
debounce_ms = 1000
poll = false
direct_in_process = true

[[watcher.targets]]
path = "D:\\Knowledge\\Platform"
scope = "platform"
knowledge_category = "BestPractice"
include_patterns = ["*.md", "*.pdf", "*.docx", "*.xlsx"]
exclude_patterns = ["*.tmp", ".~*", ".DS_Store", "desktop.ini"]

[[watcher.targets]]
path = "D:\\Knowledge\\ProjectAlpha"
scope = "project"
project_id = "0193234a-9b41-7100-8800-000000000001"
knowledge_category = "AuthoritativeRequirement"
include_patterns = ["*.md", "*.pdf", "*.docx"]
```

---

## 4. API Service Endpoints (Without `km` Namespace)

All endpoints reside under `/api/v1/`.

| Method | Endpoint | Description | Scope |
| :--- | :--- | :--- | :--- |
| `HEAD` / `GET` | `/api/v1/documents/by-hash/{sha256}` | Pre-flight hash verification. Returns `200 OK` if the document is already registered and indexed, `404 Not Found` if new. | `documents:read` |
| `POST` | `/api/v1/documents/upload` | Creates a temporary `DocumentInUpload` record, verifies the content hash, processes the file, then creates or resolves the canonical `Document` and its source/project mappings. | `documents:write` |
| `GET` | `/api/v1/documents` | List registered documents with filtering by project association and MIME type. Documents without project mappings are platform-level. | `documents:read` |
| `GET` | `/api/v1/documents/{id}` | Retrieve canonical document metadata and available chunk/indexing summary. Temporary upload status is not part of `Document`. | `documents:read` |
| `GET` | `/api/v1/documents/{id}/download-url` | Generate a presigned Garage S3 download URL. | `documents:read` |
| `GET` | `/api/v1/documents/{id}/sources` | List recorded source locations for a canonical document. | `documents:read` |
| `POST` | `/api/v1/documents/{id}/sources` | Add a source-location reference to an existing document. | `documents:write` |
| `GET` | `/api/v1/documents/{id}/projects` | List projects mapped to a document. | `documents:read` |
| `PUT` | `/api/v1/documents/{id}/projects/{project_id}` | Idempotently associate a document with a project. | `documents:write` |
| `DELETE` | `/api/v1/documents/{id}/projects/{project_id}` | Remove a document-project association. | `documents:write` |
| `DELETE`| `/api/v1/documents/{id}` | Soft-delete document, marking chunks inactive. | `documents:admin` |
| `GET` | `/api/v1/documents/{id}/chunks` | List normalized chunks belonging to a document. | `documents:read` |
| `GET` | `/api/v1/chunks/{id}` | Retrieve single chunk text, token count, and knowledge-category tags. | `documents:read` |
| `PATCH` | `/api/v1/chunks/{id}/knowledge-category` | Update the user-facing knowledge category. | `documents:admin` |
| `POST` | `/api/v1/search/hybrid` | Execute hybrid vector and lexical FTS search with RRF scoring and cross-encoder reranking. | `search:read` |
| `POST` | `/api/v1/context/resolve` | Context Engine (`[CX]`): returns prioritized, token-budgeted context for an active agent runtime. | `search:read` |
| `GET` | `/api/v1/stages/{stage_id}/requirements` | Fetch authoritative requirements and baselines for an SDLC stage. | `search:read` |
| `GET` | `/api/v1/traceability/graph` | Query openCypher graph (Apache AGE) linking requirements to deliverables. | `traceability:read` |
| `POST` | `/api/v1/traceability/links` | Record a bidirectional link in the knowledge graph. | `traceability:write` |
| `GET` | `/api/v1/health` | Comprehensive health check (PostgreSQL, Garage S3, Rauthy OIDC). | Public |

---

## 5. Folder Watcher & Pre-Flight Hash Verification Flow

```text
Local File System Event (Create/Modify)
                 │
                 ▼
     Debounce Window (1000ms)
                 │
                 ▼
      Wait for File Unlock
                 │
                 ▼
  Streaming SHA-256 Calculation (64KB chunks)
                 │
                 ▼
Pre-Flight Check: HEAD /api/v1/documents/by-hash/{sha256}
        │                                │
  [200 OK: Existing ID]         [404: Not Found]
        │                                │
        ▼                                ▼
Attach source/project refs       Fetch Rauthy Bearer Token
without re-uploading                      │
                                         ▼
                              Create DocumentInUpload
                                         │
                                         ▼
                             Verify/hash and process file
                                         │
                                         ▼
               Create Document + DocumentSourceLocation
                    + DocumentProject associations
                                         │
                                         ▼
                    Delete DocumentInUpload on success
```

1. **Native OS Event Capture:** Uses the `notify` crate (`ReadDirectoryChangesW` on Windows, `inotify` on Linux).
2. **Debounce & Stabilization:** Wait until file writes settle (default `1000ms`) and confirm the file is unlocked.
3. **Zero-Copy Streaming Checksum:** Computes SHA-256 over a 64 KB streaming buffer without loading large files into memory.
4. **Pre-Flight Query:** Calls `HEAD /api/v1/documents/by-hash/{sha256}`. A `200 OK` response identifies existing canonical content; `404 Not Found` means the binary is not yet registered.
5. **Hash Match:** If the hash lookup returns an existing document ID, do not upload the binary. Record the newly observed source location and requested project association against that canonical document using the source and project mapping endpoints.
6. **Secure Multipart Upload:** If the hash is not found, upload the binary and metadata through `POST /api/v1/documents/upload`. The request includes the computed `sha256`, original source path, source platform, optional `project_id`, and user-facing `knowledge_category`.
7. **Temporary Processing and Promotion:** The API creates `DocumentInUpload`, validates the hash against received bytes, stores and processes the file, creates the canonical `Document`, adds `DocumentSourceLocation` and `DocumentProject` records, then deletes `DocumentInUpload` after success. Failed `DocumentInUpload` records remain available for retry or diagnosis. If another request wins the global unique-hash race, resolve the existing `Document`, attach the new source/project mappings, and remove the redundant in-flight record.
8. **Actor Audit:** The API derives the actor from the validated Rauthy token. Do not add custom `uploaded_by_*` attributes. Use the EDM standard `created_by` field where its type is compatible with the identity subject; resolve that mapping during EDM modeling.

---

## 6. Document Provenance Model & Schema Governance

### 6.1 Schema Governance Directive
In accordance with project directives in `AGENTS.md`, **no database objects (tables, columns, indexes, or migrations) may be created or modified ad-hoc** directly within repository code, raw SQL files, or during this runtime phase.

All entity creation and changes to entities, attributes, relationships, indexes, and schema definitions must be performed through the `manage-edm` skill (`$env:OPENCODE_CONFIG_DIR/shared/skills/manage-edm`). Do not create or modify EDM definitions through ad-hoc scripts or raw SQL.

Before any EDM mutation, verify write access to the target and confirm explicit user authorization. If write access is absent or cannot be verified, limit work to planning or read-only inspection. Creating or deploying physical database objects requires separate explicit deployment approval and confirmed database write access.

### 6.2 Logical `Project` Entity Design
**Planned EDM assignment:** `Project` entity → Engineering SDLC domain (`ES`), Requirements Engineering module (`RE`). Read-only EDM inspection confirmed this domain and module exist and that `Project` is not currently registered there. Do not create or move the entity until write access is verified and the EDM change is authorized.

Base `Project` on the EDM `standard` entity-domain template. It contributes `id`, `project_code`, `project_name`, `project_desc`, `is_active`, `created_by`, `created_time`, `updated_by`, `updated_time`, `is_deleted`, `deleted_by`, and `deleted_time`. No additional project-specific attributes are proposed at this stage.

### 6.3 Logical `Document` Entity Design
**Planned EDM assignment:** `Document` entity → Agent Harness domain (`AH`), Knowledge Management module (`KM`), schema `km`. Read-only EDM inspection confirmed the target domain and module exist and that `Document` is not currently registered there.

Base `Document` on the EDM `standard` entity-domain template. It contributes `id`, `document_code`, `document_name`, `document_desc`, `is_active`, `created_by`, `created_time`, `updated_by`, `updated_time`, `is_deleted`, `deleted_by`, and `deleted_time`. Add:

| Attribute | Proposed type/domain | Purpose |
|---|---|---|
| `sha256` | `varchar(64)`, globally unique | Server-verified content hash and canonical identity for identical file content. |
| `file_name` | `varchar(255)` | Original filename associated with the canonical document. |
| `mime_type` | `varchar(100)` | Detected or verified media type. |
| `size_bytes` | `bigint` | File size in bytes. |
| `storage_bucket` | `varchar(100)` | Garage bucket containing the document binary. |
| `storage_key` | `varchar(255)` | Object identifier used with `storage_bucket` to retrieve the binary. |

Project associations are represented by `DocumentProject`, and source paths by `DocumentSourceLocation`; neither is stored directly on `Document`. Do not add `process_status_flag`, `knowledge_status`, or custom `uploaded_by_*` attributes. Watcher configuration remains in TOML. The standard `created_by` field is the planned record of the authenticated creator; confirm that Rauthy subject identifiers can be mapped to the standard field.

### 6.4 Logical `DocumentInUpload` Entity Design
**Planned EDM assignment:** `DocumentInUpload` entity → Agent Harness domain (`AH`), Knowledge Management module (`KM`), schema `km`.

`DocumentInUpload` is a temporary record for a file being received and processed. Base it on the EDM `standard` entity-domain template and include:

| Attribute | Proposed type/domain | Purpose |
|---|---|---|
| `sha256` | `varchar(64)` | Hash calculated by the client and verified by the server. |
| `file_name` | `varchar(255)` | Original filename during ingestion. |
| `source_path` | `text` | Original client-side path, transferred to `DocumentSourceLocation` on success. |
| `source_platform` | `varchar(20)` | Client operating system, such as `windows` or `linux`. |
| `mime_type` | `varchar(100)` | Detected or verified media type. |
| `size_bytes` | `bigint` | File size in bytes. |
| `project_id` | `uuid`, nullable, foreign key to `Project.id` | Optional project association to create after successful processing. |
| `knowledge_category` | EDM-approved type, pending confirmation | User-facing classification supplied for indexing. |
| `process_status_flag` | EDM `flag` column domain (`varchar(5)`) | Proposed values: `INIT`, `PEND`, `PROC`, `DONE`, `FAIL`. |
| `document_id` | `uuid`, nullable, foreign key to `Document.id` | Canonical document created or matched during processing. |

The lifecycle is `INIT` → `PEND` → `PROC` → `DONE` → delete. Delete the temporary record only after the canonical document and required mappings are committed. Failed records may remain in `FAIL` for retry or diagnosis; retention and cleanup rules are operational policy, not watcher configuration.

### 6.5 Logical `DocumentSourceLocation` Entity Design
**Planned EDM assignment:** `DocumentSourceLocation` entity → Agent Harness domain (`AH`), Knowledge Management module (`KM`), schema `km`.

This entity preserves every observed source path without overwriting the canonical document record. Base it on the EDM `standard` entity-domain template and add:

| Attribute | Proposed type/domain | Purpose |
|---|---|---|
| `document_id` | `uuid`, foreign key to `Document.id` | Canonical document associated with this source location. |
| `project_id` | `uuid`, nullable, foreign key to `Project.id` | Project context for this particular source location. Null for platform-level source locations. |
| `source_path` | `text` | Original local absolute path reference. The file may no longer exist at that path. |
| `source_platform` | `varchar(20)` | Operating system where the path was observed, such as `windows` or `linux`. |

Multiple source-location records may refer to one canonical document. Treat paths as sensitive metadata and restrict their exposure.

### 6.6 Logical `DocumentProject` Entity Design
**Planned EDM assignment:** `DocumentProject` entity → Agent Harness domain (`AH`), Knowledge Management module (`KM`), schema `km`.

This association entity links a canonical document to a project. Base it on the EDM `standard` entity-domain template and add:

| Attribute | Proposed type/domain | Purpose |
|---|---|---|
| `document_id` | `uuid`, foreign key to `Document.id` | Document in the association. |
| `project_id` | `uuid`, foreign key to `Project.id` | Authoritative project in Engineering SDLC (`ES`) → Requirements Engineering (`RE`). |

Each row represents one document-project pair. The proposed relationship permits a document to be associated with multiple projects and a project to include multiple documents. Enforce uniqueness of the `(document_id, project_id)` pair if supported by EDM.

### 6.7 Hash Indexes, Relationships, and Governance
Model a **global unique index or equivalent uniqueness constraint** on `Document.sha256`. Model a non-unique index on `DocumentInUpload.sha256` to find in-flight records and coordinate concurrent uploads. Verify the EDM feature needed for both through `manage-edm`.

One `Project` can be associated with many `Document` records through `DocumentProject`; one document can map to multiple projects. One `Document` can have multiple `DocumentSourceLocation` records, and each source location may optionally reference the project context where that path was observed. `Document` has no `project_id` attribute: document-level project associations are represented by `DocumentProject`. `DocumentInUpload` is temporary and links to the canonical `Document` after it is created or matched. These relationships cross module schemas, so verify cross-schema foreign-key support before modeling.

#### Live Deployment Status

Read-only inspection of the live `avrig-db` PostgreSQL catalog confirmed the following physical tables are deployed. The EDM entity names remain `Project`, `Document`, `DocumentInUpload`, `DocumentSourceLocation`, and `DocumentProject`; the physical table names use lowercase snake_case:

| EDM entity | Deployed physical table |
|---|---|
| `Project` | `re.project` |
| `Document` | `km.document` |
| `DocumentInUpload` | `km.document_in_upload` |
| `DocumentSourceLocation` | `km.document_source_location` |
| `DocumentProject` | `km.document_project` |

All five tables had zero rows at the time of inspection. The deployed schema includes the expected foreign keys and the unique constraint on `km.document.sha256`. The non-unique lookup index on `km.document_in_upload.sha256` and composite uniqueness on `(document_id, project_id)` in `km.document_project` are not present. The generated DDL files under `.edm/ddl/0.0.1/` use quoted PascalCase table names, so they do not reflect the physical table names observed in the live database.

This status was checked through a read-only database connection. The inspection did not determine when or by whom the physical objects were deployed. Continue to use `manage-edm` for EDM changes. Any future physical database deployment or migration requires separate explicit approval and verified write access.

---

## 7. Rauthy OIDC Authentication Architecture

The API and CLI integrate with Rauthy IAM (`https://iam.avrig.ai/auth/v1/`):

### 7.1 Interactive User Authentication
- Flow: OAuth 2.1 Authorization Code grant with PKCE (`S256`).
- Scopes: `openid`, `profile`, `email`, `documents:read`, `documents:write`.
- Tokens: Rauthy issues EdDSA / RS256 signed access tokens. The client attaches `Authorization: Bearer <token>` to requests.

### 7.2 Service-to-Service Ingestor Authentication
- Flow: OAuth 2.1 Client Credentials grant (`client_credentials`).
- Client: `avrig-watcher-agent`.
- Secret Storage: Store the Rauthy client secret in TOML only as Vault Transit ciphertext. The runtime decrypts it through Vault using the Transit mount and key configured in TOML. The Vault authentication credential must come from a protected local agent or machine identity, never plaintext TOML.

### 7.3 Vault-Encrypted TOML Secrets
- Secret values, including database credentials and confidential OAuth client secrets, may be carried in TOML as Vault Transit ciphertext.
- TOML contains the Vault address, Transit mount/key reference, and ciphertext. It never contains plaintext secret values or a Vault access token.
- The Windows or Linux process must have a secure machine identity or local Vault Agent path for Transit decryption. Select and verify the supported authentication method for each platform before implementation.
- Configuration settings otherwise remain in TOML. Do not add environment-variable configuration overrides.

### 7.4 Server-Side Token Verification Middleware
- Discovers endpoints via `https://iam.avrig.ai/auth/v1/.well-known/openid-configuration`.
- Retrieves public keys from `https://iam.avrig.ai/auth/v1/oidc/certs` and caches JWKS keys in memory.
- Validates signature, issuer (`https://iam.avrig.ai/auth/v1/`), audience (`avrig-api`), and expiration.
- Extracts roles and scopes to enforce route-level authorization.

---

## 8. Implementation Steps & Work Breakdown

```text
Phase 1: Foundation & Shared Types (avrig-lib)
  ├── 1.1 Ingestion and document domain models (document, temporary upload, source and project mappings)
  ├── 1.2 Storage driver extensions (streaming S3 Garage upload)
  ├── 1.3 Streaming SHA-256 calculation utility
  └── 1.4 EDM modeling alignment (manage-edm schema definition; no direct DB execution)

Phase 2: Configuration & CLI Engine (avrig-bin)
  ├── 2.1 Multi-file TOML discovery and merging logic
  ├── 2.2 Clap command tree (serve, watch, run)
  └── 2.3 Coordinated Tokio runtime and cancellation tokens

Phase 3: Server Implementation (avrig-api)
  ├── 3.1 Axum REST routes (/api/v1/documents/*, /api/v1/search/*)
  ├── 3.2 Rauthy JWT/JWKS verification middleware & user extraction
  └── 3.3 Garage S3 upload and metadata persistence handlers

Phase 4: Watcher Agent Implementation (avrig-watcher)
  ├── 4.1 Cross-platform notify monitor loop
  ├── 4.2 Pre-flight hash checking client
  └── 4.3 Multipart upload client with automatic token refresh

Phase 5: Verification & End-to-End Validation
  ├── 5.1 Unit tests for hash streaming and TOML merging
  ├── 5.2 Multi-role concurrency tests (server + watch in one process)
  └── 5.3 Live file drop tests, provenance verification, and deduplication
```

---

## 9. Verification & Acceptance Checklist

- [ ] Single executable builds successfully on Windows (`avrig.exe`) and Linux (`avrig`).
- [ ] Execution without flags automatically locates and merges `<exe_dir>/config/*.toml`.
- [ ] Specifying an external `--config <PATH>` correctly loads the target configuration.
- [ ] `avrig run` launches both the HTTP server and folder watcher when `roles = ["server", "watcher"]` is set in TOML.
- [ ] Rauthy OIDC authentication successfully validates bearer tokens against `https://iam.avrig.ai/auth/v1/`.
- [ ] Uploaded documents preserve source locations in `DocumentSourceLocation`; project associations are represented by `DocumentProject`.
- [ ] The authenticated actor is recorded through the standard `created_by` field where identity type mapping is compatible; no custom `uploaded_by_*` fields are added.
- [ ] Canonical `Document.sha256` is globally unique; `DocumentInUpload.sha256` supports efficient in-flight lookup.
- [ ] Successful processing deletes `DocumentInUpload`; failed records follow the defined retry and retention policy.
- [ ] All secret values in TOML are Vault Transit ciphertext; Vault authentication itself is provided by a protected local identity or agent.
- [ ] Dropping a document into a watched folder triggers hash calculation and uploads when the file is new.
- [ ] Re-saving or discovering unchanged content skips binary upload while recording any new source location and project association.
- [ ] Concurrent uploads with identical content resolve to one globally unique `Document` and do not lose source or project mappings.
- [ ] All API routes function cleanly under `/api/v1/` without any `km` prefix.
- [ ] Ctrl+C / SIGTERM gracefully cancels all active roles without orphaned file handles or socket leaks.
