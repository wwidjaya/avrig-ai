# AGENTS.md

## Project Documentation & Knowledge Base

Project specifications, architecture designs, and discovery research for **avrig-ai** are maintained in the central Obsidian Vault rather than inside this repository:

- **Vault Project Path:** `D:\Cloud\OneDrive\AI\Personal\vault\02-projects\avrig-ai\`
- **Project Index:** `02-projects/avrig-ai/_index.md`
- **System Architecture:** `02-projects/avrig-ai/design/System-Architecture.md`
- **Technology Architecture:** `02-projects/avrig-ai/design/Technology-Architecture.md`
- **Knowledge Management (`[KM]`):** `02-projects/avrig-ai/design/Knowledge-Management.md`
- **Dev Infrastructure Baseline:** `02-projects/avrig-ai/infra/Infrastructure.md`
- **Task Plans & Workflows:** `02-projects/avrig-ai/plans/` (Active plans) and `02-projects/avrig-ai/plans/done/` (Completed/archived plans)
- **Discovery & Capability Baselines:** `02-projects/avrig-ai/discovery/`

## Environment & Directories

The OpenCode configuration directory is located at `$env:OPENCODE_CONFIG_DIR` (`D:\Cloud\OneDrive\AI\Agentic`). Global and shared OpenCode artifacts such as `.opencode/` definitions, agents, skills, and configuration are anchored to this directory.

## Guidelines for Agents

1. **Authoritative Architecture Source:** Always consult the design and discovery documents in the Vault path above when designing or implementing SDLC, Office OS, or harness features.
2. **Task Planning & Execution Workflow:**
   - Active, multi-step task plans must be maintained in the Vault's `plans/` folder (e.g., `02-projects/avrig-ai/plans/YYYY-MM-DD-<task-name>.md`).
   - When a plan has been fully executed and verified, move it into the `plans/done/` subfolder and update its frontmatter status to `status: completed`.
   - Before executing non-trivial tasks, review any relevant plans in `plans/` or historical executions in `plans/done/`.
3. **Writing & Modification Rules:** When creating or editing notes within the Vault, adhere strictly to the `write-vault` skill guidelines:
   - Include valid YAML frontmatter.
   - Maintain a single `#` H1 heading matching the frontmatter title verbatim.
   - Do not use em-dashes (replace with colons, commas, or parentheses).
   - Enclose `---` section separators in blank lines.
   - Normalize paragraph flow and escape markdown table pipes (`\|`).
4. **Database Schema Design & Management:**
   - Database schemas (relational tables, columns, indexes, relationships, and migrations) must NOT be designed or modified ad-hoc directly in repository code or raw SQL scripts.
   - All database schemas must be modeled, designed, and managed separately using the `manage-edm` remote skill (`$env:OPENCODE_CONFIG_DIR/shared/skills/manage-edm`).
   - Consult `manage-edm` workflows for Enterprise Data Models (EDM), entity definitions, DDL generation, ERD visualizations, schema validations, and database connection profiles.
