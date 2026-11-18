# SemVer 2.0 Capability Implementation Plan

## 1. Goals and Objectives
* **Measurable Outcome 1:** Strict SemVer 2.0.0 compliance (MAJOR.MINOR.PATCH with optional prerelease and build metadata) stored directly within the compiled avrig binary across both Windows PE (avrig.exe) and Linux ELF (avrig) builds.
* **Measurable Outcome 2:** CLI verification supporting standard flags (avrig --version, avrig -V) and extended verbose info (avrig --version --verbose).
* **Measurable Outcome 3:** Automated bump automation via Makefile targets (make bump-patch, make bump-minor, make bump-major, make bump-version VERSION=X.Y.Z) and native PowerShell scripts (scripts/bump-version.ps1) synchronizing root Cargo.toml, Cargo.lock, and apps/web/package.json in lockstep.
* **Measurable Outcome 4:** Dedicated backend API endpoint GET /api/v1/version returning structured version, git commit SHA, build timestamp, and target architecture.
* **Measurable Outcome 5:** Frontend UI presentation featuring a telemetry version badge in the sidebar footer and an interactive System Info / About dialog with client-server synchronization checks.

---

## 2. Key Detailed Design

### Target Program Files
* `Cargo.toml` (Edited: Workspace root package version authoritative source).
* `gateway/Cargo.toml` (Edited: Inherit workspace package version, declare build script).
* `gateway/build.rs` (New: Compile-time extraction of git commit, build timestamp, target triple with fail-safe fallbacks).
* `gateway/src/version.rs` (New: VersionInfo structure and immutable version constants).
* `gateway/src/main.rs` (Edited: Mount GET /api/v1/version route and wire version module into CLI and router).
* `Makefile` (Edited: Add bump and version-sync targets).
* `scripts/bump-version.ps1` (New: Cross-platform PowerShell manifest updater with SemVer 2.0 regex validation).
* `scripts/bump-version.sh` (New: POSIX bash equivalent for Linux and WSL).
* `apps/web/package.json` (Edited: Synchronized version field).
* `apps/web/vite.config.ts` (Edited: Define `__APP_VERSION__` compile constant).
* `apps/web/src/shared/types/version.ts` (New: TypeScript interfaces for version payload).
* `apps/web/src/shell/CommandCenterLayout.tsx` (Edited: Render version badge in telemetry footer).
* `apps/web/src/shared/components/SystemInfoDialog.tsx` (New: Modal dialog showing version details, git commit, target architecture, and sync status).

### Program Design & Architecture
1. **Binary Metadata (`gateway/build.rs`):**
   * Uses `cargo:rustc-env=` directives and `$OUT_DIR/version_info.rs` generation.
   * Emits `cargo:rerun-if-changed=.git/HEAD` and `cargo:rerun-if-changed=.git/index` (when `.git` is present).
   * Fail-Safe Fallbacks: Zero `.unwrap()` calls on git commands. Defaults to `unknown`, `detached`, or environment variables (`AVRIG_GIT_SHA`) if Git CLI or `.git` directory is unavailable.
2. **Backend API (`GET /api/v1/version`):**
   * Serves public JSON payload:
     ```json
     {
       "semver": "0.1.0",
       "major": 0,
       "minor": 1,
       "patch": 0,
       "prerelease": null,
       "build_metadata": null,
       "commit_sha": "b38f2a1b9...",
       "commit_short_sha": "b38f2a1",
       "build_timestamp": "2026-11-18T10:15:30Z",
       "target_triple": "x86_64-pc-windows-msvc",
       "dirty": false
     }
     ```
3. **Frontend UI Presentation:**
   * **Sidebar Footer:** Displays `v0.1.0` badge next to telemetry status with green indicator.
   * **About / System Info Modal:** Triggered on click; shows detailed commit SHA, architecture, and alerts if client asset version diverges from backend runtime.

---

## 3. Parallel Execution Plan

```
Phase 1: Design & Approval (Plan Agent) [COMPLETED]
Phase 2: Quality Gate (Tester & Analyst) [COMPLETED]
Phase 3: Concurrent Implementation
  |-- Stream A (Assignee: be): gateway/build.rs, gateway/src/version.rs, gateway/src/main.rs, Makefile, scripts/bump-version.ps1, scripts/bump-version.sh
  |-- Stream B (Assignee: fe): apps/web/package.json, apps/web/vite.config.ts, apps/web/src/shared/types/version.ts, apps/web/src/shell/CommandCenterLayout.tsx, apps/web/src/shared/components/SystemInfoDialog.tsx
Phase 4: Workspace Build Gate (Assignee: build)
  |-- cargo check --workspace & pnpm build
  |-- make build (Dual Windows PE & Linux ELF compilation)
Phase 5: Automated Verification (Assignee: tester)
  |-- Execute Test Specification Matrix (SEM-BIN-*, SEM-AUT-*, SEM-API-*, SEM-UI-*, SEM-XPF-*)
Phase 6: Infrastructure & Deployment (Assignee: Infra)
  |-- make deploy (Windows D:\avrig and Linux /opt/avrig) & live smoke check
Phase 7: Review & Knowledge Management (Assignee: km)
  |-- Vault retrospective and plan archive
```

---

