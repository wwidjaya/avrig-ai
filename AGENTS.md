# AGENTS.md

This file describes what avrig-ai is and how it is built. It does not describe the delivery workflow: plan identity, numbering, branches, candidate tags, and releases are governed by the global `AGENTS.md` and by `.opencode/agents/Architect.md`, and repeating them here would create a second copy that drifts.

## What This Project Is

avrig-ai is an agentic engineering system for system development. It models a virtual company in which human actors and AI agents plan, coordinate, and carry out engineering work under shared governance. The engineering value is not autonomy for its own sake: it is that work becomes organized, observable, and traceable as it progresses.

## Documentation & Knowledge Base

Specifications, architecture designs, and discovery research live in the central Obsidian Vault rather than in this repository. Read them before designing a feature, because the code is the implementation of those documents rather than an independent source of truth.

- **Vault project path:** `D:\Cloud\OneDrive\AI\Personal\vault\02-projects\avrig-ai\`
- **Project index:** `02-projects/avrig-ai/_index.md`
- **System architecture:** `02-projects/avrig-ai/design/System-Architecture.md`
- **Technology architecture:** `02-projects/avrig-ai/design/Technology-Architecture.md`
- **Knowledge management:** `02-projects/avrig-ai/design/Knowledge-Management.md`
- **Dev infrastructure baseline:** `02-projects/avrig-ai/infra/Infrastructure.md`
- **Discovery and capability baselines:** `02-projects/avrig-ai/discovery/`

## Environment

The OpenCode configuration directory is `$env:OPENCODE_CONFIG_DIR` (`D:\Cloud\OneDrive\AI\Agentic`). Global and shared OpenCode artifacts such as `.opencode/` definitions, agents, skills, and configuration are anchored there, not in this repository.

## Workspace Layout

A single Cargo workspace at the root covers Rust, and a pnpm workspace covers TypeScript. `pnpm-workspace.yaml` globs `apps/*` and `packages/*`.

Rust members, from `Cargo.toml`:

| Member | Purpose |
|---|---|
| `crates/avrig-harness` | The core crate. OAuth and provider clients, the SDLC domain model, governance guardrails, and the office event surface. |
| `crates/avrig-sdlc` | SDLC lifecycle and coordination primitives. |
| `crates/avatar-runtime` | Deterministic avatar state model, outfit resolver, and manifest loader for the PET companion. |
| `avatar/pet-desktop` | Bevy-based desktop PET companion binary. |
| `apps/desktop/src-tauri` | Tauri desktop shell. |
| `test` | Playwright browser harness. |
| `claude` | Claude integration crate. |

The TypeScript side has three apps (`web`, `desktop`, `mobile`) and three shared packages (`api-client`, `types`, `ui`).

Several directories under `crates/` exist but are empty placeholders with no `Cargo.toml` and no source: `actor`, `agent-runtime`, `domain`, `event-bus`, `graph`, `iam`, `memory`, `office-api`, `office-core`, `policy`, `repository`, `tools`. They signal intended decomposition, not implemented modules. Do not describe them as features, and do not cite them as dependencies, because a build referencing a crate that does not exist fails.

## Design Invariants

These are the properties the code is built to preserve. They are the project's actual design commitments, and a change that breaks one is a design change, not a refactor.

**Human authority over approval.** `Guardrail::check_action` in `crates/avrig-harness/src/governance/policy.rs` rejects `ActionType::ApproveArtifact` when the caller is an agent, with the message that only human authority can approve candidates. An agent may generate, and an agent may execute a mutating tool, but that path logs a warning because an audit record is required. Approval is never an agent action.

**Epistemic status is explicit, not implied.** Every claim carries an `EpistemicStatus` (`domain/epistemic.rs`): `AuthoritativeRequirement`, `ApprovedBaseline`, `ExistingPractice`, `BestPractice`, `AgentInference`, or `AssumptionOrUnknown`. `is_authoritative()` is true only for the first two, and `is_agent_generated()` only for the last two. Code that treats agent inference as a requirement defeats the purpose of the model.

**Artifacts move through a defined lifecycle.** `CandidateStatus` (`domain/artifact.rs`) is `Draft`, `Candidate`, `ValidatedCandidate`, `ReviewedCandidate`, `Approved`, `Superseded`, or `Rejected`. `is_terminal()` is true only for `Superseded` and `Rejected`, and `is_approved()` only for `Approved`. Do not invent intermediate states in a caller; extend the enum and its predicates together.

**Traceability is a first-class relation.** `RelationType` (`domain/traceability.rs`) names the permitted links: `DerivedFrom`, `Satisfies`, `ConstrainedBy`, `RealizedBy`, `ImplementedBy`, `VerifiedBy`, `DeployedAs`. A `TraceabilityLink` pins both `source_version` and `target_version`, so a link is a statement about specific versions rather than about artifacts in general.

## Implementation Standards

**Build and deploy.** `make build` in `avrig-api` compiles both targets, a Windows PE binary (`avrig.exe`) and a Linux ELF binary (`avrig`), embedding `apps/web/dist`. `make deploy` in `avrig-api` deploys to both `D:\avrig\` and `/opt/avrig/avrig`. Version bumping is `make bump-version VERSION=<X.Y.Z>` in `avrig-ai`; the positional form fails because the target requires the named variable.

**Codebase exploration.** Use `graphify` (`D:\miniconda3\envs\kb\Scripts\graphify.exe query "<question>"`) or the `explore` subagent to inspect structure, symbols, and cross-module relationships. Recursive `grep` for discovery is prohibited; it is permitted only for a pinpoint edit at a known path.

**Delegation.** Work routes to the owning specialist rather than being done inline: `be` for the Rust runtime and HTTP surfaces, `fe` for web, desktop, and mobile UI, `edm` for schema and migrations, `Infra` for services, reverse proxy, and certificates, `tester` for test matrices and live browser verification, `analyst` for plan audit, `km` for retrospectives, `explore` for codebase discovery.

**Frontend.** Any HTML, CSS, or client-side JavaScript work requires the `modern-web-guidance` skill before designing or writing UI code, invoked as `npx modern-web-guidance@latest search "<query>"` then `retrieve <ids>`. It does not apply to Rust, SQL, infrastructure, or tooling.

## Development Environment

`.env.development` is the local baseline and it is the source of truth for ports and services rather than an example to improvise around:

- PostgreSQL at `127.0.0.1:5432`, database `avrig_km_dev`, user `avrig`.
- S3-compatible object storage (Garage) at `127.0.0.1:3900`, region `garage`, buckets `avrig-platform-knowledge` and `avrig-project-artifacts`.
- HashiCorp Vault at `https://vault.avrig.ai`, which also serves as the Vault Agent proxy address.
- ONNX models under `/home/avrig/.cache/avrig/models`.

IAM is Rauthy, reverse proxied by nginx on the `avrig-ai` WSL instance; `infra/iam.avrig.ai.conf` is the vhost and `infra/update_rauthy_client.sh` updates the client registration. TLS certificates come from the Vault PKI rather than being generated locally.

## Testing

Authenticated suites read `.secrets/test_token.json`, which carries a short lifetime and must be refreshed rather than assumed valid. The Playwright harness lives in `test/` and resolves `@playwright/test` only from that directory, so run browser checks with that as the working directory.

## Writing Rules

- Never use an em-dash (U+2014) or an en-dash (U+2013). Use a colon, comma, parentheses, or a separate sentence.
- When writing Vault notes, follow the `write-vault` skill: valid YAML frontmatter, a single `#` H1 matching the frontmatter title verbatim, blank lines around `---` separators, and escaped table pipes (`\|`).
