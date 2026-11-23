# Avrig Command Center UI Specification

**Status:** Design proposal  
**Product:** avrig-ai  
**Scope:** Authenticated browser command center across Office, Deliberations, SDLC, Knowledge, and Knowledge Chat  
**Related design:** [Landing and Console Unslop Design](AVRIG-00002/design.md)

## Product job

Help the Founder understand what the engineering organization is doing, inspect the evidence behind its work, and take the human decisions reserved to them. The interface is an inspection bench for a governed engineering company, not a generic AI dashboard.

## Design principles

1. **Evidence before activity.** Show artifacts, versions, provenance, and gate state before agent narration or telemetry.
2. **Human authority is visible.** Agents may propose and execute permitted work. Ratification controls are clearly attributed to the human operator and never appear as agent actions.
3. **One calm frame.** Use a persistent navigation rail, a clear page title, and a focused working area. Reserve strong colour and material for the current gate and approval mark.
4. **Truthful status.** Display only observed connection and domain state. Do not imply that a service, agent, or verification is healthy when that state is unknown.
5. **Inspectable projections.** Office maps, lifecycle boards, and trace paths visualize structured records. Provide a direct route to the underlying record and its version.

## Shared application frame

### Navigation

Use a fixed-width left rail on desktop and a compact, touch-friendly navigation drawer or bottom navigation on narrow screens. Group destinations by user intent:

| Group | Destination | Purpose |
|---|---|---|
| Organization | Office | Workforce, departments, and current work locations |
| Coordination | Deliberations | Meeting rooms, participants, decisions, and outcomes |
| Engineering | SDLC | Canonical lifecycle stages, stage gates, and artifacts |
| Evidence | Knowledge & Trace | Searchable knowledge records and version-pinned relationships |
| Evidence | Knowledge Chat | Ask questions over available knowledge and inspect citations |

Navigation labels remain readable without module abbreviations. The active destination uses a quiet surface and a slim leading marker. Module codes belong in page content where they identify an actual record.

### Header

Each destination has a page title, one sentence describing its current purpose, and page-specific actions. The global header contains the current operator and a compact connection indicator only when connection state is available. Version and diagnostics sit in a secondary system-information surface, not as a permanent green status badge.

### Shared visual language

Use the warm neutral ramp and solid product blue defined by the approved design artifact. Primary actions use blue fills; accent text uses the accessible accent-text token. Semantic colours indicate state only. Cards group related records and should not wrap every individual value in a badge. Use mono text for identifiers, version pins, hashes, and timestamps.

The approval seal is a small square stamped mark, used only for approved work. It must show the relevant work-item code and optional short state; it is not a generic decoration or a substitute for the approval record.

## Screen specifications

### Office

**User question:** Who is working, where are they organized, and what work is in motion?

- Start with a compact organization summary: departments, active employees, and current assignments, using observed counts only.
- Show the organization hierarchy as the primary view. A spatial office view may be offered as a switchable visualization when room and position data exist.
- Selecting an employee opens a detail panel with organizational role, capabilities or skills, current runtime state, assigned work, and recent relevant events.
- Distinguish persistent employee identity from the execution runtime. Paused or terminated runtime state must not imply that the employee record was removed.
- Empty state explains that no workforce records are available and offers the relevant setup or refresh action only if supported.

### Deliberations

**User question:** What decisions are being discussed, who is involved, and what has been recorded?

- Present meetings as a list grouped by active, scheduled, and concluded state, with the state vocabulary backed by real data.
- Each row shows title or agenda, room, participants, facilitator, and the most relevant time. Avoid invented activity summaries.
- Meeting detail contains agenda, participant roles, discussion artifacts, decisions, and follow-up work. Keep source notes distinguishable from approved decisions.
- Decision records link to the artifacts or requirements they affect. A meeting conclusion alone must not appear as an approved baseline.

### SDLC

**User question:** Which lifecycle stage is active, what evidence is incomplete, and what needs human review?

- Preserve the canonical stage order and stage names from the domain model. Use a horizontal phase overview with a vertically readable stage list or responsive card grid; do not collapse the lifecycle into an arbitrary kanban board.
- Every stage row shows stage code, name, phase, state, accountable lead, artifact count, and baseline version or hash where present.
- Put the current actionable gate first in the working area and make its missing checklist items explicit. Completed and pending stages remain inspectable without competing for attention.
- Stage detail presents the verification checklist, artifacts with pinned versions, provenance links, and baseline comparison. Hashes are copyable and rendered in mono text.
- Ratification is available only to an authorized human. The action is disabled until required checks pass; its confirmation states the stage, exact baseline version, and the permanence of the recorded decision. The resulting approval record shows who approved and which version was approved.
- Use the approved traceability path as the one richly plotted visualization on this view. Each node links to its source record and version. Provide a textual equivalent for screen readers and narrow screens.

### Knowledge & Trace

**User question:** What evidence is available, where did it come from, and what does it support?

