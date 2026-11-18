---
name: manage-edm
description: "Manage and explore Enterprise Data Models (EDM), ERDs, and databases. Use for EDM entities, tables, columns, relationships, schemas, domains, modules, DDL, sample data, templates, database connections, checking/testing DB connections, querying/exploring live databases, and ERD generation/export. Supports PostgreSQL and other configured databases via Harlequin."
---

# manage-edm

Manage EDM schemas and **database connections**.

## Write-Access & Planning Gate

Updates or modifications to EDM schemas, entities, domains, modules, templates, or live databases are strictly prohibited unless the agent has verified write access and explicit user authorization.

1. **Verify Write Access:** Check and confirm that the agent possesses authorized write permissions on the target EDM system or database before executing any mutating command (`add-*`, `modify-*`, `delete-*`, `move`, `apply-template`, `unapply-template`, `init`, `publish`, `deploy`).
2. **Planning-Only Mode:** If write access is not present, unverified, or not explicitly granted, the agent MUST restrict its operation strictly to planning, schema design proposals, or read-only inspection. No state-changing commands or DDL migrations may be dispatched.
3. **Database Deployments:** Creating or deploying physical database objects (`deploy`) requires separate, explicit confirmation and verified administrative credentials on the target database connection. Without verified write access, only planning and DDL preview are permitted.

## Entity Naming Style Configuration

Before creating, renaming, modifying, or generating DDL for EDM entities, read the EDM-wide `naming_style_flag` setting from the `config` table in `.edm/data/<project>-edm.db` and follow it consistently for entity/table names and entity-owned column names:

* `S` (default): `snake_case` (e.g. `document_project`, `project_code`).
* `C`: `camelCase` (e.g. `documentProject`, `projectCode`).

If the `config` table or `naming_style_flag` row is missing in `.edm/data/<project>-edm.db`, default to `S` (`snake_case`). Do not silently rename existing entities when the setting changes: renames must be explicit and coordinated with database migrations.

Use this skill for:

* check/test database connection
* connect to or explore a database
* inspect database schemas/tables
* entities, columns, relationships, ERD
* domains/modules
* CRUD schema definitions
* DDL/sample data
* entity/column templates
* ERD view/export

## Commands

