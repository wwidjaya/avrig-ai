# AGENTS.md

## Project Documentation & Knowledge Base

Project specifications, architecture designs, and discovery research for **avrig-ai** are maintained in the central Obsidian Vault rather than inside this repository:

- **Vault Project Path:** `D:\Cloud\OneDrive\AI\Personal\vault\02-projects\avrig-ai\`
- **Project Index:** `02-projects/avrig-ai/_index.md`
- **System Architecture:** `02-projects/avrig-ai/design/System-Architecture.md`
- **Technology Architecture:** `02-projects/avrig-ai/design/Technology-Architecture.md`
- **Knowledge Management (`[KM]`):** `02-projects/avrig-ai/design/Knowledge-Management.md`
- **Dev Infrastructure Baseline:** `02-projects/avrig-ai/infra/Infrastructure.md`
- **Task Plans & Workflows:** `plans/` (Active project-root plans) and `plans/done/` (Completed/archived plans)
- **Discovery & Capability Baselines:** `02-projects/avrig-ai/discovery/`

## Environment & Directories

The OpenCode configuration directory is located at `$env:OPENCODE_CONFIG_DIR` (`D:\Cloud\OneDrive\AI\Agentic`). Global and shared OpenCode artifacts such as `.opencode/` definitions, agents, skills, and configuration are anchored to this directory.

## Project Guidelines

1. **Authoritative Architecture Source:** Always consult the design and discovery documents in the Vault path above when designing or implementing SDLC, Office OS, or harness features.
2. **Writing & Modification Rules:** When creating or editing notes within the Vault, adhere strictly to the `write-vault` skill guidelines:
   - Include valid YAML frontmatter.
   - Maintain a single `#` H1 heading matching the frontmatter title verbatim.
   - Do not use em-dashes (replace with colons, commas, or parentheses).
   - Enclose `---` section separators in blank lines.
   - Normalize paragraph flow and escape markdown table pipes (`\|`).
3. **Subagent Delegation & Planning:** Follow the global subagent delegation policy (`edm`, `Infra`, `fe`, `be`, `tester`, `analyst`, `km`, `explore`). Primary agents must strictly delegate implementation, exploration, testing, and infrastructure work to their dedicated subagents rather than performing domain tasks directly. Follow the project-root plan workflow in `$env:OPENCODE_CONFIG_DIR/.opencode/agents/plan.md`.
   - **Infra Agent Specialization**: Owns development infrastructure, systemd services (`avrig.service`, `rauthy.service`, `vault.service`), reverse proxy configurations, and IAM management via the `manage-rauthy` and `manage-nginx` skills.
4. **Build & Deployment Standards (Dual Windows & Linux ELF):**
   - The unified runtime service builds both a Windows PE binary (`avrig.exe`) and a Linux ELF binary (`avrig`) embedding `apps/web/dist`.
   - Always run `make build` in `avrig-api` to compile both targets with fresh frontend assets.
   - Run `make deploy` in `avrig-api` to deploy to both Windows (`D:\avrig\`) and Linux/WSL (`/opt/avrig/avrig`).
5. **Codebase Exploration & Knowledge Graph (graphify > grep):**
   - **MANDATORY:** Always use `graphify` (`D:\miniconda3\envs\kb\Scripts\graphify.exe query "<question>"`) or dispatch the `explore` subagent (`agent: "explore"`) to inspect and understand codebase structures, components, functions, and cross-module relationships.
   - Recursive or directory-wide `grep` searches for exploration or discovery are strictly prohibited across all subagents.
5. **Testing & Token Cache Workflow:**
   - Active plans must specify clear, measurable `## Goals and Objectives`.
   - `tester` subagent must check or prepare `.secrets/test_token.json` before running authenticated test suites across iterations.
   - At the conclusion of a verification session, `tester` asks the `analyst` subagent to audit achievement of the plan's goals and record findings under `## Review Findings`.
6. **Release & Versioning Policy (Mandatory):**
   - **Automatic bump on success:** whenever a test run finishes successfully (all tests PASS), the version MUST be incremented per Semantic Versioning 2.0.0 before the session concludes: `patch` for fixes and refactors, `minor` for new backward-compatible capabilities, `major` for breaking changes.
   - **Bump mechanics:** run `make release-patch`, `make release-minor`, or `make release-major` in `avrig-api` (or `avrig-ai`). The release script (`avrig-ai/scripts/release.ps1`) validates SemVer 2.0, synchronizes `avrig-ai/Cargo.toml`, `avrig-ai/apps/web/package.json`, and `avrig-api/Cargo.toml`, refreshes lockfiles, commits, tags, and pushes. Bump-only variants remain available via `make bump-*` and `make check-version-sync` in `avrig-ai`.
   - **Tag and publish:** create the annotated Git tag named exactly after the version (`X.Y.Z`, no `v` prefix) and apply it to all four repositories: `avrig-ai`, `avrig-api`, `avrig-lib`, and `avrig-ui`. Commit the version bump, then push the branch and tag to each remote.
   - **Verification:** confirm `git ls-remote --tags origin` lists `X.Y.Z` in all four repositories and report the commit SHA, tag, and branch per repo.
   - The `Build` agent orchestrates bump, tag, and push; `tester` reports the successful verification that triggers the release.