## 4. Test Specification and Validation Matrix (Authored by tester)

| Test ID | Category | Description | Input / Precondition | Expected Outcome | Automation Method |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEM-BIN-001** | Binary / CLI | Display basic SemVer version string | Run `avrig.exe -V` and `--version` | Outputs `avrig x.y.z` matching workspace `Cargo.toml`; exit code 0 | PowerShell / Bash assert regex: `^avrig \d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$` |
| **SEM-BIN-002** | Binary / Build Info | Embed and output build metadata | Run `avrig --version --verbose` or `avrig version` | Output includes SemVer, Git commit SHA, ISO-8601 build timestamp, target triple | CLI command test capturing stdout |
| **SEM-BIN-003** | Binary / Build Script | Verification of `build.rs` compile-time capture | Dirty git repo vs clean git tree vs missing `.git` | Clean fallback or dirty marker without failing compilation | Cargo build test with mocked git environment |
| **SEM-AUT-001** | Automation / Make | Automated patch increment | `make bump-patch` | `Cargo.toml`, `Cargo.lock`, `package.json` incremented from `1.2.3` to `1.2.4` | Script parsing manifests and running `git diff --name-only` |
| **SEM-AUT-002** | Automation / Make | Automated minor increment | `make bump-minor` | Version becomes `1.3.0` across all manifests | Assert manifests match `1.3.0` |
| **SEM-AUT-003** | Automation / Make | Automated major increment | `make bump-major` | Version becomes `2.0.0` across all manifests | Assert manifests match `2.0.0` |
| **SEM-AUT-004** | Automation / Make | Explicit version assignment | `make bump-version VERSION=2.1.0-rc.1` | Manifests adopt target version string; exit code 0 | Run target with custom version; verify file contents |
| **SEM-AUT-005** | Automation / Validation | Rejection of non-compliant SemVer strings | `make bump-version VERSION=invalid-1.0` | Fails with non-zero exit code; descriptive error; manifests untouched | Shell invocation asserting non-zero exit code |
| **SEM-AUT-006** | Automation / Sync | Multi-file synchronization integrity check | `make check-version-sync` | Verifies `Cargo.toml`, `Cargo.lock`, `package.json` match; fails on divergence | Workspace manifest check script |
| **SEM-API-001** | Backend API | Dedicated version endpoint schema | `GET /api/v1/version` | HTTP 200 OK; JSON payload with `semver`, `commit_sha`, `build_timestamp`, `target_triple` | Automated API test with JSON Schema validation |
| **SEM-API-002** | Backend API | Health endpoint version attribute | `GET /api/v1/health` | HTTP 200 OK; response includes `version` attribute | Automated test parsing `/api/v1/health` response body |
| **SEM-API-003** | Backend API | Unauthenticated and authenticated consistency | `GET /api/v1/version` with and without bearer token | Returns HTTP 200 with identical payload under both conditions | HTTP integration test with `.secrets/test_token.json` |
| **SEM-UI-001** | Frontend UI | Sidebar footer version badge display | Web UI loaded in browser | Sidebar footer renders version tag (e.g. `v0.1.0`) | Playwright test checking `[data-testid="sidebar-version-badge"]` |
| **SEM-UI-002** | Frontend UI | System Info / About dialog inspection | Click version badge in sidebar | Modal dialog opens showing version, commit SHA, build date, architecture | Playwright automation asserting dialog fields |
| **SEM-UI-003** | Frontend UI | Client-Server version mismatch indicator | Client `1.2.0` connected to backend `1.3.0` | UI displays non-blocking update notification | Playwright test injecting mocked `/api/v1/version` response |
| **SEM-XPF-001** | Cross-Platform | Windows PE binary verification | Run `.\target\release\avrig.exe --version` | Successfully executes; output matches SemVer string | PowerShell execution script |
| **SEM-XPF-002** | Cross-Platform | Linux ELF binary verification | Run `wsl -d avrig-ai -- /opt/avrig/avrig --version` | Successfully executes; ELF binary returns matching SemVer string | WSL Bash execution script |
| **SEM-XPF-003** | Cross-Platform | Dual binary parity check | Compare Windows PE and Linux ELF versions | Both binaries report identical SemVer version numbers | Automated comparison script |

---

## 5. Review Findings and Recommendations (Audited by analyst)
* **Single Source of Truth:** Workspace root `Cargo.toml` manages `[workspace.package.version]` while sub-crates inherit it. The bump targets update the root manifest and run `cargo check --workspace` to update `Cargo.lock`.
* **Rerun Triggers:** `build.rs` must specify `cargo:rerun-if-changed=.git/HEAD` to avoid re-triggering builds unnecessarily.
* **Build Fallbacks:** If `.git` is absent (such as in headless or tarball builds), `build.rs` must gracefully default to `unknown` without throwing a compilation error or invoking panics.
* **Target Detection:** Avoid spawning `rustc` subprocesses in `build.rs`; read standard environment variable `std::env::var("TARGET")`.
* **Zero Overhead Endpoints:** Since version metadata is immutable per binary build, return compile-time constants without taking locks.
* **Dual Scripting:** Bumping automation is supported via both PowerShell (`scripts/bump-version.ps1`) and POSIX shell (`scripts/bump-version.sh`) alongside Makefile targets.
