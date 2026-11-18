# Publishing Policy

## Target

Confluence Cloud at `massiveinonvasi.atlassian.net`, space `Composync`.

## Safety invariants

- **No delete.** The connector has no delete operation. To remove a page, ask a
  human to delete it via the Confluence web UI.
- **No permission changes.** The connector never touches page/space permissions.
- **No moves** unless the user explicitly requests a reparent.
- **No attachments** in v1.

## Approval modes

Three modes govern when writes happen:

1. **`draft`** — Render the content but write nothing. Show the resulting
   document to the user for review before any decision to publish.
2. **`review`** — Show:
   ```
   Target:
     Space:    Composync
     Page:     <title> (id <page_id>)
     Operation: UPDATE | APPEND
   Changes:
     + Added section "<heading>"
     ~ Modified paragraph ...
   ```
   Get explicit user confirmation, **then** write. This is the **default for
   `update` and `append`**.
3. **`publish`** — Write directly after showing the plan (space, title, parent).
   This is the **default for `create`**.

## Read → decide → write

Mandatory sequence (see SKILL.md):

1. `search` — locate any existing page with the same purpose.
2. If found: `get` to read current content **and current version**.
3. Decide CREATE vs UPDATE vs APPEND:
   - existing same-purpose page → UPDATE or APPEND (never duplicate create)
   - user wants a small addition → APPEND a new section
   - user explicitly wants replacement → UPDATE with full doc
   - none exists → CREATE
4. Build the structured document model.
5. Render → review the change summary (mode-dependent).
6. Write with the expected version.
7. `get` again → verify content matches intent.
8. **Backfill frontmatter** — write `confluence-page-id` /
   `confluence-page-url` (and `confluence-parent-page-id` /
   `confluence-parent-page-url` for child pages) into the source vault note,
   using the IDs/URLs returned by the write. Update `updated:`.
9. Report the page URL.

## Version conflict handling

Confluence versions every page. Between your `get` and your write a human may
edit the page. The connector detects this and returns:

```json
{"error": "VERSION_CONFLICT", "page_id": "...", "expected_version": 13, "actual_version": 14}
```

On conflict:

1. Re-read the page (`get -page-id N`).
2. Reconcile your intended change with the human's latest content.
3. Retry the write with the fresh version.

Never overwrite blindly on conflict — re-read and reconcile first.

## Verification checklist after a write

- [ ] Page exists / updated (confirmed by `get`)
- [ ] Title correct
- [ ] Version incremented as expected
- [ ] New/changed content present; unrelated content preserved
- [ ] Source note frontmatter backfilled (`confluence-page-id`/`-url` [+ `-parent-*`]), `updated:` refreshed
- [ ] Page URL reported to the user

## Credentials

Stored in `confluence.env` (gitignored) in the skill folder:

```
CONFLUENCE_BASE_URL=...
CONFLUENCE_EMAIL=...
CONFLUENCE_API_TOKEN=...
CONFLUENCE_SPACE_KEY=Composync
```

Never print the API token or commit it to the repository.