- Provide one search field with filters for record type, project, epistemic status, and recency where those fields are available.
- Results show title, source, status, update time, and a short relevant excerpt. Never promote agent inference to authoritative requirement through styling or sorting.
- The record view distinguishes authoritative requirements, approved baselines, existing practice, best practice, agent inference, and assumption or unknown.
- Trace links show relation type and both endpoint versions. Selecting either endpoint opens the corresponding record. A missing endpoint or version is represented explicitly as unavailable.

### Knowledge Chat

**User question:** Can I ask a question and verify the answer against its sources?

- Keep the conversation and source evidence visible together on wide screens. On small screens, expose sources in a dedicated, keyboard-accessible disclosure.
- Each answer separates the response from its cited passages. A citation opens the exact source record and version, not only a broad search result.
- Show an explicit empty state before the first question and a clear loading state during retrieval. Distinguish no evidence found from a service failure.
- If generation fails or sources are unavailable, preserve the user's question and offer retry. Do not show fabricated citations or a success state without retrieved evidence.

## Core interaction patterns

### Inspect, then act

Record rows open a detail surface without losing the user's place. Use a side panel for quick inspection and a full page for long evidence, comparison, or review tasks. Provide visible close and back behavior, preserve keyboard focus, and keep actions adjacent to the record they affect.

### Gate review

1. User opens a stage marked for review.
2. The detail view lists required checks and the exact candidate baseline.
3. User opens each evidence item or verifies the baseline comparison.
4. Ratification becomes available only after all domain-required checks pass.
5. A confirmation names the candidate, version, and approving human.
6. Success renders the recorded decision and links to the approved version.

UI state alone must never be treated as the approval record. The server is authoritative for permissions and transition validity.

### Search and filtering

Filters are additive, removable, and summarized in plain language. Keep search terms when opening and closing a record. On narrow layouts, filters open in a labelled dialog or disclosure with an obvious apply/reset path.

## Responsive behavior

- **Wide desktop:** persistent navigation rail, page content with a readable maximum line length, and optional detail panel beside the main list.
- **Tablet:** navigation can collapse to icons only when accessible names remain available; detail panels become overlays if the content area is constrained.
- **Mobile:** single-column reading order, full-width primary actions, touch targets sized for comfortable use, and no horizontal scrolling for core tasks. Convert trace diagrams to a vertical sequence or a labelled list.
- Components adapt to their containing panel where their available width differs from the viewport. Long hashes and filenames wrap or truncate with a way to inspect the full value.
- Respect reduced-motion preferences. State changes must remain understandable without animation.

## Accessibility and content rules

- Use semantic page landmarks and a heading hierarchy that reflects the screen structure.
- Every state has text; colour and icons are supporting cues. All interactive controls have a visible focus state and a name that explains the action.
- Dialogs and overlays move focus inside on open, constrain it while open, and return focus to the trigger on close.
- Tabular evidence has semantic headers. On small screens, preserve labels when reflowing rows into stacked records.
- Use concise sentence case. Avoid uppercase telemetry labels, decorative abbreviations, unexplained hashes, unverified claims, and placeholder data that resembles real production state.
- Timestamps should use the user's locale and timezone while retaining an inspectable absolute timestamp where precision matters.

## Data contract and empty states

The interface may present only fields supplied by domain records or clearly labelled derived values. Unknown values display as unknown or unavailable, never as a plausible fabricated value. Each module needs designed states for loading, no records, no search matches, partial data, permission denied, disconnected service, and recoverable error. Keep retry or navigation actions specific to the actual failure.

## Delivery sequence

1. Apply the shared shell, tokens, type hierarchy, and navigation labels.
2. Implement SDLC stage inspection and the human ratification path, since this is the platform's defining governed workflow.
3. Bring Knowledge & Trace and Knowledge Chat into the same evidence and version model.
4. Refine Office and Deliberations against actual employee, runtime, meeting, and decision records.
5. Verify each screen at desktop, tablet, and mobile widths, including keyboard-only navigation, reduced motion, empty states, and permission boundaries.

## Acceptance checklist

- The user can identify the current destination, operator, and observed connection state without decorative status noise.
- Lifecycle stage order and status vocabulary match the domain model.
- Every approval action is explicitly human, names an exact version, and cannot be enabled while required checks are incomplete.
- Knowledge claims expose epistemic status, and traceability links expose both pinned versions.
- Chat answers provide inspectable source passages and truthful no-evidence and error states.
- Office views preserve the distinction between an employee and its runtime.
- All core tasks work at narrow widths and with keyboard navigation; state does not depend on colour or motion.
- No UI presents invented operational state, fabricated evidence, or unsupported success claims.

## Reference

This specification follows the approved product character, world, palette, and signature rules in [AVRIG-00002](AVRIG-00002/design.md). That artifact attributes its adaptation of the unslop method to Damir Sokolovsky under CC BY 4.0.