```text
# Database connections
/manage-edm add-conn <name> [--type <type>] [--url <url>] [--auth-token <password>] [--login-email <email>] [--login-password <password>]
/manage-edm read-conn <name> [--show-password]
/manage-edm modify-conn <name> [...]
/manage-edm delete-conn <name>
/manage-edm test-db-conn <name>
/manage-edm test-conn <name> [--org <org>]
/manage-edm explore <conn> [--dry-run]

# Entities
/manage-edm add-entity <name> --domain <d> --module <m> [--column <col> [--column <col>]...] [--description <desc>] [--schema <s>]
/manage-edm read <name> --domain <d> --module <m>
/manage-edm modify-entity <name> --domain <d> --module <m> [--add-column <col>]... [--after <col>] [--move-col <col>] [--drop-column <col>]... [--set-type <col> <type>] [--set-col-desc <col> <desc>]... [--set-nullable <col>]... [--set-not-null <col>]... [--set-unique <col>]... [--add-fk <col> <ref_entity> <ref_col> [<fk_name>]]... [--drop-fk <fk_name>]... [--description <desc>] [--schema <s>]
/manage-edm delete-entity <name> --domain <d> --module <m>
/manage-edm move <name> --from-domain <d> --from-module <m> --to-domain <d> --to-module <m>

# Domains / modules
/manage-edm add-domain <name> [...]
/manage-edm read-domain <name>
/manage-edm modify-domain <name> [--title <t>] [--description <desc>] [--connection <name|id>] [--code <new-code>] [--display-order <n>]
/manage-edm delete-domain <name> [--force]
/manage-edm register-domain <name> --code <code> [--connection <name|id>] [--description <desc>] [--display-order <n>] [--update]
/manage-edm read-domains

/manage-edm add-module <name> --domain <d> [--repo-name <r>] [...]
/manage-edm read-module <name> --domain <d>
/manage-edm modify-module <name> [--domain <d>] [--title <t>] [--schema <s>] [--repo-name <r>] [--description <desc>] [--code <new-code>] [--parent-module <code|name|none>] [--display-order <n>]
/manage-edm delete-module <name> [--domain <d>] [--force]
/manage-edm register-module <name> --domain <d> --code <code> [--schema <s>] [--repo-name <r>] [--description <desc>] [--parent-module <code|name>] [--display-order <n>] [--update]
/manage-edm read-modules [--domain <d>]

`--parent-module` names the parent module (sub/sub-sub hierarchy); pass `none` on `modify-module` to clear it.

# Data types
/manage-edm register-data-type <name> --code <code> [--category <cat>] [--aliases <aliases>] [--connection <name|id>] [--description <desc>] [--update]
/manage-edm read-data-types [--category <cat>]
/manage-edm modify-data-type <code> [...]
/manage-edm delete-data-type <code>

# Templates
/manage-edm add-template <name> --type entity|column [--data-type <type>] [...]
/manage-edm add-column-domain <name> --data-type <type> [--title <t>] [--description <desc>]
/manage-edm read-template <name> --type entity|column
/manage-edm read-templates [--type entity|column|all]
/manage-edm read-column-domains
/manage-edm read-entity-domains
/manage-edm modify-template <name> --type entity|column [...]
/manage-edm delete-template <name> --type entity|column [--force]
/manage-edm apply-template <entity> --domain <d> --module <m> --template <t> --type entity|column [--column <col>]
/manage-edm unapply-template <entity> --domain <d> --module <m> --template <t> --type entity|column

# Note: Column domains define reusable data types (e.g. Money -> decimal(17,2)) rather than
# fixed column names. When applied with `--type column --column <col>`, they assign the data type
# and provenance to the entity's designated column.

# Generate / view / deploy
/manage-edm list
/manage-edm create-project <name> --conn <name> [--org <org>] [--description <d>] [--encoding-version <n>] [--storage-kind local|remote] [--no-schema]
/manage-edm delete-project <name> --conn <name> [--org <org>]
/manage-edm delete-org <name> --conn <azimut-conn> [--email <login-email>] [--password <login-password>] [--force]
/manage-edm add-layout <layout-name> --conn <azimut-conn> [--tables <schema.table> ...] [--color <color>] [--force] [--org <org>] [--project <project>]
/manage-edm sync-layouts --conn <azimut-conn> [--org <org>] [--project <project>]
# Layouts follow the module hierarchy (parent_module_id) without domain-level layouts: a layout is emitted
# for modules (parents and submodules), named by the module name path (e.g. `Data Lakehouse/Overview`, `Data Lakehouse/Bronze`)
# so Azimutt's layout menu renders sub-menus with leaf module names. Parent layouts contain their subtree tables placed
# hierarchically (submodule block beneath its parent block). User-saved positions are preserved.
# Add `--insecure` to publish/sync-layouts/add-layout when the Azimutt server uses an expired/self-signed cert.
/manage-edm set-version [<version>] [--force] [--list]
/manage-edm read-version-history [--version <id|code>] [--table <name>] [--limit <n>]
/manage-edm init [--force]
/manage-edm generate <entity> --domain <d> --module <m>
/manage-edm view [--domain <d>] [--module <m>]
/manage-edm publish --conn <azimut-conn> [--domain <d>] [--module <m>] [--org <org>] [--project <project>] [--source-name <name>] [--force]
# The source is named after the EDM connection (`connection_name`, else its code), so every
# scope publishes into that one shared source; `--source-name` overrides it. Since a scoped
# publish would replace the whole model with just that scope's tables, it is refused unless
# `--force` is passed.
# Creating a source sends the connection taken from the EDM config: `kind`
# (`DatabaseConnection` with the url from the connection payload and its password
# URL-encoded), plus the source name and `enabled`.
# The Azimutt API only accepts `{tables, relations, types}` when updating an existing source
# (`name`/`kind` are rejected), so a source connection can never be changed after creation.
# Publishing warns when the stored connection url differs from the EDM connection; delete the
# source and publish again to recreate it with the current credentials.
# Relations are stored inside one source, so a scoped publish emits its relations anyway even
# when the target table is out of scope (Azimutt keeps such dangling relations).
# Each entity is published with its effective schema: entity override (`entity.schema`),
# else the module schema, else `LOWER(module_code)`.
# Foreign keys record the target entity code only, so the target schema is resolved against
# all entities in the EDM in this order: same schema, unique candidate, unique candidate in
# the same domain, unique non-Data-Lakehouse candidate, then lowest schema name. The rule
# used per relation is tallied in the `relations: <n> (...)` summary line.
# Entities with a description are published with a table comment `{"text": <entity_desc>}`.
/manage-edm deploy --conn <db-conn> [--domain <d>] [--module <m>] [--dry-run]
/manage-edm export-image [--format png|svg] [--domain <d>] [--module <m>]
```

## Deleting an organization

Azimutt's REST API exposes organizations as `only: [:index]`: there is **no**
API endpoint to delete an organization. Deletion only works through the
session-authenticated browser route `DELETE /organizations/:id`, which requires
the logged-in user to be an **Owner** of that organization (an API `auth-token`
is rejected with 403/404).

`delete-org` therefore logs into the Azimutt server with an **Owner account**
(email/password over `POST /login`, CSRF handled automatically) and issues the
browser-route delete under that session.

Credentials precedence: `--email`/`--password` overrides → connection
`login_email`/`login_password` (set via `add-conn`/`modify-conn`, stored
Fernet-encrypted with the rest of the payload, masked by `read-conn`).

Safety: `delete-org` is a **dry run by default**: it prints the actor and the
projects that would be removed and exits. Pass `--force` to actually delete.
Deletion is destructive and cascades: projects, layouts, notes, memos, members,
and access tokens under the organization are removed.

Limitations:

* The account must be an Owner of the target organization.
* Instances that enforce reCAPTCHA on login (`g-recaptcha-response`) cannot be
  automated this way.
* The org is resolved strictly by name/slug/id against the logged-in user's
  organization list; unknown names fail rather than guess.



## Database Exploration

`explore <conn>` loads the configured connection, decrypts credentials, and launches Harlequin.

`explore <conn>` is a launcher, not an inline query: Harlequin always runs in its own mux
tab/pane (a new tab surface inside wmux when running in wmux, a new tab/pane in Luvus when
`LUVUS_ENV` is set, otherwise a new console window on Windows), and the command returns as
soon as that tab is spawned. Use `--dry-run` to print the resolved URL and skip both the
pre-flight and the launch. Note that `--dry-run` prints the URL with the decrypted password
in clear text.

Connections are stored under:

```text
.edm/data/<project>-edm.db (tables `connection`, `domain`, `module`, `data_type`, `version`, `version_history`, `entity_domain`, `column_domain`, `entity`; standard entity domain)
```
* `domain` table links to `connection(id)` via `connection_id` FK.
* `module` table links to `domain(id)` via `domain_id` FK; `schema` column stores the DB schema name (VARCHAR(30), UNIQUE) and falls back to `LOWER(module_code)` where NULL. `parent_module_id` is a self-reference to `module(id)` naming the parent module for sub/sub-sub modules; `read-modules` renders the hierarchy as a tree (module first, then its submodules nested beneath it, then the next module).
* `entity` table links to `module(id)` via `module_id` FK (unique per `module_id` + `entity_code`).
* Bootstrap registries: `init` migrates `.edm/_domains.md` and `.edm/<domain>/_modules.md` into `domain`/`module`, then deletes the md files. Columns: domains `| Code | Name | Description | Order |`; modules `| Code | Name | Description | Schema | Parent | Order |`. `Order` maps to `display_order`; `Parent` (parent module code or name in the same domain) sets `parent_module_id`.
* `data_type` table links to `connection(id)` via `connection_id` FK.
* `version` table stores recorded version history; the current version is the active row (`is_active = 1`).
* `version_history` table stores audit log of all changes (`table_name`, `record_id`, `change_type_flag` C/M/D, `change_detail_desc`, `version_id` right after `id`).
* `version_id` attribute placed right before `is_active` across all object tables (`connection`, `domain`, `module`, `data_type`, `entity_domain`, `column_domain`, `entity`) to track the EDM version of the last mutation.
* `entity_domain` and `column_domain` tables store template definitions (columns/foreign keys stored as JSON).
* `entity` table stores entity columns (with `entity_domain_id`/`column_domain_id` provenance) and foreign keys as JSON; AML/DDL/mermaid are derived on demand in memory.

Credentials are Fernet-encrypted; the key is retrieved from HashiCorp Vault.

## EDM Structure

```text
.edm/
├── data/
│   └── <project>-edm.db
└── ddl/
    └── <version>/
        └── <domain>-<module>-<entity>.sql
```

Entities (columns, foreign keys, template refs) are stored in the SQLite `entity` table; generated DDL lives centrally under `.edm/ddl/<version>/` named `<domain>-<module>-<entity>.sql`. No per-domain/per-module folders and no entity `.md`/`.aml` files are created: domains, modules, data types, and templates are all SQLite-backed.

Column types MUST conform to `data_type` table.

## Invocation

```text
python shared/skills/manage-edm/scripts/manage-edm.py <subcommand> [args...]
```
